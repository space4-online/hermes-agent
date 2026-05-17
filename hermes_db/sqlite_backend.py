"""SQLite backend.

Wraps the stdlib ``sqlite3`` module so it satisfies the
:class:`hermes_db.connection.Connection` / ``Cursor`` protocols.

Design notes
------------
- Each logical store maps to a single ``.db`` file.  The file path is
  decided by the factory (typically under ``HERMES_HOME``); this module
  only cares about opening the path it's given.
- WAL is enabled with the standard NFS/SMB/FUSE fallback path that is
  shared with the legacy code paths (we re-use
  ``hermes_state.apply_wal_with_fallback`` so the warning-deduping
  story is identical and we don't fork the heuristic).
- Rows are exposed as :class:`hermes_db.connection.Row` so callers see
  the same shape as the MySQL backend.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from hermes_db.connection import Connection, Cursor, Row

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------


class _SQLiteCursor(Cursor):
    """Thin adapter around ``sqlite3.Cursor`` returning :class:`Row`."""

    __slots__ = ("_cur",)

    def __init__(self, cur: sqlite3.Cursor) -> None:
        self._cur = cur

    def _columns(self) -> List[str]:
        desc = self._cur.description or ()
        return [d[0] for d in desc]

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> "Cursor":
        if params is None:
            self._cur.execute(sql)
        else:
            self._cur.execute(sql, tuple(params))
        return self

    def executemany(
        self, sql: str, seq_of_params: Iterable[Sequence[Any]]
    ) -> "Cursor":
        self._cur.executemany(sql, [tuple(p) for p in seq_of_params])
        return self

    def fetchone(self) -> Optional[Row]:
        raw = self._cur.fetchone()
        if raw is None:
            return None
        return Row(self._columns(), tuple(raw))

    def fetchall(self) -> List[Row]:
        cols = self._columns()
        return [Row(cols, tuple(r)) for r in self._cur.fetchall()]

    def fetchmany(self, size: int = 0) -> List[Row]:
        cols = self._columns()
        if size <= 0:
            rows = self._cur.fetchmany()
        else:
            rows = self._cur.fetchmany(size)
        return [Row(cols, tuple(r)) for r in rows]

    @property
    def lastrowid(self) -> Optional[int]:
        return self._cur.lastrowid

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    def close(self) -> None:
        try:
            self._cur.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


class SQLiteConnection(Connection):
    """Wraps a single ``sqlite3.Connection`` for one logical store."""

    backend = "sqlite"

    def __init__(
        self,
        *,
        store: str,
        path: Path,
        timeout: float = 30.0,
        foreign_keys: bool = True,
        wal: bool = True,
        wal_label: Optional[str] = None,
    ) -> None:
        self.store = store
        self._path = Path(path)
        self._lock = threading.RLock()
        self._closed = False

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._raw = sqlite3.connect(
            str(self._path),
            timeout=timeout,
            isolation_level="DEFERRED",
            check_same_thread=False,
        )
        # We deliberately do NOT set ``row_factory`` — the cursor wrapper
        # returns :class:`Row` regardless.

        if wal:
            try:
                from hermes_state import apply_wal_with_fallback  # type: ignore
                apply_wal_with_fallback(
                    self._raw, db_label=wal_label or self._path.name
                )
            except Exception as exc:  # pragma: no cover - defensive
                # Do not fail the connection just because WAL couldn't be
                # negotiated; the store is still usable in default mode.
                logger.debug(
                    "sqlite_backend: WAL setup skipped for %s: %s",
                    self._path,
                    exc,
                )

        if foreign_keys:
            try:
                self._raw.execute("PRAGMA foreign_keys=ON")
            except Exception as exc:  # pragma: no cover
                logger.debug("sqlite_backend: PRAGMA foreign_keys failed: %s", exc)

    # Path is occasionally useful for diagnostics / VACUUM helpers
    @property
    def path(self) -> Path:
        return self._path

    @property
    def raw(self) -> sqlite3.Connection:
        """Return the underlying ``sqlite3.Connection``.

        Some legacy call sites need engine-specific features (e.g.
        ``conn.iterdump()`` for backup or ``PRAGMA wal_checkpoint``).
        Prefer the protocol surface for portable code.
        """
        return self._raw

    # ------------------------------------------------------------------
    # Connection protocol
    # ------------------------------------------------------------------

    def cursor(self) -> Cursor:
        with self._lock:
            return _SQLiteCursor(self._raw.cursor())

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Cursor:
        cur = self.cursor()
        return cur.execute(sql, params)

    def executemany(
        self, sql: str, seq_of_params: Iterable[Sequence[Any]]
    ) -> Cursor:
        cur = self.cursor()
        return cur.executemany(sql, seq_of_params)

    def executescript(self, script: str) -> None:
        with self._lock:
            self._raw.executescript(script)

    def commit(self) -> None:
        with self._lock:
            self._raw.commit()

    def rollback(self) -> None:
        with self._lock:
            self._raw.rollback()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            try:
                self._raw.close()
            finally:
                self._closed = True

    @property
    def is_closed(self) -> bool:
        return self._closed


__all__ = ["SQLiteConnection"]
