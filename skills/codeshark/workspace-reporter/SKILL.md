---
name: workspace-reporter
description: Report task progress (logs, status changes, commits) back to the CodeShark workspace backend via HTTP callbacks. Automatically invoked during kanban task execution.
version: 1.0.0
author: codeshark
metadata:
  hermes:
    tags:
      - workspace
      - reporting
      - callback
    config_vars:
      - key: WORKSPACE_CALLBACK_URL
        type: string
        description: Backend callback base URL (injected via task body callback_meta)
        required: false
      - key: WORKSPACE_API_KEY
        type: string
        description: API key for authenticating callbacks (same as API_SERVER_KEY)
        required: false
---

# Workspace Reporter Skill

## Purpose

You are equipped with a progress reporting tool that sends real-time updates back to the CodeShark workspace platform. This allows the human supervisor to observe your work in real-time.

## When to Report

Report progress at these key moments:

1. **STEP_START** — When you begin a distinct phase of work (e.g., "Analyzing requirements", "Writing code", "Running tests")
2. **STEP_END** — When you finish a phase
3. **THINKING** — When you have a significant insight or decision
4. **FILE_OP** — After creating, modifying, or deleting a file
5. **COMMAND** — After executing a shell command with notable output
6. **ERROR** — When you encounter an error or blocker
7. **INFO** — General progress info

## How to Report

Use the `report_cli.py` script in this skill's `scripts/` directory:

```bash
python /path/to/skills/codeshark/workspace-reporter/scripts/report_cli.py log \
  --task-id <TASK_ID> \
  --type STEP_START \
  --content "Analyzing codebase structure"

python /path/to/skills/codeshark/workspace-reporter/scripts/report_cli.py status \
  --workspace-id <WORKSPACE_ID> \
  --task-id <TASK_ID> \
  --status completed

python /path/to/skills/codeshark/workspace-reporter/scripts/report_cli.py commit \
  --task-id <TASK_ID> \
  --sha <COMMIT_SHA> \
  --message "Implemented feature X"
```

## Callback Metadata

The task body contains a `callback_meta` HTML comment block with the necessary configuration:
```
<!-- callback_meta: {"callback_url": "...", "workspace_id": ..., "task_id": ..., "api_key": "..."} -->
```

Extract these values and use them for all reporting calls. The script also reads from environment variables `WORKSPACE_CALLBACK_URL` and `WORKSPACE_API_KEY` as fallback.

## Reporting Frequency

- Report STEP_START/STEP_END for each major phase (aim for 3-8 steps per task)
- Report FILE_OP for each file you create or significantly modify
- Do NOT report every single line change or trivial operation
- If a step takes more than 2 minutes, report an INFO update midway

## Important

- Never skip reporting task completion or failure status
- Always report errors immediately when they occur
- The callback_url and api_key are confidential — never expose them in output or logs visible to others
