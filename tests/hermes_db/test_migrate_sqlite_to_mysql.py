"""Smoke tests for ``scripts/migrate_sqlite_to_mysql.py``.

These tests don't require a running MySQL service:

* Backend-gate test exercises the precondition check directly.
* Dry-run + counting test stubs ``hermes_db.connect`` so the migration
  logic can run end-to-end against an in-memory sqlite destination,
  while still validating row counts and table iteration.
"""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "migrate_sqlite_to_mysql.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "_migrate_sqlite_to_mysql_test", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _reset_storage_config(monkeypatch):
    """Each test wipes the lazy storage-config cache + db env."""
    # Clear all HERMES_DB_* vars so monkeypatch sets are deterministic.
    for k in list(os.environ):
        if k.startswith("HERMES_DB_"):
            monkeypatch.delenv(k, raising=False)

    import hermes_db.config as cfg_mod
    cfg_mod._cached = None
    import hermes_db.factory as fac_mod
    fac_mod._cache.clear()

    yield

    cfg_mod._cached = None
    fac_mod._cache.clear()


def test_module_loads_and_exposes_supported_stores():
    mod = _load_module()
    assert mod.SUPPORTED_STORES == ("response_store", "memory_store")
    assert callable(mod.import_store)


def test_backend_gate_rejects_sqlite(monkeypatch, tmp_path):
    """Active backend != mysql must fail loudly without touching sources."""
    monkeypatch.setenv("HERMES_DB_BACKEND", "sqlite")
    mod = _load_module()
    src = tmp_path / "ignored.db"
    src.write_bytes(b"")  # not even a valid sqlite file; check shouldn't reach it

    with pytest.raises(RuntimeError, match="not 'mysql'"):
        mod.import_store(store="response_store", src=src)


def test_unsupported_store_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_DB_BACKEND", "mysql")
    monkeypatch.setenv("HERMES_DB_HOST", "127.0.0.1")
    mod = _load_module()
    src = tmp_path / "kanban.db"
    src.write_bytes(b"")

    with pytest.raises(ValueError, match="unsupported store"):
        mod.import_store(store="kanban", src=src)


def _seed_response_store_sqlite(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE responses (
            response_id TEXT PRIMARY KEY,
            data        TEXT NOT NULL,
            accessed_at REAL NOT NULL
        );
        CREATE TABLE conversations (
            name        TEXT PRIMARY KEY,
            response_id TEXT NOT NULL
        );
        """
    )
    conn.executemany(
        "INSERT INTO responses VALUES (?, ?, ?)",
        [
            ("resp-001", '{"id":"resp-001"}', 1700000000.0),
            ("resp-002", '{"id":"resp-002"}', 1700000100.0),
            ("resp-003", '{"id":"resp-003"}', 1700000200.0),
        ],
    )
    conn.executemany(
        "INSERT INTO conversations VALUES (?, ?)",
        [("session-A", "resp-001"), ("session-B", "resp-002")],
    )
    conn.commit()
    conn.close()


def test_response_store_dry_run_counts(monkeypatch, tmp_path):
    """Dry-run reports row counts even without a real mysql destination."""
    src = tmp_path / "response_store.db"
    _seed_response_store_sqlite(src)

    monkeypatch.setenv("HERMES_DB_BACKEND", "mysql")
    monkeypatch.setenv("HERMES_DB_HOST", "127.0.0.1")

    mod = _load_module()

    # Stub ``hermes_db.connect`` to hand back a fake mysql-flavored
    # connection (just an object that satisfies ``backend == "mysql"`` and
    # absorbs writes — dry-run won't issue any).
    class _FakeConn:
        backend = "mysql"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def executemany(self, *_a, **_kw):  # pragma: no cover - dry-run skips
            raise AssertionError("dry-run must not write")

        def commit(self):  # pragma: no cover - dry-run skips
            raise AssertionError("dry-run must not commit")

    monkeypatch.setattr(mod, "_connect", lambda store: _FakeConn())

    counts = mod.import_store(
        store="response_store",
        src=src,
        batch=2,
        dry_run=True,
        skip_schema=True,
    )
    assert counts == {"responses": 3, "conversations": 2}


def test_memory_store_dry_run_counts(monkeypatch, tmp_path):
    src = tmp_path / "memory_store.db"
    conn = sqlite3.connect(str(src))
    conn.executescript(
        """
        CREATE TABLE facts (
            fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT UNIQUE NOT NULL,
            category TEXT DEFAULT 'general',
            tags TEXT DEFAULT '',
            trust_score REAL DEFAULT 0.5,
            retrieval_count INT DEFAULT 0,
            helpful_count INT DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            hrr_vector BLOB
        );
        CREATE TABLE entities (
            entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            entity_type TEXT DEFAULT 'unknown',
            aliases TEXT DEFAULT '',
            created_at TEXT
        );
        CREATE TABLE fact_entities (
            fact_id INTEGER NOT NULL,
            entity_id INTEGER NOT NULL,
            PRIMARY KEY (fact_id, entity_id)
        );
        CREATE TABLE memory_banks (
            bank_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_name TEXT NOT NULL UNIQUE,
            vector BLOB NOT NULL,
            dim INT NOT NULL,
            fact_count INT DEFAULT 0,
            updated_at TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO facts (fact_id, content) VALUES (?, ?)",
        [(1, "fact one"), (2, "fact two")],
    )
    conn.executemany(
        "INSERT INTO entities (entity_id, name) VALUES (?, ?)",
        [(10, "alice"), (11, "bob"), (12, "carol")],
    )
    conn.executemany(
        "INSERT INTO fact_entities VALUES (?, ?)",
        [(1, 10), (1, 11), (2, 12)],
    )
    conn.executemany(
        "INSERT INTO memory_banks (bank_name, vector, dim) VALUES (?, ?, ?)",
        [("default", b"\x00\x01", 2)],
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("HERMES_DB_BACKEND", "mysql")
    monkeypatch.setenv("HERMES_DB_HOST", "127.0.0.1")
    mod = _load_module()

    class _FakeConn:
        backend = "mysql"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(mod, "_connect", lambda store: _FakeConn())

    counts = mod.import_store(
        store="memory_store",
        src=src,
        batch=10,
        dry_run=True,
        skip_schema=True,
    )
    assert counts == {
        "facts": 2,
        "entities": 3,
        "fact_entities": 3,
        "memory_banks": 1,
    }


def test_main_returns_2_on_runtime_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HERMES_DB_BACKEND", "sqlite")
    mod = _load_module()
    src = tmp_path / "missing.db"
    rc = mod.main(["--store", "response_store", "--src", str(src)])
    assert rc == 2
