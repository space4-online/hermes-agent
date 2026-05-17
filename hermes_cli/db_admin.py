"""``hermes db`` admin commands — schema migrations & data import.

Wires the two existing pieces (``hermes_db.migrate`` and
``scripts/migrate_sqlite_to_mysql.py``) into the unified ``hermes`` CLI:

    hermes db migrate                  # apply pending DDL to every store
    hermes db migrate --store NAME     # one store
    hermes db status                   # show applied / pending per store
    hermes db import-sqlite            # copy data from legacy *.db files

Backend-agnostic: ``migrate`` runs against whatever backend the active
storage config resolves to (sqlite or mysql). ``import-sqlite`` requires
the active backend to be mysql — see the script for details.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence


def _cmd_migrate(args: argparse.Namespace) -> int:
    """Dispatch ``hermes db migrate`` to ``hermes_db.migrate.main``."""
    from hermes_db.migrate import main as _migrate_main

    forwarded: list[str] = []
    if getattr(args, "store", None):
        forwarded += ["--store", args.store]
    if getattr(args, "backend", None):
        forwarded += ["--backend", args.backend]
    if getattr(args, "dry_run", False):
        forwarded.append("--dry-run")
    if getattr(args, "verbose", False):
        forwarded.append("--verbose")
    return _migrate_main(forwarded)


def _cmd_status(args: argparse.Namespace) -> int:
    """``hermes db status`` — list applied / pending per store."""
    from hermes_db.migrate import main as _migrate_main

    forwarded: list[str] = ["--status"]
    if getattr(args, "store", None):
        forwarded += ["--store", args.store]
    if getattr(args, "backend", None):
        forwarded += ["--backend", args.backend]
    if getattr(args, "verbose", False):
        forwarded.append("--verbose")
    return _migrate_main(forwarded)


def _cmd_import_sqlite(args: argparse.Namespace) -> int:
    """``hermes db import-sqlite`` — copy a legacy SQLite store into MySQL."""
    # Late import: ``scripts/`` isn't a package; load by file path.
    import importlib.util

    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "migrate_sqlite_to_mysql.py"
    if not script_path.exists():
        print(
            f"Error: migration script not found at {script_path}",
            file=sys.stderr,
        )
        return 2

    spec = importlib.util.spec_from_file_location(
        "_hermes_migrate_sqlite_to_mysql", script_path
    )
    if spec is None or spec.loader is None:
        print(
            "Error: failed to load scripts/migrate_sqlite_to_mysql.py",
            file=sys.stderr,
        )
        return 2
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    forwarded: list[str] = ["--store", args.store, "--src", str(args.src)]
    if args.batch:
        forwarded += ["--batch", str(args.batch)]
    if args.dry_run:
        forwarded.append("--dry-run")
    if args.skip_schema:
        forwarded.append("--skip-schema")
    if getattr(args, "verbose", False):
        forwarded.append("--verbose")

    return mod.main(forwarded)


def cmd_db(args: argparse.Namespace) -> int:
    """Top-level dispatcher — routed via ``set_defaults(func=cmd_db)``."""
    sub = getattr(args, "db_command", None)
    if sub == "migrate":
        return _cmd_migrate(args)
    if sub == "status":
        return _cmd_status(args)
    if sub == "import-sqlite":
        return _cmd_import_sqlite(args)
    print(
        "Usage: hermes db {migrate,status,import-sqlite} ...\n"
        "Run 'hermes db --help' for details.",
        file=sys.stderr,
    )
    return 2


def register_cli(db_parser: argparse.ArgumentParser) -> None:
    """Attach the ``hermes db`` subcommand tree to ``db_parser``."""
    db_subparsers = db_parser.add_subparsers(dest="db_command")

    # db migrate
    p_migrate = db_subparsers.add_parser(
        "migrate",
        help="Apply pending storage schema migrations",
        description=(
            "Apply pending DDL migrations from sql/<backend>/<store>/V*.sql "
            "to every known store (or one, with --store). Idempotent — "
            "previously applied versions are tracked in schema_version."
        ),
    )
    p_migrate.add_argument("--store", help="Run only against this store")
    p_migrate.add_argument(
        "--backend",
        choices=("sqlite", "mysql"),
        help="Force a backend (default: from storage config)",
    )
    p_migrate.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover + checksum-verify without executing DDL",
    )
    p_migrate.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging"
    )

    # db status
    p_status = db_subparsers.add_parser(
        "status",
        help="Show applied / pending storage migrations",
    )
    p_status.add_argument("--store", help="Limit to this store")
    p_status.add_argument(
        "--backend",
        choices=("sqlite", "mysql"),
        help="Force a backend (default: from storage config)",
    )
    p_status.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging"
    )

    # db import-sqlite
    p_import = db_subparsers.add_parser(
        "import-sqlite",
        help="Import a legacy SQLite *.db file into the MySQL backend",
        description=(
            "Copy data from a previously-used SQLite store (response_store "
            "or memory_store) into the active MySQL backend. Requires "
            "HERMES_DB_BACKEND=mysql. INSERT IGNORE semantics — re-running "
            "is safe; existing rows are not overwritten."
        ),
    )
    p_import.add_argument(
        "--store",
        required=True,
        choices=("response_store", "memory_store"),
        help="Logical store to import",
    )
    p_import.add_argument(
        "--src",
        required=True,
        type=Path,
        help="Path to the source SQLite *.db file",
    )
    p_import.add_argument(
        "--batch",
        type=int,
        default=500,
        help="Rows per INSERT batch (default: 500)",
    )
    p_import.add_argument(
        "--dry-run",
        action="store_true",
        help="Read + count rows without writing to the target",
    )
    p_import.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip implicit schema migrate (assume DDL already applied)",
    )
    p_import.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging"
    )

    db_parser.set_defaults(func=cmd_db)
