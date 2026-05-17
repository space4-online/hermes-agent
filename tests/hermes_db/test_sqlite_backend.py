"""End-to-end tests for the SQLite backend + factory.

These tests exercise the abstraction against a real on-disk SQLite
file in a temp dir.  No MySQL service is required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_db import config as cfg_mod
from hermes_db import factory as factory_mod
from hermes_db.sqlite_backend import SQLiteConnection


@pytest.fixture(autouse=True)
def _isolate_backend(monkeypatch, tmp_path):
    """Force backend=sqlite, redirect HERMES_HOME, drop the connection cache."""
    cfg_mod._cached = None
    monkeypatch.setattr(cfg_mod, "_load_yaml_storage_section", lambda: {})
    for key in (
        "HERMES_DB_BACKEND",
        "HERMES_DB_HOST",
        "HERMES_DB_PORT",
        "HERMES_DB_USER",
        "HERMES_DB_PASSWORD",
        "HERMES_DB_NAME",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    # Drop cached connections
    for c in list(factory_mod._cache.values()):
        try:
            c.close()
        except Exception:
            pass
    factory_mod._cache.clear()
    yield
    for c in list(factory_mod._cache.values()):
        try:
            c.close()
        except Exception:
            pass
    factory_mod._cache.clear()
    cfg_mod._cached = None


# ---------------------------------------------------------------------------
# SQLiteConnection direct
# ---------------------------------------------------------------------------


class TestSQLiteConnectionDirect:
    def test_basic_crud_round_trip(self, tmp_path):
        path = tmp_path / "demo.db"
        conn = SQLiteConnection(store="demo", path=path)
        try:
            conn.executescript(
                "CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT NOT NULL);"
            )
            conn.execute("INSERT INTO t (v) VALUES (?)", ("hello",))
            conn.execute("INSERT INTO t (v) VALUES (?)", ("world",))
            conn.commit()

            row = conn.execute(
                "SELECT v FROM t WHERE id = ?", (1,)
            ).fetchone()
            assert row is not None
            assert row["v"] == "hello"
            assert row[0] == "hello"  # positional access also works

            rows = conn.execute("SELECT id, v FROM t ORDER BY id").fetchall()
            assert [r["v"] for r in rows] == ["hello", "world"]
            assert path.exists()
        finally:
            conn.close()
            assert conn.is_closed is True

    def test_executemany(self, tmp_path):
        path = tmp_path / "many.db"
        conn = SQLiteConnection(store="demo", path=path)
        try:
            conn.executescript("CREATE TABLE t (id INTEGER, v TEXT);")
            conn.executemany(
                "INSERT INTO t (id, v) VALUES (?, ?)",
                [(1, "a"), (2, "b"), (3, "c")],
            )
            conn.commit()
            n = conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
            assert n == 3
        finally:
            conn.close()

    def test_rollback(self, tmp_path):
        path = tmp_path / "rb.db"
        conn = SQLiteConnection(store="demo", path=path)
        try:
            conn.executescript("CREATE TABLE t (v TEXT);")
            conn.commit()
            conn.execute("INSERT INTO t (v) VALUES (?)", ("dirty",))
            conn.rollback()
            n = conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
            assert n == 0
        finally:
            conn.close()

    def test_double_close_is_idempotent(self, tmp_path):
        conn = SQLiteConnection(store="demo", path=tmp_path / "x.db")
        conn.close()
        conn.close()  # no exception
        assert conn.is_closed is True

    def test_lastrowid(self, tmp_path):
        conn = SQLiteConnection(store="demo", path=tmp_path / "l.db")
        try:
            conn.executescript(
                "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, v TEXT)"
            )
            cur = conn.execute("INSERT INTO t (v) VALUES (?)", ("a",))
            assert cur.lastrowid == 1
            cur = conn.execute("INSERT INTO t (v) VALUES (?)", ("b",))
            assert cur.lastrowid == 2
        finally:
            conn.close()

    def test_raw_property_returns_sqlite3_connection(self, tmp_path):
        import sqlite3

        conn = SQLiteConnection(store="demo", path=tmp_path / "r.db")
        try:
            assert isinstance(conn.raw, sqlite3.Connection)
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# factory.connect()
# ---------------------------------------------------------------------------


class TestFactoryConnect:
    def test_default_path_resolves_under_hermes_home(self, tmp_path):
        c = factory_mod.connect("response_store")
        try:
            assert isinstance(c, SQLiteConnection)
            assert c.path == (tmp_path / "response_store.db").resolve()
        finally:
            pass  # close handled in fixture teardown

    def test_explicit_path_override(self, tmp_path):
        custom = tmp_path / "alt" / "kanban.db"
        c = factory_mod.connect("kanban", path=custom)
        try:
            assert c.path == custom.resolve()
        finally:
            pass

    def test_shared_returns_cached_connection(self, tmp_path):
        c1 = factory_mod.connect("response_store")
        c2 = factory_mod.connect("response_store")
        assert c1 is c2

    def test_shared_false_returns_fresh(self, tmp_path):
        c1 = factory_mod.connect("response_store")
        c2 = factory_mod.connect("response_store", shared=False)
        assert c1 is not c2
        c2.close()

    def test_distinct_paths_get_distinct_connections(self, tmp_path):
        # Two boards live at different files; cache key includes path.
        c1 = factory_mod.connect("kanban", path=tmp_path / "b1.db")
        c2 = factory_mod.connect("kanban", path=tmp_path / "b2.db")
        assert c1 is not c2
        assert c1.path != c2.path

    def test_close_all_clears_cache(self, tmp_path):
        c = factory_mod.connect("response_store")
        assert not c.is_closed
        factory_mod.close_all()
        assert c.is_closed
        assert factory_mod._cache == {}

    def test_get_backend_default_is_sqlite(self):
        assert factory_mod.get_backend() == "sqlite"
