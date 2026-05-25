"""Shared vault slash-command formatter.

Single source of truth for the ``/vault`` slash command output, used by:

- ``gateway/run.py`` (messaging gateways: telegram / dingtalk / slack / ...)
- ``cli.py`` HermesCLI.process_command (TUI / web chat / ACP — all routes that
  dispatch slash commands through HermesCLI)

Centralising it here avoids drift between channels (web chat used to silently
reject ``/vault`` because it was marked ``gateway_only`` and only handled in
``gateway/run.py``).

Returns a single string suitable for printing to a terminal or sending as a
chat reply.  Markdown formatting is preserved — terminals will show the
backticks literally, which is acceptable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional


_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _help_text() -> str:
    return (
        "🔐 **Vault commands:**\n"
        "• `/vault list` — list all credentials\n"
        "• `/vault show NAME` — show masked value + placeholder\n"
        "• `/vault add NAME VALUE [description]` — store a credential\n"
        "• `/vault remove NAME` — delete a credential\n\n"
        "⚠️ For `/vault add`, using `hermes vault add` via SSH is safer — "
        "the value is never exposed in chat history."
    )


def format_vault_command(parts: List[str], *, allow_inline_add: bool = True) -> str:
    """Format a ``/vault ...`` slash command response.

    Args:
        parts: Tokens AFTER ``/vault`` (i.e. for ``/vault show NAME`` pass
            ``["show", "NAME"]``).  Empty list defaults to ``list``.
        allow_inline_add: If False, the ``add`` subcommand is rejected with
            guidance to use ``hermes vault add`` instead.  Reserved for
            channels where echoing a plaintext secret in chat is unsafe.

    Returns:
        A user-facing string.  Errors are returned in-band as messages
        (no exceptions) so callers can stream the result to a chat reply
        without extra try/except plumbing.
    """
    try:
        from agent.vault import VaultStore  # type: ignore
        from agent.vault_placeholder import mask_credential_value  # type: ignore
        from hermes_constants import get_hermes_home  # type: ignore
    except Exception as e:  # pragma: no cover - import-time failure
        return f"❌ Vault module not available: {e}"

    subcmd = parts[0].lower() if parts else "list"

    try:
        vault = VaultStore(hermes_home=Path(get_hermes_home()))
    except Exception as e:
        return f"❌ Vault not available: {e}"

    if subcmd in ("list", "ls", ""):
        credentials = vault.list()
        if not credentials:
            return (
                "🔐 Vault is empty.\n"
                "Add a credential: `/vault add NAME VALUE [description]`\n"
                "Or via SSH (safer): `hermes vault add NAME`"
            )
        lines = ["🔐 **Stored credentials:**\n"]
        for cred in credentials:
            desc = f" — {cred.description}" if cred.description else ""
            lines.append(f"• `{cred.name}` ({cred.scope}){desc}")
        return "\n".join(lines)

    if subcmd == "show":
        if len(parts) < 2:
            return "Usage: `/vault show NAME`"
        name = parts[1]
        value = vault.get(name)
        if value is None:
            available = [c.name for c in vault.list()]
            avail_str = ", ".join(f"`{n}`" for n in available) if available else "(none)"
            return f"❌ Credential `{name}` not found.\nAvailable: {avail_str}"
        masked = mask_credential_value(value)
        scope = _scope_of(vault, name)
        return (
            f"🔐 `{name}` ({scope})\n"
            f"Value: `{masked}`\n"
            f"Placeholder: `{{{{vault:{name}}}}}`"
        )

    if subcmd == "add":
        if not allow_inline_add:
            return (
                "❌ Inline `/vault add` is disabled in this channel.\n"
                "Use `hermes vault add NAME` from a terminal — safer "
                "(interactive prompt, value never enters chat history)."
            )
        if len(parts) < 3:
            return (
                "Usage: `/vault add NAME VALUE [description...]`\n"
                "⚠️ Prefer `hermes vault add NAME` via SSH — safer (interactive, never exposed in chat)."
            )
        name = parts[1]
        if not _NAME_RE.match(name):
            return (
                f"❌ Invalid name `{name}`.\n"
                "Names must start with a letter or underscore and contain only letters, digits, underscores."
            )
        value = parts[2]
        description = " ".join(parts[3:]) if len(parts) > 3 else ""
        vault.set(name, value, description=description, scope="global")
        return (
            f"✅ Credential `{name}` stored.\n"
            f"⚠️ **Security notice:** This message contains your secret in plaintext. "
            f"Please **delete this message immediately** from chat history. "
            f"Using `hermes vault add {name}` via SSH is significantly safer."
        )

    if subcmd in ("remove", "rm", "delete", "del"):
        if len(parts) < 2:
            return "Usage: `/vault remove NAME`"
        name = parts[1]
        if vault.delete(name, scope="global"):
            return f"✅ Credential `{name}` removed from global vault."
        if vault.delete(name, scope="project"):
            return f"✅ Credential `{name}` removed from project vault."
        return f"❌ Credential `{name}` not found."

    return _help_text()


def _scope_of(vault, name: str) -> str:
    for cred in vault.list():
        if cred.name == name:
            return cred.scope
    return "global"


def parse_vault_args(cmd_original: str) -> List[str]:
    """Split a ``/vault ...`` command line into argument tokens.

    Drops the leading ``/vault`` (or ``vault``) token and returns the rest.
    """
    text = cmd_original.strip()
    if text.startswith("/"):
        text = text[1:]
    if text.lower().startswith("vault"):
        text = text[len("vault"):]
    return text.split()
