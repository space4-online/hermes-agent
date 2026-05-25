"""Regression tests for the shared /vault slash command handler.

The /vault command must work uniformly across:

- TUI / web chat / ACP (via ``cli.HermesCLI.process_command`` → ``vault_shared``)
- Messaging gateways (via ``gateway/run.py`` → ``vault_shared``)

Before refactoring, web chat silently dropped /vault because the command was
flagged ``gateway_only=True`` and the handler lived only in ``gateway/run.py``.
These tests pin the new contract: a single shared formatter, registered on
both surfaces.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. Command registry: vault must NOT be gateway-only anymore.
# ---------------------------------------------------------------------------


def test_vault_command_not_gateway_only() -> None:
    """``/vault`` must be available on both CLI and gateway surfaces.

    Marking it ``gateway_only=True`` would re-introduce the silent-drop bug
    that this refactor fixes.
    """
    from hermes_cli.commands import COMMAND_REGISTRY

    cmd = next(c for c in COMMAND_REGISTRY if c.name == "vault")
    assert not cmd.gateway_only, "/vault must be available in both CLI and gateway"
    assert not cmd.cli_only, "/vault must also work in messaging gateways"


def test_vault_appears_in_cli_commands_dict() -> None:
    """The CLI dispatcher uses ``COMMANDS`` for completion / help; /vault must
    be in there now that it is no longer gateway-only."""
    from hermes_cli.commands import COMMANDS

    assert "/vault" in COMMANDS


# ---------------------------------------------------------------------------
# 2. Argument parsing
# ---------------------------------------------------------------------------


def test_parse_vault_args_strips_command_word() -> None:
    from hermes_cli.vault_shared import parse_vault_args

    assert parse_vault_args("/vault list") == ["list"]
    assert parse_vault_args("vault show MY_KEY") == ["show", "MY_KEY"]
    assert parse_vault_args("/vault add NAME value extra desc") == [
        "add",
        "NAME",
        "value",
        "extra",
        "desc",
    ]
    assert parse_vault_args("/vault") == []
    assert parse_vault_args("") == []


# ---------------------------------------------------------------------------
# 3. format_vault_command — empty / list / show / add / remove / help
# ---------------------------------------------------------------------------


def _patch_vault(stub):
    """Wire ``VaultStore(...)`` to return ``stub`` regardless of args."""
    return patch("agent.vault.VaultStore", return_value=stub)


def _make_credential(name: str, scope: str = "global", description: str = ""):
    cred = MagicMock()
    cred.name = name
    cred.scope = scope
    cred.description = description
    return cred


def test_format_empty_vault_shows_guidance() -> None:
    from hermes_cli.vault_shared import format_vault_command

    stub = MagicMock()
    stub.list.return_value = []

    with _patch_vault(stub):
        out = format_vault_command(["list"])

    assert "Vault is empty" in out
    assert "hermes vault add" in out


def test_format_list_renders_credentials() -> None:
    from hermes_cli.vault_shared import format_vault_command

    stub = MagicMock()
    stub.list.return_value = [
        _make_credential("DASHSCOPE_API_KEY", "global", "Aliyun DashScope"),
        _make_credential("PROJECT_TOKEN", "project", ""),
    ]

    with _patch_vault(stub):
        out = format_vault_command([])  # default to list

    assert "DASHSCOPE_API_KEY" in out
    assert "Aliyun DashScope" in out
    assert "PROJECT_TOKEN" in out
    assert "(global)" in out
    assert "(project)" in out


def test_format_show_returns_masked_value_and_placeholder() -> None:
    from hermes_cli.vault_shared import format_vault_command

    stub = MagicMock()
    stub.get.return_value = "supersecretvalue1234"
    stub.list.return_value = [_make_credential("MY_KEY", "global", "")]

    with _patch_vault(stub), patch(
        "agent.vault_placeholder.mask_credential_value", return_value="su***34"
    ):
        out = format_vault_command(["show", "MY_KEY"])

    assert "MY_KEY" in out
    assert "su***34" in out
    assert "{{vault:MY_KEY}}" in out
    # Real value must NOT appear in any rendering.
    assert "supersecretvalue1234" not in out


def test_format_show_missing_credential_lists_alternatives() -> None:
    from hermes_cli.vault_shared import format_vault_command

    stub = MagicMock()
    stub.get.return_value = None
    stub.list.return_value = [_make_credential("OTHER", "global", "")]

    with _patch_vault(stub):
        out = format_vault_command(["show", "MISSING"])

    assert "not found" in out
    assert "OTHER" in out


def test_format_add_validates_name() -> None:
    from hermes_cli.vault_shared import format_vault_command

    stub = MagicMock()

    with _patch_vault(stub):
        out = format_vault_command(["add", "9bad-name", "value"])

    assert "Invalid name" in out
    stub.set.assert_not_called()


def test_format_add_stores_credential_with_security_warning() -> None:
    from hermes_cli.vault_shared import format_vault_command

    stub = MagicMock()

    with _patch_vault(stub):
        out = format_vault_command(["add", "GOOD_NAME", "v", "an", "API", "token"])

    stub.set.assert_called_once_with(
        "GOOD_NAME", "v", description="an API token", scope="global"
    )
    assert "stored" in out
    assert "delete this message immediately" in out


def test_format_add_disabled_when_inline_add_blocked() -> None:
    from hermes_cli.vault_shared import format_vault_command

    stub = MagicMock()

    with _patch_vault(stub):
        out = format_vault_command(
            ["add", "X", "y"], allow_inline_add=False
        )

    assert "disabled" in out
    stub.set.assert_not_called()


def test_format_remove_global_then_project_fallback() -> None:
    from hermes_cli.vault_shared import format_vault_command

    stub = MagicMock()
    # Fail global, succeed project — exercises the fallback chain.
    stub.delete.side_effect = [False, True]

    with _patch_vault(stub):
        out = format_vault_command(["remove", "FOO"])

    assert stub.delete.call_count == 2
    assert "removed from project vault" in out


def test_format_unknown_subcommand_returns_help() -> None:
    from hermes_cli.vault_shared import format_vault_command

    stub = MagicMock()
    with _patch_vault(stub):
        out = format_vault_command(["wat"])

    assert "Vault commands" in out
    assert "/vault list" in out
    assert "/vault show" in out


# ---------------------------------------------------------------------------
# 4. End-to-end: gateway adapter delegates to the shared formatter
# ---------------------------------------------------------------------------


def test_gateway_handler_delegates_to_shared_formatter() -> None:
    """``gateway/run.py`` must route through ``format_vault_command``.

    We don't import the full gateway (heavy deps); we instead grep the
    source file as a structural assertion.
    """
    src = (
        Path(__file__).resolve().parents[2]
        / "gateway"
        / "run.py"
    ).read_text(encoding="utf-8")

    # The shared import must be present and the old per-handler logic must
    # be gone (catches accidental copy-paste regressions).
    assert "from hermes_cli.vault_shared import format_vault_command" in src
    assert "return format_vault_command(parts)" in src
