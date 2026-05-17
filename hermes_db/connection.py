"""Common ``Connection`` / ``Cursor`` / ``Row`` shape used by every backend.

The two backends (SQLite, MySQL) provide their own concrete cursors,
but the rest of the codebase only sees these protocol-style classes.

Notes:
- Parameter style is ``qmark`` (``?``) at the call site.  The MySQL
  backend rewrites ``?`` -> ``%s`` transparently.  This keeps the bulk
  of existing SQL strings unchanged.
- Rows act both as a sequence (``row[0]``) and a mapping (``row["id"]``)
  so existing call sites that mix ``cursor.row_factory = sqlite3.Row``
  semantics work unchanged.
"""

from __future__ import annotations

import abc
from typing import Any, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple


class Row(Mapping[str, Any]):
    """Read-only row that supports both ``row[i]`` and ``row["col"]``.

    Backends construct ``Row`` instances from their native rows so that
    consumers of this layer can treat results uniformly.  Iteration
    yields the column names (mapping protocol) — call ``values()`` for
    values, or use integer indexing for tuple-style access.
    """

    __slots__ = ("_columns", "_values", "_index")

    def __init__(self, columns: Sequence[str], values: Sequence[Any]) -> None:
        if len(columns) != len(values):
            raise ValueError(
                f"Row column/value mismatch: {len(columns)} columns vs "
                f"{len(values)} values"
            )
        self._columns: Tuple[str, ...] = tuple(columns)
        self._values: Tuple[Any, ...] = tuple(values)
        self._index = {name: i for i, name in enumerate(self._columns)}

    # Mapping protocol -------------------------------------------------------
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._values[key]
        if isinstance(key, str):
            try:
                return self._values[self._index[key]]
            except KeyError as exc:
                raise KeyError(key) from exc
        raise TypeError(f"Row indices must be int or str, not {type(key).__name__}")

    def __iter__(self) -> Iterator[str]:
        return iter(self._columns)

    def __len__(self) -> int:
        return len(self._columns)

    def __contains__(self, key: object) -> bool:
        return key in self._index

    def keys(self) -> Tuple[str, ...]:  # type: ignore[override]
        return self._columns

    def values(self) -> Tuple[Any, ...]:  # type: ignore[override]
        return self._values

    def items(self) -> List[Tuple[str, Any]]:  # type: ignore[override]
        return list(zip(self._columns, self._values))

    def get(self, key: Any, default: Any = None) -> Any:  # type: ignore[override]
        try:
            return self[key]
        except (KeyError, IndexError):
            return default

    def __repr__(self) -> str:
        return f"Row({dict(zip(self._columns, self._values))!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Row):
            return self._columns == other._columns and self._values == other._values
        if isinstance(other, Mapping):
            return dict(self.items()) == dict(other)
        if isinstance(other, (list, tuple)):
            return list(self._values) == list(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._columns, self._values))


class Cursor(abc.ABC):
    """Cursor protocol shared by all backends."""

    @abc.abstractmethod
    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> "Cursor":
        ...

    @abc.abstractmethod
    def executemany(
        self, sql: str, seq_of_params: Iterable[Sequence[Any]]
    ) -> "Cursor":
        ...

    @abc.abstractmethod
    def fetchone(self) -> Optional[Row]:
        ...

    @abc.abstractmethod
    def fetchall(self) -> List[Row]:
        ...

    @abc.abstractmethod
    def fetchmany(self, size: int = 0) -> List[Row]:
        ...

    @property
    @abc.abstractmethod
    def lastrowid(self) -> Optional[int]:
        ...

    @property
    @abc.abstractmethod
    def rowcount(self) -> int:
        ...

    @abc.abstractmethod
    def close(self) -> None:
        ...

    def __iter__(self) -> Iterator[Row]:
        while True:
            row = self.fetchone()
            if row is None:
                return
            yield row

    def __enter__(self) -> "Cursor":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class Connection(abc.ABC):
    """Connection protocol shared by all backends."""

    #: ``"sqlite"`` or ``"mysql"`` — useful for backend-specific branches
    #: at call sites that genuinely cannot be hidden by dialect helpers
    #: (e.g. SQLite WAL pragmas).
    backend: str = "sqlite"

    #: Logical store name (``"state"``, ``"kanban"``, ...).  Useful for
    #: log labels and metrics.
    store: str = ""

    @abc.abstractmethod
    def cursor(self) -> Cursor:
        ...

    @abc.abstractmethod
    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Cursor:
        ...

    @abc.abstractmethod
    def executemany(
        self, sql: str, seq_of_params: Iterable[Sequence[Any]]
    ) -> Cursor:
        ...

    @abc.abstractmethod
    def executescript(self, script: str) -> None:
        """Execute a multi-statement SQL script.

        For sqlite this maps to ``connection.executescript``.  For
        MySQL it splits on top-level semicolons (respecting quoted
        strings) and runs each statement individually because PyMySQL
        disables ``CLIENT_MULTI_STATEMENTS`` by default.
        """

    @abc.abstractmethod
    def commit(self) -> None:
        ...

    @abc.abstractmethod
    def rollback(self) -> None:
        ...

    @abc.abstractmethod
    def close(self) -> None:
        ...

    @property
    @abc.abstractmethod
    def is_closed(self) -> bool:
        ...

    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        # NB: do NOT close here — by design the factory caches the
        # connection per (backend, store).  Use ``close_all()`` for
        # process shutdown.  The context-manager form is offered only
        # for parity with sqlite3.Connection.
        if exc is not None:
            try:
                self.rollback()
            except Exception:
                pass
        else:
            try:
                self.commit()
            except Exception:
                pass


__all__ = ["Connection", "Cursor", "Row"]
