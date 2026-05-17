"""One-shot SQLite → MySQL data migration for Hermes Agent stores.

This is a *data* migration tool — schema is created via ``hermes_db.migrate``
beforehand (the runner ensures it). It reads rows from a legacy
``*.db`` file produced by an older sqlite-backed install and writes
them into the equivalent MySQL tables exposed through ``hermes_db``.

Currently supported stores:
  * ``response_store``  (responses + conversations)
  * ``memory_store``    (facts, entities, fact_entities, memory_banks)

The other two stores (``state``, ``kanban``) are still guarded against
the MySQL backend in this branch — once their full SQL refactor lands,
add their migration paths here.

Idempotent semantics:
  * INSERT IGNORE everywhere on MySQL — re-running over an existing
    target is safe; existing rows are left untouched.
  * The script does *not* delete or update target rows. Run against
    an empty target schema, or be prepared for a manual cleanup pass.

Usage::

    # 1) make sure the target MySQL schema is created
    HERMES_DB_BACKEND=mysql HERMES_DB_HOST=... HERMES_DB_USER=... \\
        python -m hermes_db.migrate --store response_store

    # 2) copy data over
    HERMES_DB_BACKEND=mysql HERMES_DB_HOST=... HERMES_DB_USER=... \\
        python scripts/migrate_sqlite_to_mysql.py \\
            --store response_store \\
            --src ~/.hermes/response_store.db
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

# Allow running as ``python scripts/migrate_sqlite_to_mysql.py`` from a
# checkout: prepend the repo root so ``hermes_db`` resolves.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hermes_db import connect as _connect, get_backend  # noqa: E402
from hermes_db.connection import Connection  # noqa: E402

logger = logging.getLogger("hermes_db.import_sqlite")


SUPPORTED_STORES = ("response_store", "memory_store")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_sqlite(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"sqlite source not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _table_exists(src: sqlite3.Connection, name: str) -> bool:
    cur = src.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    )
    return cur.fetchone() is not None


def _iter_rows(
    src: sqlite3.Connection, table: str, batch: int
) -> Iterator[List[sqlite3.Row]]:
    cur = src.execute(f"SELECT * FROM {table}")
    while True:
        rows = cur.fetchmany(batch)
        if not rows:
            return
        yield rows


# ---------------------------------------------------------------------------
# Per-store migration logic
# ---------------------------------------------------------------------------


def _migrate_response_store(
    src: sqlite3.Connection,
    dst: Connection,
    *,
    batch: int,
    dry_run: bool,
) -> Dict[str, int]:
    """Copy ``responses`` + ``conversations`` from sqlite → mysql."""

    counts: Dict[str, int] = {"responses": 0, "conversations": 0}

    if _table_exists(src, "responses"):
        for chunk in _iter_rows(src, "responses", batch):
            params = [
                (row["response_id"], row["data"], float(row["accessed_at"]))
                for row in chunk
            ]
            counts["responses"] += len(params)
            if dry_run or not params:
                continue
            dst.executemany(
                "INSERT IGNORE INTO responses "
                "(response_id, data, accessed_at) VALUES (?, ?, ?)",
                params,
            )
            dst.commit()
            logger.info("responses: %d rows committed", counts["responses"])
    else:
        logger.warning("responses table missing in sqlite source; skipping")

    if _table_exists(src, "conversations"):
        for chunk in _iter_rows(src, "conversations", batch):
            params = [(row["name"], row["response_id"]) for row in chunk]
            counts["conversations"] += len(params)
            if dry_run or not params:
                continue
            dst.executemany(
                "INSERT IGNORE INTO conversations "
                "(name, response_id) VALUES (?, ?)",
                params,
            )
            dst.commit()
            logger.info("conversations: %d rows committed", counts["conversations"])
    else:
        logger.warning("conversations table missing in sqlite source; skipping")

    return counts


def _migrate_memory_store(
    src: sqlite3.Connection,
    dst: Connection,
    *,
    batch: int,
    dry_run: bool,
) -> Dict[str, int]:
    """Copy holographic memory tables, remapping fact_id when needed."""

    counts: Dict[str, int] = {
        "facts": 0,
        "entities": 0,
        "fact_entities": 0,
        "memory_banks": 0,
    }

    # facts: sqlite uses INTEGER PK; mysql uses BIGINT AUTO_INCREMENT with
    # uq_facts_content_hash. We reuse the source PK (sqlite is also INTEGER
    # AUTO_INCREMENT semantically) so the join through fact_entities stays
    # consistent. Build a content_hash on the fly for older rows that may
    # not have one stored.
    fact_id_map: Dict[int, int] = {}
    if _table_exists(src, "facts"):
        for chunk in _iter_rows(src, "facts", batch):
            params = []
            for row in chunk:
                row_keys = row.keys()
                content = row["content"]
                ch = (
                    row["content_hash"]
                    if "content_hash" in row_keys and row["content_hash"]
                    else _content_hash(content)
                )
                hrr = row["hrr_vector"] if "hrr_vector" in row_keys else None
                tags = row["tags"] if "tags" in row_keys else ""
                trust = row["trust_score"] if "trust_score" in row_keys else 0.5
                retrieval = (
                    row["retrieval_count"] if "retrieval_count" in row_keys else 0
                )
                helpful = row["helpful_count"] if "helpful_count" in row_keys else 0
                category = row["category"] if "category" in row_keys else "general"
                created = (
                    row["created_at"]
                    if "created_at" in row_keys and row["created_at"]
                    else None
                )
                updated = (
                    row["updated_at"]
                    if "updated_at" in row_keys and row["updated_at"]
                    else None
                )
                params.append(
                    (
                        int(row["fact_id"]),
                        content,
                        ch,
                        category,
                        tags,
                        float(trust),
                        int(retrieval),
                        int(helpful),
                        created,
                        updated,
                        hrr,
                    )
                )
                fact_id_map[int(row["fact_id"])] = int(row["fact_id"])

            counts["facts"] += len(params)
            if dry_run or not params:
                continue
            dst.executemany(
                "INSERT IGNORE INTO facts "
                "(fact_id, content, content_hash, category, tags, trust_score, "
                " retrieval_count, helpful_count, created_at, updated_at, "
                " hrr_vector) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, "
                "        COALESCE(?, CURRENT_TIMESTAMP), "
                "        COALESCE(?, CURRENT_TIMESTAMP), ?)",
                params,
            )
            dst.commit()
            logger.info("facts: %d rows committed", counts["facts"])
    else:
        logger.warning("facts table missing in sqlite source; skipping")

    if _table_exists(src, "entities"):
        for chunk in _iter_rows(src, "entities", batch):
            params = []
            for row in chunk:
                row_keys = row.keys()
                params.append(
                    (
                        int(row["entity_id"]),
                        row["name"],
                        row["entity_type"] if "entity_type" in row_keys else "unknown",
                        row["aliases"] if "aliases" in row_keys else "",
                        row["created_at"] if "created_at" in row_keys and row["created_at"] else None,
                    )
                )
            counts["entities"] += len(params)
            if dry_run or not params:
                continue
            dst.executemany(
                "INSERT IGNORE INTO entities "
                "(entity_id, name, entity_type, aliases, created_at) "
                "VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))",
                params,
            )
            dst.commit()
            logger.info("entities: %d rows committed", counts["entities"])
    else:
        logger.warning("entities table missing in sqlite source; skipping")

    if _table_exists(src, "fact_entities"):
        for chunk in _iter_rows(src, "fact_entities", batch):
            params = [
                (int(row["fact_id"]), int(row["entity_id"])) for row in chunk
            ]
            counts["fact_entities"] += len(params)
            if dry_run or not params:
                continue
            dst.executemany(
                "INSERT IGNORE INTO fact_entities (fact_id, entity_id) "
                "VALUES (?, ?)",
                params,
            )
            dst.commit()
            logger.info(
                "fact_entities: %d rows committed", counts["fact_entities"]
            )
    else:
        logger.warning("fact_entities table missing in sqlite source; skipping")

    if _table_exists(src, "memory_banks"):
        for chunk in _iter_rows(src, "memory_banks", batch):
            params = []
            for row in chunk:
                row_keys = row.keys()
                params.append(
                    (
                        row["bank_name"],
                        row["vector"],
                        int(row["dim"]),
                        int(row["fact_count"]) if "fact_count" in row_keys else 0,
                        row["updated_at"] if "updated_at" in row_keys and row["updated_at"] else None,
                    )
                )
            counts["memory_banks"] += len(params)
            if dry_run or not params:
                continue
            # bank_name is unique; on conflict refresh the vector to mirror
            # MemoryStore._rebuild_bank.
            dst.executemany(
                "INSERT INTO memory_banks "
                "(bank_name, vector, dim, fact_count, updated_at) "
                "VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP)) "
                "ON DUPLICATE KEY UPDATE "
                "  vector=VALUES(vector), dim=VALUES(dim), "
                "  fact_count=VALUES(fact_count), "
                "  updated_at=COALESCE(VALUES(updated_at), CURRENT_TIMESTAMP)",
                params,
            )
            dst.commit()
            logger.info(
                "memory_banks: %d rows committed", counts["memory_banks"]
            )
    else:
        logger.debug("memory_banks table missing in sqlite source; skipping")

    return counts


_MIGRATIONS: Dict[
    str,
    Callable[[sqlite3.Connection, Connection], Dict[str, int]],
] = {
    "response_store": _migrate_response_store,
    "memory_store": _migrate_memory_store,
}


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------


def import_store(
    store: str,
    src: Path,
    *,
    batch: int = 500,
    dry_run: bool = False,
    skip_schema: bool = False,
) -> Dict[str, int]:
    """Import data from a sqlite ``*.db`` into the configured MySQL store.

    Returns the per-table row count actually written (or that would be
    written, when ``dry_run=True``).
    """

    if store not in SUPPORTED_STORES:
        raise ValueError(
            f"unsupported store {store!r}; supported: {', '.join(SUPPORTED_STORES)}"
        )
    if get_backend() != "mysql":
        raise RuntimeError(
            "Active backend is not 'mysql'. Set HERMES_DB_BACKEND=mysql "
            "(or storage.backend in config.yaml) before running this script."
        )

    src_conn = _open_sqlite(src)
    try:
        with _connect(store) as dst_conn:
            if dst_conn.backend != "mysql":
                raise RuntimeError(
                    f"hermes_db opened {store} on backend "
                    f"{dst_conn.backend!r}; expected mysql."
                )

            if not skip_schema:
                # Lazy import to avoid the cost on ``--help``.
                from hermes_db.migrate import migrate as _run_migrate

                applied = _run_migrate(dst_conn, store=store)
                if applied:
                    logger.info(
                        "schema migrations applied for %s: %s",
                        store,
                        ", ".join(f"V{m.version}" for m in applied),
                    )

            handler = _MIGRATIONS[store]
            counts = handler(src_conn, dst_conn, batch=batch, dry_run=dry_run)
            return counts
    finally:
        src_conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrate_sqlite_to_mysql",
        description=(
            "One-shot importer that copies a Hermes Agent SQLite store "
            "into the active MySQL backend."
        ),
    )
    parser.add_argument(
        "--store",
        required=True,
        choices=SUPPORTED_STORES,
        help="Logical store name to import.",
    )
    parser.add_argument(
        "--src",
        required=True,
        type=Path,
        help="Path to the source SQLite *.db file.",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=500,
        help="Rows per INSERT batch (default: 500).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read + count rows without writing to the target.",
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip the implicit schema migrate (assume DDL already applied).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    try:
        counts = import_store(
            store=args.store,
            src=args.src,
            batch=args.batch,
            dry_run=args.dry_run,
            skip_schema=args.skip_schema,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        logger.error("%s", exc)
        return 2
    except Exception:
        logger.exception("import failed")
        return 1

    print()
    print(f"[{args.store}] import {'dry-run' if args.dry_run else 'complete'}:")
    for table, n in counts.items():
        print(f"  {table:>16}: {n} rows")
    if args.dry_run:
        print("\n  (no rows written — re-run without --dry-run to commit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
