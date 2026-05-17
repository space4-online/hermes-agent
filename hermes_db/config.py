"""Storage configuration loader.

Resolves the active storage backend (sqlite or mysql) and the
parameters required to connect.  Honors three sources in priority
order:

1. Environment variables (HERMES_DB_* — highest priority, useful for
   Docker / systemd / CI overrides).
2. ``storage:`` section in the active ``config.yaml``.
3. Built-in defaults (``backend = sqlite``).

The loader is import-safe: it never touches the filesystem at module
load time and lazily caches the resolved config to avoid re-parsing
``config.yaml`` for every ``connect()`` call.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Recognized backend names.  Add new engines here when extending the
# abstraction (e.g. ``"postgres"``); the factory dispatches on this.
SUPPORTED_BACKENDS = ("sqlite", "mysql")

# Logical store names that the factory understands.  Listed here so
# unknown names trigger a clear error instead of silently mapping to
# the default sqlite path.
KNOWN_STORES = ("state", "kanban", "memory_store", "response_store")


@dataclass
class MySQLConfig:
    """Connection parameters for the external MySQL service.

    All fields are optional at the dataclass level so partial config
    objects can be built up; ``validate()`` enforces the required set
    when the backend is actually mysql.
    """

    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "hermes"
    password: str = ""
    database: str = "hermes"
    charset: str = "utf8mb4"
    pool_size: int = 5
    connect_timeout: int = 10
    autocommit: bool = False
    ssl_disabled: bool = False
    # Per-store database name override (``state``: ``hermes_state``).
    # When set, the store uses this database instead of ``database``.
    # Useful when ops policy requires per-store isolation.
    per_store_database: Dict[str, str] = field(default_factory=dict)
    # Free-form extra params forwarded to ``pymysql.connect``.
    extra: Dict[str, Any] = field(default_factory=dict)

    def database_for(self, store: str) -> str:
        return self.per_store_database.get(store, self.database)

    def validate(self) -> None:
        if not self.host:
            raise ValueError("storage.mysql.host is required")
        if not self.database:
            raise ValueError("storage.mysql.database is required")
        if not self.user:
            raise ValueError("storage.mysql.user is required")
        if self.port <= 0 or self.port > 65535:
            raise ValueError(f"storage.mysql.port out of range: {self.port}")


@dataclass
class StorageConfig:
    """Resolved active storage configuration."""

    backend: str = "sqlite"
    mysql: MySQLConfig = field(default_factory=MySQLConfig)

    def is_sqlite(self) -> bool:
        return self.backend == "sqlite"

    def is_mysql(self) -> bool:
        return self.backend == "mysql"


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

_cached: Optional[StorageConfig] = None
_cache_lock = threading.Lock()


def _coerce_int(val: Any, default: int) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _coerce_bool(val: Any, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return default


def _load_yaml_storage_section() -> Dict[str, Any]:
    """Best-effort read of the ``storage:`` section in ``config.yaml``.

    Returns an empty dict on any failure — the caller then falls back
    to defaults / env vars.  We deliberately avoid hard-importing
    ``hermes_cli.config`` here because that module imports a lot of
    optional dependencies; a partial install (e.g. fresh container
    bootstrap) should still let the SQLite backend work.
    """

    try:
        from hermes_cli.config import load_config  # type: ignore
    except Exception:  # pragma: no cover - optional during early bootstrap
        return {}

    try:
        cfg = load_config() or {}
    except Exception as exc:
        logger.debug("storage config: failed to load config.yaml: %s", exc)
        return {}

    section = cfg.get("storage")
    if isinstance(section, dict):
        return section
    return {}


def _build_mysql_config(yaml_section: Dict[str, Any]) -> MySQLConfig:
    """Merge YAML + env vars into a MySQLConfig.  Env wins on conflicts."""

    raw = (yaml_section.get("mysql") or {}) if isinstance(yaml_section, dict) else {}

    # YAML
    cfg = MySQLConfig(
        host=str(raw.get("host", "127.0.0.1")),
        port=_coerce_int(raw.get("port"), 3306),
        user=str(raw.get("user", "hermes")),
        password=str(raw.get("password", "")),
        database=str(raw.get("database", "hermes")),
        charset=str(raw.get("charset", "utf8mb4")),
        pool_size=_coerce_int(raw.get("pool_size"), 5),
        connect_timeout=_coerce_int(raw.get("connect_timeout"), 10),
        autocommit=_coerce_bool(raw.get("autocommit"), False),
        ssl_disabled=_coerce_bool(raw.get("ssl_disabled"), False),
    )
    psd = raw.get("per_store_database")
    if isinstance(psd, dict):
        cfg.per_store_database = {str(k): str(v) for k, v in psd.items()}
    extra = raw.get("extra")
    if isinstance(extra, dict):
        cfg.extra = dict(extra)

    # Env overrides
    env = os.environ
    if env.get("HERMES_DB_HOST"):
        cfg.host = env["HERMES_DB_HOST"].strip()
    if env.get("HERMES_DB_PORT"):
        cfg.port = _coerce_int(env["HERMES_DB_PORT"], cfg.port)
    if env.get("HERMES_DB_USER"):
        cfg.user = env["HERMES_DB_USER"].strip()
    if "HERMES_DB_PASSWORD" in env:
        # Allow empty string override (e.g. for local trust auth).
        cfg.password = env["HERMES_DB_PASSWORD"]
    if env.get("HERMES_DB_NAME"):
        cfg.database = env["HERMES_DB_NAME"].strip()
    if env.get("HERMES_DB_CHARSET"):
        cfg.charset = env["HERMES_DB_CHARSET"].strip()
    if env.get("HERMES_DB_POOL_SIZE"):
        cfg.pool_size = _coerce_int(env["HERMES_DB_POOL_SIZE"], cfg.pool_size)
    if env.get("HERMES_DB_CONNECT_TIMEOUT"):
        cfg.connect_timeout = _coerce_int(
            env["HERMES_DB_CONNECT_TIMEOUT"], cfg.connect_timeout
        )

    return cfg


def _resolve() -> StorageConfig:
    yaml_section = _load_yaml_storage_section()

    backend = (
        os.environ.get("HERMES_DB_BACKEND")
        or (yaml_section.get("backend") if isinstance(yaml_section, dict) else None)
        or "sqlite"
    )
    backend = str(backend).strip().lower()
    if backend not in SUPPORTED_BACKENDS:
        logger.warning(
            "storage.backend=%r is not supported; falling back to sqlite. "
            "Supported: %s",
            backend,
            SUPPORTED_BACKENDS,
        )
        backend = "sqlite"

    mysql_cfg = _build_mysql_config(yaml_section if isinstance(yaml_section, dict) else {})

    cfg = StorageConfig(backend=backend, mysql=mysql_cfg)

    if cfg.is_mysql():
        try:
            cfg.mysql.validate()
        except ValueError as exc:
            logger.error(
                "storage.backend=mysql but configuration is invalid: %s. "
                "Falling back to sqlite to avoid hard startup failure.",
                exc,
            )
            cfg.backend = "sqlite"

    return cfg


def get_storage_config() -> StorageConfig:
    """Return the cached storage config, resolving on first call."""

    global _cached
    if _cached is not None:
        return _cached
    with _cache_lock:
        if _cached is None:
            _cached = _resolve()
    return _cached


def reload_storage_config() -> StorageConfig:
    """Re-resolve from disk + env.  Useful for tests and ``hermes db reload``."""

    global _cached
    with _cache_lock:
        _cached = _resolve()
    return _cached
