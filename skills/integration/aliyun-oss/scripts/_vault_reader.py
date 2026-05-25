"""
Standalone vault.yaml reader.

The skill subprocess can't always import `agent.vault` (sys.path may differ
when running outside the Hermes process). This is a minimal reader that
opens ~/.hermes/vault.yaml directly and returns name -> value mapping.

Reads:
  1. ~/.hermes/vault.yaml          (global; HERMES_HOME overrides ~/.hermes)
  2. <project_root>/.hermes-vault  (project; if HERMES_PROJECT_ROOT is set)

Project entries override global entries.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

try:
    import yaml
except ImportError:                     # pragma: no cover
    yaml = None  # type: ignore[assignment]


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hermes"


def _project_root() -> Optional[Path]:
    env = os.environ.get("HERMES_PROJECT_ROOT")
    if env:
        return Path(env).expanduser()
    return None


def _load_yaml(path: Path) -> Dict[str, str]:
    if yaml is None or not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    creds = raw.get("credentials", {})
    if not isinstance(creds, dict):
        return {}
    out: Dict[str, str] = {}
    for name, data in creds.items():
        if isinstance(data, dict) and "value" in data:
            out[str(name)] = str(data["value"])
    return out


def load_vault() -> Dict[str, str]:
    """Return merged name->value mapping (project overrides global)."""
    out = _load_yaml(_hermes_home() / "vault.yaml")
    proj_root = _project_root()
    if proj_root:
        out.update(_load_yaml(proj_root / ".hermes-vault"))
    return out


def get(name: str, default: Optional[str] = None) -> Optional[str]:
    """Single entry lookup. Env var of the same name wins (for local debug)."""
    env_v = os.environ.get(name)
    if env_v:
        return env_v
    return load_vault().get(name, default)


def list_profiles() -> list[str]:
    """Detect available OSS profiles by scanning vault keys.

    A profile <P> is "available" iff vault contains all 4 of:
    OSS_<P>_ENDPOINT / OSS_<P>_BUCKET / OSS_<P>_AK / OSS_<P>_SK.
    """
    entries = load_vault()
    # Also pick up env-var profiles (useful in CI / local debug)
    for k in os.environ:
        if k.startswith("OSS_") and (
            k.endswith("_ENDPOINT") or k.endswith("_BUCKET")
            or k.endswith("_AK") or k.endswith("_SK")
        ):
            entries.setdefault(k, os.environ[k])
    profiles: dict[str, set[str]] = {}
    for k in entries:
        if not k.startswith("OSS_"):
            continue
        parts = k.split("_")
        if len(parts) < 3:
            continue
        # OSS_<PROFILE>_<FIELD>; FIELD might itself be 1-2 tokens (AK / SK)
        # but our schema only uses 1-token fields.
        profile = "_".join(parts[1:-1])
        field = parts[-1]
        profiles.setdefault(profile, set()).add(field)
    out = sorted(p for p, f in profiles.items() if {"ENDPOINT", "BUCKET", "AK", "SK"} <= f)
    return out
