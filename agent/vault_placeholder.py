"""
Vault Placeholder Engine — Bidirectional substitution between credential
values and named placeholders.

Placeholder format: {{vault:CREDENTIAL_NAME}}

Two core operations:
  - inject_placeholders(text, vault):  value → placeholder  (before sending to LLM)
  - resolve_placeholders(text, vault): placeholder → value  (before tool execution)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from agent.vault import VaultStore

# Regex to match vault placeholders in text
VAULT_PLACEHOLDER_RE = re.compile(r"\{\{vault:([A-Za-z_][A-Za-z0-9_]*)\}\}")

# Minimum credential value length for automatic injection.
# Shorter values risk false-positive replacements in normal text.
MIN_AUTO_INJECT_LENGTH = 6


def inject_placeholders(
    text: Optional[str],
    vault: "VaultStore",
    *,
    force_all: bool = False,
) -> Optional[str]:
    """Replace credential values in text with {{vault:NAME}} placeholders.

    Args:
        text: Input text that may contain raw credential values.
        vault: VaultStore instance providing credential mappings.
        force_all: If True, inject even short (<6 char) credentials.
                   Default False skips short values to avoid false positives.

    Returns:
        Text with credential values replaced by placeholders, or None if input is None.

    Notes:
        - Replacements are applied in descending order of value length to prevent
          a shorter value from partially matching inside a longer one.
        - Values that are substrings of the placeholder pattern itself are skipped.
    """
    if text is None:
        return None
    entries = vault.all_entries()
    if not entries:
        return text

    # Build replacement pairs sorted by value length (longest first)
    pairs: List[Tuple[str, str]] = []
    for name, value in entries.items():
        if not value:
            continue
        if not force_all and len(value) < MIN_AUTO_INJECT_LENGTH:
            continue
        placeholder = f"{{{{vault:{name}}}}}"
        # Don't replace if the value is already a placeholder pattern
        if VAULT_PLACEHOLDER_RE.match(value):
            continue
        pairs.append((value, placeholder))

    # Sort by value length descending — longest values replaced first
    pairs.sort(key=lambda p: len(p[0]), reverse=True)

    result = text
    for value, placeholder in pairs:
        result = result.replace(value, placeholder)
    return result


def resolve_placeholders(
    text: Optional[str],
    vault: "VaultStore",
) -> Optional[str]:
    """Replace {{vault:NAME}} placeholders with actual credential values.

    Args:
        text: Input text containing vault placeholders.
        vault: VaultStore instance providing credential mappings.

    Returns:
        Text with placeholders resolved to real values.
        Unknown placeholders are left unchanged.
    """
    if text is None:
        return None
    if "{{vault:" not in text:
        return text

    def _replacer(match: re.Match) -> str:
        name = match.group(1)
        value = vault.get(name)
        if value is not None:
            return value
        # Unknown credential — leave placeholder intact
        return match.group(0)

    return VAULT_PLACEHOLDER_RE.sub(_replacer, text)


def mask_credential_value(value: str, head: int = 6, tail: int = 4) -> str:
    """Return a masked version of a credential value for display purposes.

    Examples:
        "ghp_abcdefgh1234567890" -> "ghp_ab...7890"
        "short" -> "***"
    """
    if len(value) <= head + tail + 3:
        return "***"
    return f"{value[:head]}...{value[-tail:]}"


def inject_placeholders_in_messages(
    messages: List[dict],
    vault: "VaultStore",
) -> List[dict]:
    """Apply placeholder injection to a list of chat messages (deep copy).

    Handles standard OpenAI message format with 'content' field.
    Does NOT modify the original messages list.
    """
    if not messages:
        return messages

    entries = vault.all_entries()
    if not entries:
        return messages

    result = []
    for msg in messages:
        new_msg = dict(msg)
        content = msg.get("content")
        if isinstance(content, str):
            new_msg["content"] = inject_placeholders(content, vault)
        elif isinstance(content, list):
            # Handle multi-part content (e.g., text + image blocks)
            new_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    new_part = dict(part)
                    new_part["text"] = inject_placeholders(
                        part.get("text", ""), vault
                    )
                    new_parts.append(new_part)
                else:
                    new_parts.append(part)
            new_msg["content"] = new_parts
        result.append(new_msg)
    return result


def resolve_placeholders_in_tool_args(
    arguments_json: str,
    vault: "VaultStore",
) -> str:
    """Resolve vault placeholders in tool call argument JSON string.

    This is called just before tool execution so tools receive real values.
    """
    return resolve_placeholders(arguments_json, vault) or arguments_json
