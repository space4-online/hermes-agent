"""Tests for AUXILIARY_<TASK>_* env var fallback when config.yaml fields are
empty or hold unresolved ${VAR} placeholders.

Regression: previously a deployment with `auxiliary.vision.api_key: ""` in
config.yaml would silently lose its credential even when AUXILIARY_VISION_API_KEY
was injected by docker-compose, because the empty config field short-circuited
the resolver before the env var could be consulted.
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


from agent.auxiliary_client import _resolve_task_provider_model  # noqa: E402


def _clear_aux_env(monkeypatch, task: str):
    for suffix in ("PROVIDER", "MODEL", "BASE_URL", "API_KEY"):
        monkeypatch.delenv(f"AUXILIARY_{task.upper()}_{suffix}", raising=False)


class TestEnvFallbackForEmptyConfig:
    """When config fields are empty, fall back to AUXILIARY_<TASK>_* env vars."""

    def test_empty_api_key_falls_back_to_env(self, monkeypatch):
        _clear_aux_env(monkeypatch, "vision")
        monkeypatch.setenv("AUXILIARY_VISION_API_KEY", "env-vision-key")
        monkeypatch.setenv("AUXILIARY_VISION_BASE_URL", "https://env.example/v1")

        # Simulate config.yaml with provider/base_url set but api_key empty
        cfg = {"provider": "alibaba", "model": "qwen-vl-max",
               "base_url": "https://config.example/v1", "api_key": ""}

        with patch("agent.auxiliary_client._get_auxiliary_task_config", return_value=cfg):
            provider, model, base_url, api_key, _api_mode = _resolve_task_provider_model("vision")

        # Both base_url + api_key now present → custom endpoint should win
        assert provider == "custom"
        assert base_url == "https://config.example/v1"  # config takes precedence
        assert api_key == "env-vision-key"  # rescued from env
        assert model == "qwen-vl-max"

    def test_unresolved_placeholder_treated_as_empty(self, monkeypatch):
        _clear_aux_env(monkeypatch, "vision")
        monkeypatch.setenv("AUXILIARY_VISION_API_KEY", "env-fallback-key")

        # ${UNSET_VAR} survived _expand_env_vars (env was unset)
        cfg = {"provider": "alibaba", "base_url": "https://config.example/v1",
               "api_key": "${UNSET_VAR}"}

        with patch("agent.auxiliary_client._get_auxiliary_task_config", return_value=cfg):
            _provider, _model, _base_url, api_key, _api_mode = _resolve_task_provider_model("vision")

        assert api_key == "env-fallback-key"

    def test_all_empty_falls_back_to_env(self, monkeypatch):
        _clear_aux_env(monkeypatch, "web_extract")
        monkeypatch.setenv("AUXILIARY_WEB_EXTRACT_PROVIDER", "alibaba")
        monkeypatch.setenv("AUXILIARY_WEB_EXTRACT_MODEL", "qwen-plus")
        monkeypatch.setenv("AUXILIARY_WEB_EXTRACT_BASE_URL", "https://env.example/v1")
        monkeypatch.setenv("AUXILIARY_WEB_EXTRACT_API_KEY", "env-key")

        cfg = {"provider": "", "model": "", "base_url": "", "api_key": ""}

        with patch("agent.auxiliary_client._get_auxiliary_task_config", return_value=cfg):
            provider, model, base_url, api_key, _api_mode = _resolve_task_provider_model("web_extract")

        assert provider == "custom"  # base_url + api_key both set → custom
        assert base_url == "https://env.example/v1"
        assert api_key == "env-key"
        assert model == "qwen-plus"

    def test_config_value_wins_over_env(self, monkeypatch):
        """Non-empty config field must take precedence over env var."""
        _clear_aux_env(monkeypatch, "vision")
        monkeypatch.setenv("AUXILIARY_VISION_API_KEY", "env-key")

        cfg = {"provider": "alibaba", "base_url": "https://config.example/v1",
               "api_key": "config-key"}

        with patch("agent.auxiliary_client._get_auxiliary_task_config", return_value=cfg):
            _provider, _model, _base_url, api_key, _api_mode = _resolve_task_provider_model("vision")

        assert api_key == "config-key"

    def test_no_env_no_config_returns_auto(self, monkeypatch):
        """When neither config nor env has anything, fall through to auto."""
        _clear_aux_env(monkeypatch, "vision")

        cfg = {}

        with patch("agent.auxiliary_client._get_auxiliary_task_config", return_value=cfg):
            provider, _model, base_url, api_key, _api_mode = _resolve_task_provider_model("vision")

        assert provider == "auto"
        assert base_url is None
        assert api_key is None
