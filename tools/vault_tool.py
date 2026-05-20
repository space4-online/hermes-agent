"""
Vault Tool Module - Credential Management for LLM

Provides tools for the LLM to interact with the credential vault:
  - list_credentials: See available credential names and descriptions (no values)
  - use_credential: Get a {{vault:NAME}} placeholder to use in tool arguments

Security:
  The LLM never sees actual credential values. It only sees placeholder strings.
  When tools are executed, the placeholder engine resolves them to real values.
"""

import json
from typing import Any, Dict, Optional


def list_credentials_handler(args: Dict[str, Any], **kwargs) -> str:
    """List all available credentials (names + descriptions, no values)."""
    vault = kwargs.get("vault")
    if vault is None:
        return json.dumps({"error": "Vault not available in this session."})

    credentials = vault.list()
    if not credentials:
        return json.dumps({
            "credentials": [],
            "message": "No credentials stored. Use `hermes vault add <name>` to add credentials."
        })

    items = []
    for cred in credentials:
        items.append({
            "name": cred.name,
            "description": cred.description or "(no description)",
            "scope": cred.scope,
        })
    return json.dumps({"credentials": items}, ensure_ascii=False)


def use_credential_handler(args: Dict[str, Any], **kwargs) -> str:
    """Return a vault placeholder for the named credential.

    The LLM should include this placeholder in subsequent tool call arguments.
    The placeholder engine will resolve it to the real value at execution time.
    """
    vault = kwargs.get("vault")
    if vault is None:
        return json.dumps({"error": "Vault not available in this session."})

    name = args.get("name", "").strip()
    if not name:
        return json.dumps({"error": "Parameter 'name' is required."})

    if not vault.has(name):
        available = [c.name for c in vault.list()]
        return json.dumps({
            "error": f"Credential '{name}' not found.",
            "available": available,
        }, ensure_ascii=False)

    placeholder = f"{{{{vault:{name}}}}}"
    return json.dumps({
        "placeholder": placeholder,
        "instruction": (
            f"Use the string {placeholder} in your tool arguments where "
            f"this credential is needed. It will be automatically resolved "
            f"to the real value when the tool executes."
        ),
    })


def check_vault_requirements() -> bool:
    """Check if vault is available (PyYAML installed)."""
    try:
        import yaml
        return True
    except ImportError:
        return False


# --- Schemas ---

LIST_CREDENTIALS_SCHEMA = {
    "name": "list_credentials",
    "description": (
        "List all available credentials stored in the vault. "
        "Returns credential names and descriptions (never actual values). "
        "Use this to discover what credentials are available before using them."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

USE_CREDENTIAL_SCHEMA = {
    "name": "use_credential",
    "description": (
        "Get a secure placeholder for a named credential. "
        "The returned placeholder (e.g., {{vault:GITHUB_TOKEN}}) should be placed "
        "in tool arguments where the credential value is needed. "
        "The system will automatically resolve it to the real value at execution time. "
        "NEVER try to guess or hardcode credential values — always use this tool."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The credential name (e.g., GITHUB_TOKEN, DB_PASSWORD)",
            },
        },
        "required": ["name"],
    },
}


# --- Registry ---
from tools.registry import registry

registry.register(
    name="list_credentials",
    toolset="vault",
    schema=LIST_CREDENTIALS_SCHEMA,
    handler=list_credentials_handler,
    check_fn=check_vault_requirements,
    emoji="🔐",
)

registry.register(
    name="use_credential",
    toolset="vault",
    schema=USE_CREDENTIAL_SCHEMA,
    handler=use_credential_handler,
    check_fn=check_vault_requirements,
    emoji="🔑",
)
