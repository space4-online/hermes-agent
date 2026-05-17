"""Pluggable storage backend layer for Hermes Agent.

Provides a thin DB-API-2.0-shaped abstraction that lets ``state.db``,
``kanban.db``, ``memory_store.db`` and ``response_store.db`` run on
either SQLite (default, file-based) or an external MySQL service.

Usage:
    from hermes_db import connect, get_backend

    with connect("state") as conn:
        cur = conn.execute("SELECT id FROM sessions WHERE id = ?", (sid,))
        row = cur.fetchone()

The high-level rule of thumb:
- SQL stays raw; dialect helpers in ``hermes_db.dialect`` hide the
  small per-engine differences (FTS5 vs FULLTEXT, parameter style, ...).
- Each logical store has a name (``"state"``, ``"kanban"``, ...) which
  the factory routes to the right backend / file / database.
- The default backend is sqlite — a fresh checkout with no
  ``storage.backend`` config keeps every existing code path intact.
"""

from __future__ import annotations

from hermes_db.config import (
    StorageConfig,
    get_storage_config,
    reload_storage_config,
)
from hermes_db.connection import Connection, Cursor, Row
from hermes_db.factory import connect, get_backend, close_all

__all__ = [
    "StorageConfig",
    "get_storage_config",
    "reload_storage_config",
    "Connection",
    "Cursor",
    "Row",
    "connect",
    "get_backend",
    "close_all",
]
