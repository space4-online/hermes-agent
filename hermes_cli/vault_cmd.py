"""
Vault CLI command — hermes vault add|list|remove|show

Manage credential vault for secure secret storage used by the agent.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path
from typing import Optional


def cmd_vault(args) -> None:
    """Dispatch vault subcommands."""
    command = getattr(args, "vault_command", None)

    if command is None or command == "list" or command == "ls":
        _vault_list(args)
    elif command == "add":
        _vault_add(args)
    elif command == "remove" or command == "rm":
        _vault_remove(args)
    elif command == "show":
        _vault_show(args)
    else:
        _vault_list(args)


def _get_vault(project: bool = False):
    """Create VaultStore instance."""
    from agent.vault import VaultStore
    from hermes_constants import get_hermes_home

    project_root = None
    if project:
        # Try to find project root (look for .git, pyproject.toml, package.json, etc.)
        project_root = _find_project_root()
        if project_root is None:
            print("Error: Could not determine project root directory.", file=sys.stderr)
            print("Run from within a project directory or specify --project.", file=sys.stderr)
            sys.exit(1)

    return VaultStore(
        hermes_home=Path(get_hermes_home()),
        project_root=project_root,
    )


def _find_project_root() -> Optional[Path]:
    """Walk up from CWD to find a project root marker."""
    markers = [".git", "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml"]
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        for marker in markers:
            if (parent / marker).exists():
                return parent
    return None


def _vault_add(args) -> None:
    """Add or update a credential."""
    name = args.name
    value = getattr(args, "value", None)
    description = getattr(args, "description", "") or ""
    project = getattr(args, "project", False)

    # Validate credential name
    import re
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        print(
            f"Error: Invalid credential name '{name}'. "
            "Use only letters, digits, and underscores (start with letter or _).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Prompt for value if not provided
    if not value:
        try:
            value = getpass.getpass(f"Enter value for {name}: ")
            if not value:
                print("Error: Empty value. Aborted.", file=sys.stderr)
                sys.exit(1)
            # Confirm
            confirm = getpass.getpass(f"Confirm value for {name}: ")
            if value != confirm:
                print("Error: Values do not match. Aborted.", file=sys.stderr)
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.", file=sys.stderr)
            sys.exit(1)

    vault = _get_vault(project=project)
    scope = "project" if project else "global"
    vault.set(name, value, description=description, scope=scope)

    scope_label = "project" if project else "global"
    print(f"Credential '{name}' stored ({scope_label}).")


def _vault_list(args) -> None:
    """List all credentials."""
    project_only = getattr(args, "project", False)
    vault = _get_vault(project=project_only)
    credentials = vault.list()

    if not credentials:
        print("No credentials stored.")
        print("  Use: hermes vault add <name>")
        return

    if project_only:
        credentials = [c for c in credentials if c.scope == "project"]

    if not credentials:
        print("No project-level credentials found.")
        return

    # Table display
    print(f"{'Name':<24} {'Scope':<10} {'Description':<40} {'Created':<20}")
    print("-" * 94)
    for cred in credentials:
        desc = cred.description[:38] + ".." if len(cred.description) > 40 else cred.description
        created = cred.created[:19] if cred.created else ""
        print(f"{cred.name:<24} {cred.scope:<10} {desc:<40} {created:<20}")
    print(f"\nTotal: {len(credentials)} credential(s)")


def _vault_remove(args) -> None:
    """Remove a credential."""
    name = args.name
    project = getattr(args, "project", False)
    scope = "project" if project else "global"

    vault = _get_vault(project=project)
    if vault.delete(name, scope=scope):
        print(f"Credential '{name}' removed ({scope}).")
    else:
        print(f"Credential '{name}' not found in {scope} vault.", file=sys.stderr)
        sys.exit(1)


def _vault_show(args) -> None:
    """Show a credential with masked value."""
    from agent.vault_placeholder import mask_credential_value

    name = args.name
    vault = _get_vault(project=True)  # load both global and project

    value = vault.get(name)
    if value is None:
        print(f"Credential '{name}' not found.", file=sys.stderr)
        sys.exit(1)

    # Find scope
    scope = "global"
    for cred in vault.list():
        if cred.name == name:
            scope = cred.scope
            break

    masked = mask_credential_value(value)
    print(f"Name:        {name}")
    print(f"Scope:       {scope}")
    print(f"Value:       {masked}")
    print(f"Placeholder: {{{{vault:{name}}}}}")
