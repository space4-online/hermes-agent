#!/usr/bin/env python3
"""
Git Workspace CLI — local file tracking with commit semantics.

Commands:
  commit  — Snapshot current workspace state and report to backend
  list    — List files in the workspace directory
  diff    — Show changes since last commit

Output: ONE JSON line on stdout per command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


# Track last commit state in a hidden file
_STATE_FILE = ".workspace_state.json"


def _get_config():
    return {
        "callback_url": os.getenv("WORKSPACE_CALLBACK_URL", ""),
        "api_key": os.getenv("WORKSPACE_API_KEY", os.getenv("API_SERVER_KEY", "")),
    }


def _post(url: str, api_key: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "hermes-git-workspace/1.0",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return {"ok": True, "status": resp.status}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return {"ok": False, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _scan_files(workspace_path: str) -> list[dict]:
    """Scan workspace directory and return file tree."""
    files = []
    base = Path(workspace_path)
    if not base.exists():
        return files
    for p in sorted(base.rglob("*")):
        if p.name.startswith(".workspace_"):
            continue
        rel = str(p.relative_to(base))
        if p.is_file():
            files.append({
                "path": rel,
                "size": p.stat().st_size,
                "type": "file",
            })
        elif p.is_dir():
            files.append({
                "path": rel,
                "size": 0,
                "type": "dir",
            })
    return files


def _compute_sha(workspace_path: str, file_tree: list[dict]) -> str:
    """Compute a SHA-256 based on file contents."""
    h = hashlib.sha256()
    base = Path(workspace_path)
    for f in file_tree:
        if f["type"] == "file":
            fp = base / f["path"]
            if fp.exists():
                h.update(f["path"].encode())
                h.update(fp.read_bytes())
    return h.hexdigest()[:16]


def _load_state(workspace_path: str) -> dict:
    state_path = Path(workspace_path) / _STATE_FILE
    if state_path.exists():
        return json.loads(state_path.read_text())
    return {"last_sha": None, "last_tree": []}


def _save_state(workspace_path: str, sha: str, tree: list[dict]):
    state_path = Path(workspace_path) / _STATE_FILE
    state_path.write_text(json.dumps({"last_sha": sha, "last_tree": tree}))


def _compute_changes(old_tree: list[dict], new_tree: list[dict]) -> list[dict]:
    """Compute file changes between two trees."""
    old_files = {f["path"]: f for f in old_tree if f["type"] == "file"}
    new_files = {f["path"]: f for f in new_tree if f["type"] == "file"}

    changes = []
    for path in new_files:
        if path not in old_files:
            changes.append({"path": path, "action": "A"})
        elif new_files[path]["size"] != old_files[path]["size"]:
            changes.append({"path": path, "action": "M"})
    for path in old_files:
        if path not in new_files:
            changes.append({"path": path, "action": "D"})
    return changes


def cmd_commit(args):
    """Commit workspace state and report to backend."""
    config = _get_config()
    callback_url = args.callback_url or config["callback_url"]
    api_key = args.api_key or config["api_key"]

    workspace_path = args.workspace_path
    if not Path(workspace_path).exists():
        Path(workspace_path).mkdir(parents=True, exist_ok=True)

    # Scan current state
    file_tree = _scan_files(workspace_path)
    current_sha = _compute_sha(workspace_path, file_tree)

    # Load previous state
    state = _load_state(workspace_path)
    parent_sha = state["last_sha"]
    changes = _compute_changes(state["last_tree"], file_tree)

    if not changes and parent_sha:
        print(json.dumps({"ok": True, "message": "No changes to commit", "sha": parent_sha}))
        sys.exit(0)

    # Save new state
    _save_state(workspace_path, current_sha, file_tree)

    result = {
        "ok": True,
        "sha": current_sha,
        "parent_sha": parent_sha,
        "message": args.message,
        "files_changed": len(changes),
        "total_files": len([f for f in file_tree if f["type"] == "file"]),
    }

    # Report to backend if callback configured
    if callback_url and api_key:
        payload = {
            "taskId": args.task_id,
            "commitSha": current_sha,
            "parentSha": parent_sha,
            "message": args.message,
            "fileTreeJson": json.dumps(file_tree),
            "filesChanged": json.dumps(changes),
        }
        url = f"{callback_url.rstrip('/')}/commit"
        report_result = _post(url, api_key, payload)
        result["reported"] = report_result["ok"]
        if not report_result["ok"]:
            result["report_error"] = report_result.get("error", "unknown")

    print(json.dumps(result))
    sys.exit(0)


def cmd_list(args):
    """List files in workspace."""
    file_tree = _scan_files(args.workspace_path)
    files_only = [f for f in file_tree if f["type"] == "file"]
    print(json.dumps({"ok": True, "files": files_only, "count": len(files_only)}))
    sys.exit(0)


def cmd_diff(args):
    """Show changes since last commit."""
    workspace_path = args.workspace_path
    file_tree = _scan_files(workspace_path)
    state = _load_state(workspace_path)
    changes = _compute_changes(state["last_tree"], file_tree)
    print(json.dumps({"ok": True, "changes": changes, "count": len(changes)}))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Git Workspace CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # commit
    commit_parser = subparsers.add_parser("commit", help="Commit workspace state")
    commit_parser.add_argument("--task-id", type=int, required=True)
    commit_parser.add_argument("--workspace-path", required=True)
    commit_parser.add_argument("--message", required=True)
    commit_parser.add_argument("--callback-url", default=None)
    commit_parser.add_argument("--api-key", default=None)
    commit_parser.set_defaults(func=cmd_commit)

    # list
    list_parser = subparsers.add_parser("list", help="List workspace files")
    list_parser.add_argument("--workspace-path", required=True)
    list_parser.set_defaults(func=cmd_list)

    # diff
    diff_parser = subparsers.add_parser("diff", help="Show changes since last commit")
    diff_parser.add_argument("--workspace-path", required=True)
    diff_parser.set_defaults(func=cmd_diff)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
