"""Per-engine SQL helpers.

The two engines we support diverge on a handful of constructs:
- Parameter style: ``?`` (sqlite) vs ``%s`` (PyMySQL)
- Auto-increment: ``INTEGER PRIMARY KEY AUTOINCREMENT`` vs ``BIGINT AUTO_INCREMENT PRIMARY KEY``
- Full-text search: ``MATCH ?`` (FTS5) vs ``MATCH(col) AGAINST(? IN BOOLEAN MODE)``
- Multi-statement scripts: sqlite supports ``executescript``; PyMySQL needs splitting.

Higher layers should call into this module instead of branching inline
on ``conn.backend == "mysql"``.  Keeping the dialect logic localized
makes it easy to add a third engine (e.g. PostgreSQL) later.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple


# ---------------------------------------------------------------------------
# Parameter style translation
# ---------------------------------------------------------------------------

# Match ``?`` placeholders that are NOT inside a single- or double-quoted
# string literal.  We deliberately do not try to be a full SQL parser:
# the codebase does not embed ``?`` literals in strings, and SQL strings
# inside our own code never contain stray quotes.  Stays simple and fast.
_QMARK_RE = re.compile(
    r"""
    (?P<str>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
    | (?P<q>\?)
    """,
    re.VERBOSE,
)


def qmark_to_pyformat(sql: str) -> str:
    """Rewrite ``?`` placeholders to ``%s`` for PyMySQL.

    Quoted string literals are preserved verbatim so a ``?`` inside
    ``'foo?'`` does not get mistakenly translated.
    """

    def _sub(match: "re.Match[str]") -> str:
        if match.group("str") is not None:
            return match.group("str")
        return "%s"

    return _QMARK_RE.sub(_sub, sql)


# ---------------------------------------------------------------------------
# DDL helpers
# ---------------------------------------------------------------------------


def autoincrement_pk(backend: str) -> str:
    """Return the engine-specific clause for ``id`` integer PK columns."""

    if backend == "mysql":
        return "BIGINT AUTO_INCREMENT PRIMARY KEY"
    return "INTEGER PRIMARY KEY AUTOINCREMENT"


def schema_version_table_sql(backend: str, table: str = "schema_version") -> str:
    """DDL for the Flyway-style schema version tracker."""

    if backend == "mysql":
        return f"""
            CREATE TABLE IF NOT EXISTS `{table}` (
                installed_rank  INT          NOT NULL,
                version         VARCHAR(64)  NOT NULL,
                description     VARCHAR(200) NOT NULL,
                script          VARCHAR(255) NOT NULL,
                checksum        VARCHAR(64)  NOT NULL,
                installed_on    DATETIME     NOT NULL,
                execution_time  INT          NOT NULL,
                success         TINYINT(1)   NOT NULL,
                PRIMARY KEY (installed_rank),
                UNIQUE KEY uq_version (version)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    return f"""
        CREATE TABLE IF NOT EXISTS {table} (
            installed_rank  INTEGER PRIMARY KEY,
            version         TEXT    NOT NULL UNIQUE,
            description     TEXT    NOT NULL,
            script          TEXT    NOT NULL,
            checksum        TEXT    NOT NULL,
            installed_on    TEXT    NOT NULL,
            execution_time  INTEGER NOT NULL,
            success         INTEGER NOT NULL
        )
    """


# ---------------------------------------------------------------------------
# Full-text search adapter
# ---------------------------------------------------------------------------


def fts_match(
    backend: str,
    *,
    table: str,
    column: str,
    query: str,
    boolean_mode: bool = True,
) -> Tuple[str, Tuple[str]]:
    """Return ``(WHERE-fragment, params)`` for a full-text query.

    SQLite (FTS5):
        ``<table> MATCH ?``  with the original query as the parameter.

    MySQL (FULLTEXT WITH PARSER ngram):
        ``MATCH(<table>.<column>) AGAINST(? IN [BOOLEAN ]MODE)`` —
        wrapped queries containing CJK characters work with the
        ``ngram`` parser when the FULLTEXT index was created with it.

    The caller chooses the table/column appropriate to its schema.
    """

    if backend == "mysql":
        mode = "IN BOOLEAN MODE" if boolean_mode else "IN NATURAL LANGUAGE MODE"
        return (f"MATCH({table}.{column}) AGAINST(? {mode})", (query,))
    return (f"{table} MATCH ?", (query,))


# ---------------------------------------------------------------------------
# Multi-statement script splitter (for MySQL)
# ---------------------------------------------------------------------------

# Split on semicolons that are NOT inside string literals or
# ``BEGIN ... END`` trigger bodies.  Our DDL never uses triggers, so a
# simple quote-aware tokenizer is enough.
_SCRIPT_SPLIT_RE = re.compile(
    r"""
      '(?:[^'\\]|\\.)*'        # single-quoted string
    | "(?:[^"\\]|\\.)*"        # double-quoted string
    | --[^\n]*                  # line comment
    | /\*[\s\S]*?\*/            # block comment
    | ;                         # statement terminator
    """,
    re.VERBOSE,
)


def split_sql_script(script: str) -> List[str]:
    """Split a multi-statement SQL script on top-level semicolons.

    Strips leading/trailing whitespace from each statement and skips
    empty fragments.  Comments are kept inline (they're harmless to
    pass through to the engine).
    """

    statements: List[str] = []
    last = 0
    for m in _SCRIPT_SPLIT_RE.finditer(script):
        if m.group(0) == ";":
            stmt = script[last:m.start()].strip()
            if stmt:
                statements.append(stmt)
            last = m.end()
    tail = script[last:].strip()
    if tail:
        statements.append(tail)
    return statements


__all__ = [
    "qmark_to_pyformat",
    "autoincrement_pk",
    "schema_version_table_sql",
    "fts_match",
    "split_sql_script",
]
