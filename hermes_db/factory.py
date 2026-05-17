"""Connection factory.

Single entry point that the rest of the codebase calls:

    from hermes_db import connect
    with connect("state") as conn:
        ...

Responsibilities
----------------
- Pick the backend from :func:`hermes_db.config.get_storage_config`.
- Resolve a logical ``store`` name (``"state"``, ``"kanban"``, ...) to:
  * a SQLite file path (default: ``$HERMES_HOME/<store>.db``), or
  * a MySQL database name (from ``MySQLConfig.database_for(store)``).
- Cache one connection per ``(backend, store, path-or-database)`` so
  repeated ``connect()`` calls do not re-open sockets.  Callers that
  legitimately need a fresh connection pass ``shared=False``.
- Expose :func:`close_all` for orderly shutdown.

The factory does NOT attempt schema migration; that's the job of
``hermes_db.migrate`` (Task 2) and is run explicitly via
``hermes db migrate`` or as part of CLI startup.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple

from hermes_db.config import KNOWN_STORES, MySQLConfig, get_storage_config
from hermes_db.connection import Connection
from hermes_db.mysql_backend import MySQLConnection
from hermes_db.sqlite_backend import SQLiteConnection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HERMES_HOME resolution
# ---------------------------------------------------------------------------


def _hermes_home() -> Path:
    """Return ``$HERMES_HOME`` (or ``~/.hermes``) as a Path.

    Mirrors the resolution order used by :mod:`hermes_state` and
    ``hermes_cli`` so default paths stay aligned across the codebase.
    """

    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hermes"


# Default per-store sqlite filenames.  Holographic memory and other
# memory-provider stores ship their own paths; for those, callers pass
# an explicit ``path=`` override to :func:`connect`.
_DEFAULT_SQLITE_FILES: Dict[str, str] = {
    "state": "state.db",
    "kanban": "kanban.db",
    "memory_store": "memory_store.db",
    "response_store": "response_store.db",
}


def _default_sqlite_path(store: str) -> Path:
    fname = _DEFAULT_SQLITE_FILES.get(store, f"{store}.db")
    return _hermes_home() / fname


# ---------------------------------------------------------------------------
# Connection cache
# ---------------------------------------------------------------------------

# Keyed by (backend, store, key) where ``key`` is the absolute sqlite
# path or the mysql database name.  Distinct keys ⇒ distinct entries
# so multi-board kanban (each board has its own ``kanban.db`` path)
# does not collide.
_cache: Dict[Tuple[str, str, str], Connection] = {}
_cache_lock = threading.RLock()


def get_backend() -> str:
    """Return the active backend name (``"sqlite"`` or ``"mysql"``)."""

    return get_storage_config().backend


def _build_sqlite(store: str, path: Path, **kwargs) -> SQLiteConnection:
    return SQLiteConnection(store=store, path=path, **kwargs)


def _build_mysql(store: str, mysql_cfg: MySQLConfig, database: str) -> MySQLConnection:
    return MySQLConnection(
        store=store,
        host=mysql_cfg.host,
        port=mysql_cfg.port,
        user=mysql_cfg.user,
        password=mysql_cfg.password,
        database=database,
        charset=mysql_cfg.charset,
        connect_timeout=mysql_cfg.connect_timeout,
        autocommit=mysql_cfg.autocommit,
        ssl_disabled=mysql_cfg.ssl_disabled,
        extra=mysql_cfg.extra,
    )


def connect(
    store: str,
    *,
    path: Optional[Path] = None,
    shared: bool = True,
    sqlite_kwargs: Optional[dict] = None,
) -> Connection:
    """Open (or return cached) connection for ``store``.

    Parameters
    ----------
    store
        Logical name (``"state"``, ``"kanban"``, ``"memory_store"``,
        ``"response_store"``, or any custom store name).  Unknown
        names are accepted (e.g. memory-provider databases) but a
        debug log is emitted because the SQLite default-path may not
        match the caller's expectation.
    path
        SQLite file path override.  Required for non-default stores
        (e.g. ``~/.hermes/memories/holographic_memory.db``) and for
        multi-DB kanban boards.  Ignored when the backend is MySQL.
    shared
        When ``True`` (default), the same backing connection is
        returned on subsequent calls.  Set to ``False`` for short-lived
        scripts that need their own connection (e.g. backup tools that
        want isolated transactions).
    sqlite_kwargs
        Extra keyword arguments forwarded to :class:`SQLiteConnection`
        (e.g. ``timeout``, ``foreign_keys``, ``wal``).  Ignored for
        MySQL.
    """

    if store not in KNOWN_STORES:
        # Not an error: memory-provider stores and tests use custom names.
        logger.debug("hermes_db.connect: non-standard store name %r", store)

    cfg = get_storage_config()
    backend = cfg.backend

    if backend == "sqlite":
        sqlite_path = (path if path is not None else _default_sqlite_path(store))
        sqlite_path = Path(sqlite_path).expanduser().resolve()
        cache_key = (backend, store, str(sqlite_path))
    elif backend == "mysql":
        database = cfg.mysql.database_for(store)
        cache_key = (backend, store, database)
    else:  # pragma: no cover - resolver clamps to supported set
        raise RuntimeError(f"hermes_db: unsupported backend {backend!r}")

    if shared:
        with _cache_lock:
            cached = _cache.get(cache_key)
            if cached is not None and not cached.is_closed:
                return cached

    if backend == "sqlite":
        conn = _build_sqlite(store, sqlite_path, **(sqlite_kwargs or {}))
    else:
        conn = _build_mysql(store, cfg.mysql, database)

    if shared:
        with _cache_lock:
            existing = _cache.get(cache_key)
            if existing is not None and not existing.is_closed:
                # Lost a race; keep the existing one and discard the new.
                try:
                    conn.close()
                except Exception:
                    pass
                return existing
            _cache[cache_key] = conn

    return conn


def close_all() -> None:
    """Close every cached connection.  Idempotent."""

    with _cache_lock:
        items = list(_cache.items())
        _cache.clear()
    for key, conn in items:
        try:
            conn.close()
        except Exception as exc:
            logger.debug("hermes_db: close_all error for %s: %s", key, exc)


__all__ = ["connect", "get_backend", "close_all"]
