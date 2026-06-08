#!/usr/bin/env python3
"""
Workspace Reporter CLI — send progress callbacks to CodeShark backend.

Commands:
  log     — Report a log entry (THINKING/FILE_OP/COMMAND/ERROR/STEP_START/STEP_END/INFO)
  status  — Report a status change (running/completed/failed/cancelled)
  commit  — Report a file commit

Each command emits ONE JSON line on stdout. On error: {"ok": false, "error": "..."}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def _get_config():
    """Read callback config from env vars."""
    return {
        "callback_url": os.getenv("WORKSPACE_CALLBACK_URL", ""),
        "api_key": os.getenv("WORKSPACE_API_KEY", os.getenv("API_SERVER_KEY", "")),
    }


def _post(url: str, api_key: str, payload: dict) -> dict:
    """Send POST request with JSON body."""
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "hermes-workspace-reporter/1.0",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return {"ok": True, "status": resp.status, "response": body}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return {"ok": False, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_log(args):
    """Report a log entry."""
    config = _get_config()
    callback_url = args.callback_url or config["callback_url"]
    api_key = args.api_key or config["api_key"]

    if not callback_url:
        print(json.dumps({"ok": False, "error": "No callback_url configured"}))
        sys.exit(1)

    payload = {
        "taskId": args.task_id,
        "logType": args.type,
        "content": args.content,
        "metadata": args.metadata,
    }
    url = f"{callback_url.rstrip('/')}/log"
    result = _post(url, api_key, payload)
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


def cmd_status(args):
    """Report a status change."""
    config = _get_config()
    callback_url = args.callback_url or config["callback_url"]
    api_key = args.api_key or config["api_key"]

    if not callback_url:
        print(json.dumps({"ok": False, "error": "No callback_url configured"}))
        sys.exit(1)

    payload = {
        "workspaceId": args.workspace_id,
        "taskId": args.task_id,
        "status": args.status,
    }
    url = f"{callback_url.rstrip('/')}/status"
    result = _post(url, api_key, payload)
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


def cmd_commit(args):
    """Report a commit."""
    config = _get_config()
    callback_url = args.callback_url or config["callback_url"]
    api_key = args.api_key or config["api_key"]

    if not callback_url:
        print(json.dumps({"ok": False, "error": "No callback_url configured"}))
        sys.exit(1)

    payload = {
        "taskId": args.task_id,
        "commitSha": args.sha,
        "parentSha": args.parent_sha,
        "message": args.message,
        "fileTreeJson": args.file_tree,
        "filesChanged": args.files_changed,
    }
    url = f"{callback_url.rstrip('/')}/commit"
    result = _post(url, api_key, payload)
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


def main():
    parser = argparse.ArgumentParser(description="Workspace Reporter CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # log command
    log_parser = subparsers.add_parser("log", help="Report a log entry")
    log_parser.add_argument("--task-id", type=int, required=True)
    log_parser.add_argument("--type", required=True,
                            choices=["THINKING", "FILE_OP", "COMMAND", "ERROR",
                                     "STEP_START", "STEP_END", "CHAT_MSG", "INFO"])
    log_parser.add_argument("--content", required=True)
    log_parser.add_argument("--metadata", default=None)
    log_parser.add_argument("--callback-url", default=None)
    log_parser.add_argument("--api-key", default=None)
    log_parser.set_defaults(func=cmd_log)

    # status command
    status_parser = subparsers.add_parser("status", help="Report status change")
    status_parser.add_argument("--workspace-id", type=int, required=True)
    status_parser.add_argument("--task-id", type=int, required=True)
    status_parser.add_argument("--status", required=True,
                               choices=["running", "completed", "failed", "cancelled"])
    status_parser.add_argument("--callback-url", default=None)
    status_parser.add_argument("--api-key", default=None)
    status_parser.set_defaults(func=cmd_status)

    # commit command
    commit_parser = subparsers.add_parser("commit", help="Report a commit")
    commit_parser.add_argument("--task-id", type=int, required=True)
    commit_parser.add_argument("--sha", required=True)
    commit_parser.add_argument("--parent-sha", default=None)
    commit_parser.add_argument("--message", required=True)
    commit_parser.add_argument("--file-tree", default=None, help="JSON array of file tree")
    commit_parser.add_argument("--files-changed", default=None, help="JSON array of changed files")
    commit_parser.add_argument("--callback-url", default=None)
    commit_parser.add_argument("--api-key", default=None)
    commit_parser.set_defaults(func=cmd_commit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
