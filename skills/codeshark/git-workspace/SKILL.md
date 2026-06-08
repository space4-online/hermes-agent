---
name: git-workspace
description: Manage workspace file repositories with git-like semantics (commit, diff, log). Files are stored via local workspace directory and commits are reported to the CodeShark backend.
version: 1.0.0
author: codeshark
metadata:
  hermes:
    tags:
      - workspace
      - git
      - files
    config_vars:
      - key: WORKSPACE_CALLBACK_URL
        type: string
        description: Backend callback URL for reporting commits
        required: false
      - key: WORKSPACE_API_KEY
        type: string
        description: API key for callback auth
        required: false
---

# Git Workspace Skill

## Purpose

You have access to a git-like file management system for workspace tasks. Every file modification you make during task execution should be tracked as a "commit" — a snapshot of changes with a descriptive message.

## Workflow

1. **Work in the workspace directory** — Your task's workspace path is provided in the task body. All file operations happen here.
2. **Commit changes** — After completing a logical unit of work, use the commit tool to snapshot your changes.
3. **Report commits** — Each commit is reported back to the CodeShark backend for version tracking.

## How to Commit

Use the `git_workspace_cli.py` script:

```bash
# Commit current changes with a message
python /path/to/skills/codeshark/git-workspace/scripts/git_workspace_cli.py commit \
  --task-id <TASK_ID> \
  --workspace-path /tmp/workspace/<WID>/task/<TID> \
  --message "Implemented login form validation" \
  --callback-url <CALLBACK_URL> \
  --api-key <API_KEY>

# List files in the workspace
python /path/to/skills/codeshark/git-workspace/scripts/git_workspace_cli.py list \
  --workspace-path /tmp/workspace/<WID>/task/<TID>

# Show diff since last commit
python /path/to/skills/codeshark/git-workspace/scripts/git_workspace_cli.py diff \
  --workspace-path /tmp/workspace/<WID>/task/<TID>
```

## Commit Guidelines

- Commit after each logical unit of work (similar to conventional git commits)
- Write clear, concise commit messages describing what was done
- Do NOT commit incomplete/broken states
- Commit at minimum:
  - After initial file creation
  - After each major feature addition
  - Before and after refactoring
  - When the task is completed

## File Tree

Each commit automatically captures the full file tree (path, size, type) and the list of changed files (path, action: A/M/D). This enables the workspace platform to show file diffs to the supervisor.

## Important Notes

- The workspace directory is ephemeral — it only exists during task execution
- Always commit important work; uncommitted changes may be lost
- The commit SHA is generated locally (SHA-256 of content)
- Use the workspace-reporter skill to report your progress alongside commits
