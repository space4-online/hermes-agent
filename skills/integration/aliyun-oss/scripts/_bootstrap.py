"""
Lazy dependency bootstrap for the aliyun-oss skill.

Why: the host pyproject does not include `oss2`, so a freshly built
hermes container has no SDK. We don't want to require ops to remember
`pip install -r requirements.txt` after every image rebuild — the skill
should self-heal on first invocation.

Strategy:
  1. Try to `import oss2`. If it works, return.
  2. Otherwise install missing deps into a writable, persistent cache
     dir under `$HERMES_HOME/skill-deps/aliyun-oss/`. We use this dir
     instead of the venv because:
       - the venv (/opt/hermes/.venv) is owned by root in our Docker
         image and the runtime user (`hermes`) cannot write to it
       - `$HERMES_HOME` (= `/opt/data`, bind-mounted from `~/.hermes`)
         is writable by the runtime user and persists across container
         restarts, so the install runs at most once per host
  3. Insert the cache dir into `sys.path` and re-attempt the import.

Escape hatches:
  - `HERMES_OSS_NO_BOOTSTRAP=1` skips bootstrap (for debugging or when
    the user manages deps via pyproject). The caller will see the usual
    ImportError surface.
  - `HERMES_OSS_DEPS_DIR=<path>` overrides the cache location.

All progress / pip output is sent to stderr so the caller's stdout
(reserved for the JSON contract) stays clean.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence


# Modules → pip distribution names. Only oss2 is missing from the host
# pyproject — PyYAML ships with hermes core. Listing it here as a sanity
# check is cheap; if it's already importable we won't reinstall.
_REQUIRED = (
    ("oss2", "oss2>=2.18.0"),
)

_PIP_TIMEOUT_SECONDS = 240


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hermes"


def _deps_dir() -> Path:
    override = os.environ.get("HERMES_OSS_DEPS_DIR")
    if override:
        return Path(override).expanduser()
    return _hermes_home() / "skill-deps" / "aliyun-oss"


def _missing(modules: Sequence[tuple[str, str]]) -> list[str]:
    """Return pip specs for every module that fails to import."""
    needed: list[str] = []
    for module_name, pip_spec in modules:
        try:
            __import__(module_name)
        except ImportError:
            needed.append(pip_spec)
    return needed


def _log(msg: str) -> None:
    print(f"[aliyun-oss/bootstrap] {msg}", file=sys.stderr, flush=True)


def _run_pip(target: Path, specs: Sequence[str]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", str(target),
        "--quiet", "--disable-pip-version-check", "--no-input",
        *specs,
    ]
    _log(f"installing {', '.join(specs)} into {target}")
    proc = subprocess.run(
        cmd,
        timeout=_PIP_TIMEOUT_SECONDS,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        # Surface pip's stderr — it usually pinpoints the network or
        # version-resolution issue — so the JSON error the CLI emits
        # afterwards is actionable.
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-15:]
        raise RuntimeError(
            "pip install failed (exit "
            f"{proc.returncode}). Last lines:\n  "
            + "\n  ".join(tail)
        )


def ensure_dependencies() -> None:
    """Make sure `oss2` is importable. No-op if already installed.

    Raises RuntimeError on install failure so the CLI can wrap it in the
    standard `{"ok": false, "error": ...}` envelope.
    """
    if os.environ.get("HERMES_OSS_NO_BOOTSTRAP", "").strip() in ("1", "true", "yes"):
        return

    # Add the cache dir to sys.path *before* the first probe so a prior
    # successful install (from a previous invocation) gets picked up
    # without going through pip again.
    cache = _deps_dir()
    if cache.exists() and str(cache) not in sys.path:
        sys.path.insert(0, str(cache))

    missing = _missing(_REQUIRED)
    if not missing:
        return

    _run_pip(cache, missing)

    # Re-probe with the cache dir on the path.
    if str(cache) not in sys.path:
        sys.path.insert(0, str(cache))
    still_missing = _missing(_REQUIRED)
    if still_missing:
        raise RuntimeError(
            "dependencies still unimportable after install: "
            + ", ".join(still_missing)
            + f". Cache dir: {cache}. Try clearing it and re-running."
        )
    _log("dependencies ready")
