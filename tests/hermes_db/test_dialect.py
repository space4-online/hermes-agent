"""Unit tests for hermes_db.dialect helpers.

Covers the per-engine SQL helpers that hide the small differences
between SQLite and MySQL.  No live database connection is required —
these are pure-string transformations.
"""

from __future__ import annotations

import pytest

from hermes_db import dialect


# ---------------------------------------------------------------------------
# qmark_to_pyformat
# ---------------------------------------------------------------------------


class TestQmarkToPyformat:
    def test_simple(self):
        assert dialect.qmark_to_pyformat("SELECT * FROM t WHERE id = ?") == (
            "SELECT * FROM t WHERE id = %s"
        )

    def test_multiple(self):
        sql = "INSERT INTO t (a, b, c) VALUES (?, ?, ?)"
        assert dialect.qmark_to_pyformat(sql) == (
            "INSERT INTO t (a, b, c) VALUES (%s, %s, %s)"
        )

    def test_question_mark_inside_string_literal_is_preserved(self):
        # ``?`` inside a quoted string must not be substituted.
        sql = "SELECT * FROM t WHERE label = 'why?' AND id = ?"
        assert dialect.qmark_to_pyformat(sql) == (
            "SELECT * FROM t WHERE label = 'why?' AND id = %s"
        )

    def test_double_quoted_string_preserved(self):
        sql = 'SELECT * FROM t WHERE label = "what?" AND id = ?'
        assert dialect.qmark_to_pyformat(sql) == (
            'SELECT * FROM t WHERE label = "what?" AND id = %s'
        )

    def test_no_qmark_passes_through(self):
        sql = "SELECT 1"
        assert dialect.qmark_to_pyformat(sql) == sql


# ---------------------------------------------------------------------------
# fts_match
# ---------------------------------------------------------------------------


class TestFtsMatch:
    def test_sqlite_returns_match_clause(self):
        clause, params = dialect.fts_match(
            "sqlite", table="facts_fts", column="content", query="python"
        )
        assert clause == "facts_fts MATCH ?"
        assert params == ("python",)

    def test_mysql_boolean_mode_default(self):
        clause, params = dialect.fts_match(
            "mysql", table="facts", column="content", query="python"
        )
        assert "MATCH(facts.content)" in clause
        assert "BOOLEAN MODE" in clause
        assert params == ("python",)

    def test_mysql_natural_language_mode(self):
        clause, params = dialect.fts_match(
            "mysql",
            table="facts",
            column="content",
            query="python",
            boolean_mode=False,
        )
        assert "NATURAL LANGUAGE MODE" in clause
        assert params == ("python",)


# ---------------------------------------------------------------------------
# split_sql_script
# ---------------------------------------------------------------------------


class TestSplitSqlScript:
    def test_single_statement(self):
        assert dialect.split_sql_script("SELECT 1;") == ["SELECT 1"]

    def test_no_trailing_semicolon(self):
        assert dialect.split_sql_script("SELECT 1") == ["SELECT 1"]

    def test_multiple_statements(self):
        script = "CREATE TABLE a (x INT);\nCREATE TABLE b (y INT);\n"
        assert dialect.split_sql_script(script) == [
            "CREATE TABLE a (x INT)",
            "CREATE TABLE b (y INT)",
        ]

    def test_semicolon_inside_string_literal_is_preserved(self):
        # The splitter must not split on a ``;`` that lives inside a
        # quoted SQL string literal.
        script = "INSERT INTO t (s) VALUES ('a;b'); SELECT 1;"
        assert dialect.split_sql_script(script) == [
            "INSERT INTO t (s) VALUES ('a;b')",
            "SELECT 1",
        ]

    def test_empty_input(self):
        assert dialect.split_sql_script("") == []

    def test_whitespace_only(self):
        assert dialect.split_sql_script("\n\n  \n") == []


# ---------------------------------------------------------------------------
# autoincrement_pk + schema_version_table_sql
# ---------------------------------------------------------------------------


class TestDdlHelpers:
    def test_autoincrement_pk_sqlite(self):
        assert dialect.autoincrement_pk("sqlite") == (
            "INTEGER PRIMARY KEY AUTOINCREMENT"
        )

    def test_autoincrement_pk_mysql(self):
        assert dialect.autoincrement_pk("mysql") == (
            "BIGINT AUTO_INCREMENT PRIMARY KEY"
        )

    def test_schema_version_sqlite_uses_text(self):
        ddl = dialect.schema_version_table_sql("sqlite")
        assert "schema_version" in ddl
        assert "INTEGER PRIMARY KEY" in ddl
        # No MySQL-specific tokens
        assert "ENGINE=InnoDB" not in ddl

    def test_schema_version_mysql_uses_innodb(self):
        ddl = dialect.schema_version_table_sql("mysql")
        assert "ENGINE=InnoDB" in ddl
        assert "VARCHAR(64)" in ddl
        assert "schema_version" in ddl
