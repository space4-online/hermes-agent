"""Flyway-style schema migration runner.

Usage from Python::

    from hermes_db import connect
    from hermes_db.migrate import migrate

    with connect("state") as conn:
        migrate(conn, store="state")

Usage from the shell::

    python -m hermes_db.migrate                    # all known stores
    python -m hermes_db.migrate --store state      # one store
    python -m hermes_db.migrate --status           # list applied / pending

Layout
------
::

    sql/
      mysql/
        state/V1__init.sql
        state/V2__add_xyz.sql
        kanban/V1__init.sql
        ...
      sqlite/        # optional — currently the SQLite path lives in
                     # hermes_state.SCHEMA_SQL etc., kept inline for
                     # back-compat.

Each ``V<N>__<description>.sql`` file is applied at most once per
target database.  Applied versions are tracked in the ``schema_version``
table (see :func:`hermes_db.dialect.schema_version_table_sql`).

Idempotency rules
-----------------
- Files are sorted by numeric version, not lexicographic.
- A failed migration aborts the whole run; the runner does NOT mark the
  failed version as applied.  Re-running picks up where it stopped.
- The checksum (sha256 of the file body) is recorded so out-of-band
  edits to an already-applied file produce a loud warning instead of
  silent drift.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import hashlib
import logging
import re
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from hermes_db import connect as _connect
from hermes_db.config import KNOWN_STORES, get_storage_config
from hermes_db.connection import Connection
from hermes_db.dialect import schema_version_table_sql, split_sql_script

logger = logging.getLogger(__name__)


_FILE_RE = re.compile(r"^V(?P<num>\d+)__(?P<desc>[A-Za-z0-9_\-]+)\.sql$")


@dataclasses.dataclass(frozen=True)
class _Migration:
    version: str            # e.g. "1"
    description: str        # human-readable from filename
    script: str             # filename
    body: str               # file contents
    checksum: str           # sha256 hex


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    # ``hermes_db/migrate.py`` -> repo root
    return Path(__file__).resolve().parent.parent


def _migrations_dir(backend: str, store: str) -> Path:
    return _project_root() / "sql" / backend / store


def _checksum(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def discover(backend: str, store: str) -> List[_Migration]:
    """Return migrations for ``store`` sorted by numeric version."""

    base = _migrations_dir(backend, store)
    if not base.exists():
        return []
    found: List[Tuple[int, _Migration]] = []
    for path in base.iterdir():
        if not path.is_file():
            continue
        m = _FILE_RE.match(path.name)
        if not m:
            continue
        body = path.read_text(encoding="utf-8")
        found.append(
            (
                int(m.group("num")),
                _Migration(
                    version=m.group("num"),
                    description=m.group("desc").replace("_", " "),
                    script=path.name,
                    body=body,
                    checksum=_checksum(body),
                ),
            )
        )
    found.sort(key=lambda t: t[0])
    return [m for _, m in found]


# ---------------------------------------------------------------------------
# schema_version table helpers
# ---------------------------------------------------------------------------


def _ensure_schema_version(conn: Connection) -> None:
    sql = schema_version_table_sql(conn.backend)
    conn.executescript(sql)
    conn.commit()


def _applied_versions(conn: Connection) -> List[Tuple[str, str]]:
    """Return ``[(version, checksum), ...]`` for successful entries."""

    cur = conn.execute(
        "SELECT version, checksum, success FROM schema_version "
        "ORDER BY installed_rank"
    )
    out: List[Tuple[str, str]] = []
    for row in cur.fetchall():
        success = row["success"]
        if isinstance(success, bytes):  # MySQL TINYINT(1) sometimes
            success = int(success.decode())
        if int(success) == 1:
            out.append((str(row["version"]), str(row["checksum"])))
    return out


def _next_rank(conn: Connection) -> int:
    cur = conn.execute(
        "SELECT MAX(installed_rank) AS r FROM schema_version"
    )
    row = cur.fetchone()
    if row is None or row["r"] is None:
        return 1
    return int(row["r"]) + 1


def _record(
    conn: Connection,
    *,
    rank: int,
    mig: _Migration,
    duration_ms: int,
    success: bool,
) -> None:
    conn.execute(
        "INSERT INTO schema_version "
        "(installed_rank, version, description, script, checksum, "
        " installed_on, execution_time, success) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            rank,
            mig.version,
            mig.description,
            mig.script,
            mig.checksum,
            _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            duration_ms,
            1 if success else 0,
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def migrate(
    conn: Connection,
    *,
    store: str,
    backend: Optional[str] = None,
    dry_run: bool = False,
) -> List[_Migration]:
    """Apply all pending migrations for ``store`` on ``conn``.

    Returns the list of migrations that were applied (empty if the
    database was already up-to-date).

    Setting ``dry_run=True`` runs discovery + checksum verification
    but does not execute any DDL.
    """

    backend = backend or conn.backend
    _ensure_schema_version(conn)
    applied = {v: cs for v, cs in _applied_versions(conn)}
    pending: List[_Migration] = []

    for mig in discover(backend, store):
        if mig.version in applied:
            if applied[mig.version] != mig.checksum:
                logger.warning(
                    "schema drift detected: %s/%s checksum changed since "
                    "it was first applied (db=%s, file=%s). Manual "
                    "review required.",
                    store,
                    mig.version,
                    applied[mig.version],
                    mig.checksum,
                )
            continue
        pending.append(mig)

    if dry_run or not pending:
        return pending

    rank = _next_rank(conn)
    for mig in pending:
        logger.info(
            "applying migration %s/%s [%s] (%s)",
            store,
            mig.version,
            mig.description,
            mig.script,
        )
        started = time.monotonic()
        try:
            statements = split_sql_script(mig.body) if backend == "mysql" else [mig.body]
            for stmt in statements:
                stripped = stmt.strip()
                if not stripped or stripped.startswith("--"):
                    continue
                if backend == "mysql":
                    conn.execute(stripped)
                else:
                    conn.executescript(stripped)
            duration_ms = int((time.monotonic() - started) * 1000)
            _record(conn, rank=rank, mig=mig, duration_ms=duration_ms, success=True)
        except Exception:
            duration_ms = int((time.monotonic() - started) * 1000)
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                _record(conn, rank=rank, mig=mig, duration_ms=duration_ms, success=False)
            except Exception as exc:
                logger.debug("could not record failed migration: %s", exc)
            raise
        rank += 1

    return pending


def status(conn: Connection, *, store: str, backend: Optional[str] = None) -> dict:
    """Return ``{"applied": [...], "pending": [...]}`` for ``store``."""

    backend = backend or conn.backend
    _ensure_schema_version(conn)
    applied = dict(_applied_versions(conn))
    found = discover(backend, store)
    pending = [m for m in found if m.version not in applied]
    return {
        "store": store,
        "backend": backend,
        "applied": [m for m in found if m.version in applied],
        "pending": pending,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _iter_targets(arg_store: Optional[str]) -> Iterable[str]:
    if arg_store:
        return (arg_store,)
    return KNOWN_STORES


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hermes_db.migrate",
        description="Apply pending Hermes Agent schema migrations.",
    )
    parser.add_argument(
        "--store",
        help="Target one store (default: every store in KNOWN_STORES).",
    )
    parser.add_argument(
        "--backend",
        choices=("sqlite", "mysql"),
        help="Force a backend (default: from storage config).",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="List applied / pending migrations without applying.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover + checksum-verify without executing DDL.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging."
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    cfg = get_storage_config()
    backend = args.backend or cfg.backend

    rc = 0
    for store in _iter_targets(args.store):
        try:
            with _connect(store) as conn:
                if conn.backend != backend:
                    logger.warning(
                        "store %s opened on backend %s (config says %s) — skipping",
                        store,
                        conn.backend,
                        backend,
                    )
                    continue
                if args.status:
                    info = status(conn, store=store)
                    print(f"[{store}] backend={info['backend']}")
                    print("  applied:")
                    for m in info["applied"]:
                        print(f"    V{m.version}  {m.script}")
                    print("  pending:")
                    for m in info["pending"]:
                        print(f"    V{m.version}  {m.script}")
                else:
                    applied = migrate(conn, store=store, dry_run=args.dry_run)
                    if applied:
                        print(
                            f"[{store}] applied {len(applied)} migration(s): "
                            + ", ".join(f"V{m.version}" for m in applied)
                        )
                    else:
                        print(f"[{store}] up-to-date")
        except Exception as exc:
            logger.error("migration failed for store=%s: %s", store, exc)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
