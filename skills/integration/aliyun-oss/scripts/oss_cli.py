#!/usr/bin/env python3
"""
Aliyun OSS CLI — upload / list / share / delete / info.

Each command emits ONE JSON line on stdout. On error: {"ok": false, "error": "..."}
plus non-zero exit code. Designed for the agent to JSON-parse the last line.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

# Allow imports from sibling modules (./_vault_reader.py, ./_oss_client.py)
SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# Lazy-install missing third-party deps (oss2) on first invocation. Must
# happen before _oss_client is imported because that module reaches into
# oss2 lazily via _import_oss2() but we want all callers (including
# `info` which doesn't need oss2 yet) to share one dependency-ready path.
from _bootstrap import ensure_dependencies

try:
    ensure_dependencies()
except Exception as _bootstrap_err:                              # pragma: no cover
    # Surface as the standard JSON error envelope, matching the rest of
    # the CLI's output contract, then exit non-zero.
    print(
        json.dumps(
            {
                "ok": False,
                "error": f"dependency bootstrap failed: {_bootstrap_err}",
                "hint": (
                    "Set HERMES_OSS_NO_BOOTSTRAP=1 to skip auto-install "
                    "and manage deps yourself, or pre-install with "
                    "`pip install oss2`."
                ),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    sys.exit(1)

from _oss_client import (
    OssConfigError,
    delete,
    list_objects,
    load_profile,
    share,
    upload_file,
)
from _vault_reader import list_profiles


def _emit(payload: dict, *, exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=False))
    sys.stdout.flush()
    sys.exit(exit_code)


def _emit_error(msg: str, *, hint: str = "") -> None:
    err = {"ok": False, "error": msg}
    if hint:
        err["hint"] = hint
    _emit(err, exit_code=1)


def cmd_info(args: argparse.Namespace) -> None:
    available = list_profiles()
    if not args.profile and not available:
        _emit({
            "ok": True,
            "profile": None,
            "available_profiles": [],
            "note": (
                "No OSS profiles configured. Add credentials with "
                "'hermes vault add OSS_<PROFILE>_{ENDPOINT,BUCKET,AK,SK}'."
            ),
        })
        return
    target = args.profile or (available[0] if available else "default")
    try:
        profile = load_profile(target)
    except OssConfigError as e:
        _emit({
            "ok": False,
            "error": str(e),
            "available_profiles": available,
        }, exit_code=1)
        return
    _emit({
        "ok": True,
        "profile": profile.public_summary(),
        "available_profiles": available,
    })


def cmd_upload(args: argparse.Namespace) -> None:
    profile = load_profile(args.profile)
    result = upload_file(
        profile,
        Path(args.local_path).expanduser().resolve(),
        key=args.key,
        public=args.public if args.public is not None else None,
        expires_seconds=args.expires,
    )
    _emit(result)


def cmd_share(args: argparse.Namespace) -> None:
    profile = load_profile(args.profile)
    _emit(share(profile, args.oss_key, expires_seconds=args.expires))


def cmd_list(args: argparse.Namespace) -> None:
    profile = load_profile(args.profile)
    _emit(list_objects(profile, prefix=args.prefix, limit=args.limit))


def cmd_delete(args: argparse.Namespace) -> None:
    profile = load_profile(args.profile)
    _emit(delete(profile, args.oss_key))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="oss_cli.py",
        description="Aliyun OSS CLI for Hermes (vault-backed credentials).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="Print active profile + available profiles.")
    p_info.add_argument("--profile", default=None)
    p_info.set_defaults(func=cmd_info)

    p_up = sub.add_parser("upload", help="Upload a local file. Returns URL.")
    p_up.add_argument("local_path")
    p_up.add_argument("--key", default=None, help="OSS object key (default: auto-generated under prefix)")
    p_up.add_argument("--profile", default="default")
    public_group = p_up.add_mutually_exclusive_group()
    public_group.add_argument("--public", dest="public", action="store_const", const=True)
    public_group.add_argument("--no-public", dest="public", action="store_const", const=False)
    p_up.set_defaults(public=None)
    p_up.add_argument("--expires", type=int, default=86400, help="Pre-signed URL TTL in seconds (ignored when --public)")
    p_up.set_defaults(func=cmd_upload)

    p_sh = sub.add_parser("share", help="Generate a pre-signed URL for an existing object.")
    p_sh.add_argument("oss_key")
    p_sh.add_argument("--profile", default="default")
    p_sh.add_argument("--expires", type=int, default=86400)
    p_sh.set_defaults(func=cmd_share)

    p_ls = sub.add_parser("list", help="List objects in the bucket.")
    p_ls.add_argument("--prefix", default=None)
    p_ls.add_argument("--profile", default="default")
    p_ls.add_argument("--limit", type=int, default=100)
    p_ls.set_defaults(func=cmd_list)

    p_rm = sub.add_parser("delete", help="Delete an object.")
    p_rm.add_argument("oss_key")
    p_rm.add_argument("--profile", default="default")
    p_rm.set_defaults(func=cmd_delete)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except OssConfigError as e:
        _emit_error(str(e), hint="Check 'hermes vault list' and re-add missing entries.")
    except FileNotFoundError as e:
        _emit_error(str(e))
    except Exception as e:                                  # pragma: no cover
        # Last-ditch catch — surface error class + message + last 3 traceback frames
        tb = traceback.format_exception(type(e), e, e.__traceback__)
        _emit_error(f"{type(e).__name__}: {e}", hint="".join(tb[-3:]))


if __name__ == "__main__":
    main()
