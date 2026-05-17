"""Unit tests for hermes_db.config storage resolution.

Resolution priority is:
1. Environment variables (HERMES_DB_*)
2. ``storage:`` section in config.yaml
3. Hard-coded defaults

Tests below isolate each layer; they never touch the real config.yaml.
"""

from __future__ import annotations

import pytest

from hermes_db import config as cfg_mod


@pytest.fixture(autouse=True)
def _isolate_cache_and_env(monkeypatch):
    """Reset the resolver cache and clear HERMES_DB_* env vars per test."""
    # Clear cache so each test re-resolves from scratch.
    cfg_mod._cached = None
    # Stub ``_load_yaml_storage_section`` to return empty unless the
    # individual test overrides it — keeps tests hermetic.
    monkeypatch.setattr(cfg_mod, "_load_yaml_storage_section", lambda: {})
    # Clear known env vars
    for key in (
        "HERMES_DB_BACKEND",
        "HERMES_DB_HOST",
        "HERMES_DB_PORT",
        "HERMES_DB_USER",
        "HERMES_DB_PASSWORD",
        "HERMES_DB_NAME",
        "HERMES_DB_CHARSET",
        "HERMES_DB_POOL_SIZE",
        "HERMES_DB_CONNECT_TIMEOUT",
    ):
        monkeypatch.delenv(key, raising=False)
    yield
    cfg_mod._cached = None


class TestDefaults:
    def test_default_backend_is_sqlite(self):
        c = cfg_mod.reload_storage_config()
        assert c.backend == "sqlite"
        assert c.is_sqlite() is True
        assert c.is_mysql() is False

    def test_default_mysql_subconfig_is_populated(self):
        c = cfg_mod.reload_storage_config()
        # Defaults exist even when backend is sqlite — they're only
        # validated when actually selected.
        assert c.mysql.host == "127.0.0.1"
        assert c.mysql.port == 3306
        assert c.mysql.charset == "utf8mb4"


class TestEnvOverride:
    def test_env_selects_mysql(self, monkeypatch):
        monkeypatch.setenv("HERMES_DB_BACKEND", "mysql")
        monkeypatch.setenv("HERMES_DB_HOST", "db.internal")
        monkeypatch.setenv("HERMES_DB_USER", "hermes_user")
        monkeypatch.setenv("HERMES_DB_NAME", "hermes_db")
        c = cfg_mod.reload_storage_config()
        assert c.backend == "mysql"
        assert c.mysql.host == "db.internal"
        assert c.mysql.user == "hermes_user"
        assert c.mysql.database == "hermes_db"

    def test_unknown_backend_falls_back_to_sqlite(self, monkeypatch):
        monkeypatch.setenv("HERMES_DB_BACKEND", "redis")
        c = cfg_mod.reload_storage_config()
        assert c.backend == "sqlite"

    def test_invalid_mysql_config_falls_back_to_sqlite(self, monkeypatch):
        # backend=mysql but the configured port is out of range —
        # validate() raises and we downgrade to sqlite to keep the
        # agent bootable.  This guards the soft-fallback in ``_resolve``.
        monkeypatch.setattr(
            cfg_mod,
            "_load_yaml_storage_section",
            lambda: {
                "backend": "mysql",
                "mysql": {
                    "host": "h",
                    "user": "u",
                    "database": "d",
                    "port": 70000,
                },
            },
        )
        c = cfg_mod.reload_storage_config()
        assert c.backend == "sqlite"


class TestYamlSection:
    def test_yaml_provides_backend(self, monkeypatch):
        monkeypatch.setattr(
            cfg_mod,
            "_load_yaml_storage_section",
            lambda: {
                "backend": "mysql",
                "mysql": {
                    "host": "yaml-host",
                    "user": "yaml-user",
                    "database": "yaml-db",
                },
            },
        )
        c = cfg_mod.reload_storage_config()
        assert c.backend == "mysql"
        assert c.mysql.host == "yaml-host"
        assert c.mysql.user == "yaml-user"

    def test_env_overrides_yaml(self, monkeypatch):
        monkeypatch.setattr(
            cfg_mod,
            "_load_yaml_storage_section",
            lambda: {
                "backend": "mysql",
                "mysql": {
                    "host": "yaml-host",
                    "user": "yaml-user",
                    "database": "yaml-db",
                },
            },
        )
        monkeypatch.setenv("HERMES_DB_HOST", "env-host")
        c = cfg_mod.reload_storage_config()
        assert c.backend == "mysql"
        assert c.mysql.host == "env-host"  # env wins
        assert c.mysql.user == "yaml-user"  # untouched yaml value


class TestPerStoreDatabase:
    def test_database_for_falls_back_to_default(self, monkeypatch):
        monkeypatch.setattr(
            cfg_mod,
            "_load_yaml_storage_section",
            lambda: {
                "backend": "mysql",
                "mysql": {
                    "host": "h",
                    "user": "u",
                    "database": "default_db",
                },
            },
        )
        c = cfg_mod.reload_storage_config()
        assert c.mysql.database_for("state") == "default_db"

    def test_per_store_override_used(self, monkeypatch):
        monkeypatch.setattr(
            cfg_mod,
            "_load_yaml_storage_section",
            lambda: {
                "backend": "mysql",
                "mysql": {
                    "host": "h",
                    "user": "u",
                    "database": "default_db",
                    "per_store_database": {"state": "hermes_state"},
                },
            },
        )
        c = cfg_mod.reload_storage_config()
        assert c.mysql.database_for("state") == "hermes_state"
        assert c.mysql.database_for("kanban") == "default_db"


class TestMySQLValidate:
    def test_validate_passes_with_required_fields(self):
        m = cfg_mod.MySQLConfig(host="h", user="u", database="d")
        m.validate()  # should not raise

    @pytest.mark.parametrize(
        "kwargs, hint",
        [
            ({"host": "", "user": "u", "database": "d"}, "host"),
            ({"host": "h", "user": "", "database": "d"}, "user"),
            ({"host": "h", "user": "u", "database": ""}, "database"),
            ({"host": "h", "user": "u", "database": "d", "port": 0}, "port"),
            ({"host": "h", "user": "u", "database": "d", "port": 70000}, "port"),
        ],
    )
    def test_validate_rejects_invalid(self, kwargs, hint):
        m = cfg_mod.MySQLConfig(**kwargs)
        with pytest.raises(ValueError, match=hint):
            m.validate()
