"""
Vault — Structured credential storage for Hermes Agent.

Provides a named credential store that integrates with the placeholder engine
to ensure sensitive values are never exposed to the LLM while remaining
available for tool execution.

Storage locations:
  - Global: HERMES_HOME/vault.yaml (permissions 0600)
  - Project: <project_root>/.hermes-vault (permissions 0600)

Merge strategy: project-level credentials override global ones with the same name.
"""

from __future__ import annotations

import os
import stat
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


@dataclass
class CredentialInfo:
    """Public metadata for a credential (no value exposed)."""
    name: str
    description: str = ""
    created: str = ""
    scope: str = "global"  # "global" or "project"


@dataclass
class _CredentialEntry:
    """Internal full credential entry including the secret value."""
    value: str
    description: str = ""
    created: str = ""


def _yaml_available() -> bool:
    return yaml is not None


def _ensure_yaml():
    if not _yaml_available():
        raise ImportError(
            "PyYAML is required for vault operations. Install with: pip install pyyaml"
        )


def _secure_write(path: Path, content: str) -> None:
    """Write content to file with secure permissions (0600)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600


def _ensure_gitignore_entry(project_root: Path) -> None:
    """Ensure .hermes-vault is listed in the project's .gitignore."""
    gitignore_path = project_root / ".gitignore"
    entry = ".hermes-vault"
    try:
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
            if entry in content.splitlines():
                return
            if not content.endswith("\n"):
                content += "\n"
            content += f"\n# Hermes credential vault (contains secrets)\n{entry}\n"
            gitignore_path.write_text(content, encoding="utf-8")
        else:
            gitignore_path.write_text(
                f"# Hermes credential vault (contains secrets)\n{entry}\n",
                encoding="utf-8",
            )
    except OSError:
        pass  # Best-effort; don't fail credential storage if .gitignore can't be updated


def _load_vault_file(path: Path) -> Dict[str, _CredentialEntry]:
    """Load credentials from a YAML vault file."""
    _ensure_yaml()
    if not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    creds_raw = raw.get("credentials", {})
    if not isinstance(creds_raw, dict):
        return {}
    entries: Dict[str, _CredentialEntry] = {}
    for name, data in creds_raw.items():
        if not isinstance(data, dict) or "value" not in data:
            continue
        entries[str(name)] = _CredentialEntry(
            value=str(data["value"]),
            description=str(data.get("description", "")),
            created=str(data.get("created", "")),
        )
    return entries


def _save_vault_file(path: Path, entries: Dict[str, _CredentialEntry]) -> None:
    """Save credentials to a YAML vault file with secure permissions."""
    _ensure_yaml()
    creds_data = {}
    for name, entry in sorted(entries.items()):
        creds_data[name] = {
            "value": entry.value,
            "description": entry.description,
            "created": entry.created,
        }
    content = yaml.dump(
        {"credentials": creds_data},
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    _secure_write(path, content)


class VaultStore:
    """
    Credential vault supporting global and project-level scopes.

    Usage:
        vault = VaultStore(hermes_home=Path("~/.hermes"), project_root=Path("/my/project"))
        vault.set("GITHUB_TOKEN", "ghp_xxxx", description="My PAT")
        token = vault.get("GITHUB_TOKEN")  # -> "ghp_xxxx"
    """

    def __init__(
        self,
        hermes_home: Optional[Path] = None,
        project_root: Optional[Path] = None,
    ):
        self._lock = threading.Lock()
        # Resolve paths
        if hermes_home is None:
            from hermes_constants import get_hermes_home
            hermes_home = Path(get_hermes_home())
        self._global_path = hermes_home / "vault.yaml"
        self._project_path = (
            Path(project_root) / ".hermes-vault" if project_root else None
        )
        # Lazy-loaded caches
        self._global_entries: Optional[Dict[str, _CredentialEntry]] = None
        self._project_entries: Optional[Dict[str, _CredentialEntry]] = None

    @property
    def global_path(self) -> Path:
        return self._global_path

    @property
    def project_path(self) -> Optional[Path]:
        return self._project_path

    def _load_global(self) -> Dict[str, _CredentialEntry]:
        if self._global_entries is None:
            self._global_entries = _load_vault_file(self._global_path)
        return self._global_entries

    def _load_project(self) -> Dict[str, _CredentialEntry]:
        if self._project_entries is None:
            if self._project_path:
                self._project_entries = _load_vault_file(self._project_path)
            else:
                self._project_entries = {}
        return self._project_entries

    def reload(self) -> None:
        """Force reload from disk."""
        with self._lock:
            self._global_entries = None
            self._project_entries = None

    def get(self, name: str) -> Optional[str]:
        """Get credential value by name. Project-level overrides global."""
        with self._lock:
            project = self._load_project()
            if name in project:
                return project[name].value
            globe = self._load_global()
            if name in globe:
                return globe[name].value
            return None

    def set(
        self,
        name: str,
        value: str,
        description: str = "",
        scope: str = "global",
    ) -> None:
        """Store or update a credential."""
        with self._lock:
            entry = _CredentialEntry(
                value=value,
                description=description,
                created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
            if scope == "project":
                if self._project_path is None:
                    raise ValueError(
                        "No project root configured. Use --project with a valid project directory."
                    )
                entries = self._load_project()
                entries[name] = entry
                _save_vault_file(self._project_path, entries)
                # Auto-add .hermes-vault to .gitignore if not already present
                _ensure_gitignore_entry(self._project_path.parent)
            else:
                entries = self._load_global()
                entries[name] = entry
                _save_vault_file(self._global_path, entries)

    def delete(self, name: str, scope: str = "global") -> bool:
        """Delete a credential. Returns True if it existed."""
        with self._lock:
            if scope == "project":
                if self._project_path is None:
                    return False
                entries = self._load_project()
            else:
                entries = self._load_global()
            if name not in entries:
                return False
            del entries[name]
            path = self._project_path if scope == "project" else self._global_path
            _save_vault_file(path, entries)
            return True

    def list(self) -> List[CredentialInfo]:
        """List all credentials (merged, no values). Project overrides global."""
        with self._lock:
            result: Dict[str, CredentialInfo] = {}
            for name, entry in self._load_global().items():
                result[name] = CredentialInfo(
                    name=name,
                    description=entry.description,
                    created=entry.created,
                    scope="global",
                )
            for name, entry in self._load_project().items():
                result[name] = CredentialInfo(
                    name=name,
                    description=entry.description,
                    created=entry.created,
                    scope="project",
                )
            return sorted(result.values(), key=lambda c: c.name)

    def all_entries(self) -> Dict[str, str]:
        """Return name->value mapping of all credentials (merged).
        Project-level overrides global. Used internally by the placeholder engine."""
        with self._lock:
            merged: Dict[str, str] = {}
            for name, entry in self._load_global().items():
                merged[name] = entry.value
            for name, entry in self._load_project().items():
                merged[name] = entry.value
            return merged

    def has(self, name: str) -> bool:
        """Check if a credential exists."""
        return self.get(name) is not None
