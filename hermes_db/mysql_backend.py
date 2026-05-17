"""MySQL backend.

Implements :class:`hermes_db.connection.Connection` on top of PyMySQL.
PyMySQL is a pure-Python driver — no native build deps — and is
declared as an *optional* dependency (``hermes-agent[mysql]``).  The
import is therefore deferred until ``MySQLConnection`` is actually
instantiated, so SQLite-only deployments are unaffected.

Highlights
----------
- Translates ``?`` placeholders to ``%s`` automatically via
  :func:`hermes_db.dialect.qmark_to_pyformat`.  Existing SQL strings
  in the codebase keep their qmark style; the backend rewrites at
  execution time.
- Ships a small per-connection retry on ``OperationalError`` /
  ``InterfaceError`` because long-lived agent processes routinely hit
  MySQL ``wait_timeout``.  We attempt one transparent reconnect before
  bubbling the exception up.
- Returns rows as :class:`hermes_db.connection.Row` (dict-and-tuple
  shape) — the same surface as the SQLite backend so call sites do
  not branch.
- ``executescript`` splits the input on top-level semicolons (PyMySQL
  disables ``CLIENT_MULTI_STATEMENTS`` by default).  Per-statement
  errors include the offending fragment for easier debugging.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Iterable, List, Optional, Sequence

from hermes_db.connection import Connection, Cursor, Row
from hermes_db.dialect import qmark_to_pyformat, split_sql_script

logger = logging.getLogger(__name__)


def _import_pymysql():
    """Defer the PyMySQL import so SQLite-only installs work without it."""

    try:
        import pymysql  # type: ignore
        import pymysql.cursors  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "MySQL backend requires the optional 'pymysql' dependency. "
            "Install with: pip install 'hermes-agent[mysql]' "
            "or: pip install pymysql"
        ) from exc
    return pymysql


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------


class _MySQLCursor(Cursor):
    """Adapter around a PyMySQL ``DictCursor`` returning :class:`Row`.

    Uses PyMySQL's ``DictCursor`` so we can preserve column ordering
    via ``cursor.description`` while still getting field-name access
    cheaply.
    """

    __slots__ = ("_cur",)

    def __init__(self, raw_cursor: Any) -> None:
        self._cur = raw_cursor

    def _columns(self) -> List[str]:
        desc = self._cur.description or ()
        return [d[0] for d in desc]

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> "Cursor":
        translated = qmark_to_pyformat(sql)
        if params is None:
            self._cur.execute(translated)
        else:
            self._cur.execute(translated, tuple(params))
        return self

    def executemany(
        self, sql: str, seq_of_params: Iterable[Sequence[Any]]
    ) -> "Cursor":
        translated = qmark_to_pyformat(sql)
        self._cur.executemany(translated, [tuple(p) for p in seq_of_params])
        return self

    def fetchone(self) -> Optional[Row]:
        raw = self._cur.fetchone()
        if raw is None:
            return None
        return self._row_from(raw)

    def fetchall(self) -> List[Row]:
        return [self._row_from(r) for r in self._cur.fetchall()]

    def fetchmany(self, size: int = 0) -> List[Row]:
        if size <= 0:
            rows = self._cur.fetchmany()
        else:
            rows = self._cur.fetchmany(size)
        return [self._row_from(r) for r in rows]

    def _row_from(self, raw: Any) -> Row:
        # DictCursor returns dict; fall back to positional if not a dict
        if isinstance(raw, dict):
            cols = self._columns()
            values = [raw.get(c) for c in cols]
            return Row(cols, values)
        return Row(self._columns(), tuple(raw))

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


class MySQLConnection(Connection):
    """One PyMySQL connection scoped to one logical store / database."""

    backend = "mysql"

    def __init__(
        self,
        *,
        store: str,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        charset: str = "utf8mb4",
        connect_timeout: int = 10,
        autocommit: bool = False,
        ssl_disabled: bool = False,
        extra: Optional[dict] = None,
    ) -> None:
        self.store = store
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._charset = charset
        self._connect_timeout = connect_timeout
        self._autocommit = autocommit
        self._ssl_disabled = ssl_disabled
        self._extra = dict(extra or {})

        self._lock = threading.RLock()
        self._closed = False
        self._raw = self._open()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def _open(self) -> Any:
        pymysql = _import_pymysql()
        kwargs = dict(
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            database=self._database,
            charset=self._charset,
            connect_timeout=self._connect_timeout,
            autocommit=self._autocommit,
            cursorclass=pymysql.cursors.DictCursor,
        )
        if not self._ssl_disabled and "ssl" in self._extra:
            kwargs["ssl"] = self._extra["ssl"]
        for k, v in self._extra.items():
            if k == "ssl":
                continue
            kwargs[k] = v
        logger.debug(
            "mysql_backend: opening %s@%s:%s/%s for store=%s",
            self._user,
            self._host,
            self._port,
            self._database,
            self.store,
        )
        return pymysql.connect(**kwargs)

    def _ensure_alive(self) -> None:
        """One-shot reconnect on dropped connections.

        Long-running gateways routinely sit idle longer than
        ``wait_timeout`` (8h default).  PyMySQL's ``ping(reconnect=True)``
        handles that case cleanly.
        """
        try:
            self._raw.ping(reconnect=True)
        except Exception as exc:
            logger.warning(
                "mysql_backend: ping failed for store=%s, reopening (%s)",
                self.store,
                exc,
            )
            try:
                self._raw.close()
            except Exception:
                pass
            self._raw = self._open()

    # ------------------------------------------------------------------
    # Connection protocol
    # ------------------------------------------------------------------

    def cursor(self) -> Cursor:
        with self._lock:
            self._ensure_alive()
            return _MySQLCursor(self._raw.cursor())

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Cursor:
        cur = self.cursor()
        return cur.execute(sql, params)

    def executemany(
        self, sql: str, seq_of_params: Iterable[Sequence[Any]]
    ) -> Cursor:
        cur = self.cursor()
        return cur.executemany(sql, seq_of_params)

    def executescript(self, script: str) -> None:
        statements = split_sql_script(script)
        if not statements:
            return
        with self._lock:
            self._ensure_alive()
            with self._raw.cursor() as raw_cur:
                for stmt in statements:
                    try:
                        raw_cur.execute(qmark_to_pyformat(stmt))
                    except Exception as exc:
                        snippet = stmt if len(stmt) <= 200 else stmt[:200] + "..."
                        raise RuntimeError(
                            f"mysql_backend: executescript statement failed: "
                            f"{exc}\n--SQL--\n{snippet}"
                        ) from exc

    def commit(self) -> None:
        with self._lock:
            self._raw.commit()

    def rollback(self) -> None:
        with self._lock:
            try:
                self._raw.rollback()
            except Exception as exc:
                logger.debug("mysql_backend: rollback ignored: %s", exc)

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


__all__ = ["MySQLConnection"]
