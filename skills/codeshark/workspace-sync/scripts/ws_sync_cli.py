#!/usr/bin/env python3
"""
Workspace OSS Sync CLI — Hermes Agent 与 Backend OSS 之间的文件同步工具。

双向同步链路:
  Agent Local (/opt/data/workspace/{wid}/)  ←HTTP→  Backend API  ←→  Aliyun OSS

命令:
  init       从 OSS 全量拉取到本地（首次启动）
  push       上传单个文件到 OSS
  push-all   扫描本地变更，批量推送
  pull       下载单个文件到本地
  pull-all   全量覆盖本地
  status     对比本地 manifest 与 OSS 状态

认证:
  使用 X-Bot-Api-Key header，密钥从环境变量或参数获取。

用法:
  export CODESHARK_BOT_API_URL="https://dev.codeshark.cn/api"
  export CODESHARK_BOT_API_KEY="your-key"

  python3 ws_sync_cli.py init --workspace-id 1
  python3 ws_sync_cli.py push --workspace-id 1 --path analysis/report.md
  python3 ws_sync_cli.py status --workspace-id 1
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, List, Any

# ── Defaults ─────────────────────────────────────────────────────

DEFAULT_WORKSPACE_DIR = "/opt/data/workspace/{workspace_id}"
DEFAULT_API_BASE = os.environ.get("CODESHARK_BOT_API_URL", "")
DEFAULT_API_KEY = os.environ.get("CODESHARK_BOT_API_KEY", "")

STATE_FILE = ".workspace_sync_state.json"
API_PATH = "/v2/workspace/bot/agent-sync"


# ── HTTP helpers ─────────────────────────────────────────────────

def _api_url(workspace_id: int, path: str = "") -> str:
    """构造完整的 API URL。"""
    base = DEFAULT_API_BASE.rstrip("/") if DEFAULT_API_BASE else ""
    if not base:
        raise RuntimeError("缺少 API base URL，请设置环境变量 CODESHARK_BOT_API_URL 或用 --api-base-url 指定")
    return f"{base}{API_PATH}/{workspace_id}{path}"


def _api_key() -> str:
    if not DEFAULT_API_KEY:
        raise RuntimeError("缺少 API Key，请设置环境变量 CODESHARK_BOT_API_KEY 或用 --api-key 指定")
    return DEFAULT_API_KEY


def _request(method: str, url: str, data: Optional[bytes] = None,
             headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Any:
    """发送 HTTP 请求，返回 (status, body_bytes, response_headers)。"""
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-Bot-Api-Key", _api_key())
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if data and "Content-Type" not in (headers or {}):
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] HTTP {e.code}: {body[:500]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[ERROR] 网络错误: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _get_json(url: str) -> Any:
    """GET 请求并解析 JSON 响应。"""
    _, body, _ = _request("GET", url)
    return json.loads(body)


# ── File helpers ─────────────────────────────────────────────────

def sha256_file(filepath: Path) -> str:
    """计算文件的 SHA-256 十六进制摘要。"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """计算字节数组的 SHA-256。"""
    return hashlib.sha256(data).hexdigest()


def load_state(workspace_dir: Path) -> Dict[str, Any]:
    """加载本地同步状态文件。"""
    state_path = workspace_dir / STATE_FILE
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return {"files": {}}


def save_state(workspace_dir: Path, state: Dict[str, Any]):
    """保存本地同步状态。"""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    with open(workspace_dir / STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def scan_local_files(workspace_dir: Path) -> List[Dict[str, Any]]:
    """扫描本地 workspace 目录，返回文件列表（不含隐藏文件）。"""
    files = []
    if not workspace_dir.exists():
        return files
    for p in sorted(workspace_dir.rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            rel = str(p.relative_to(workspace_dir))
            files.append({
                "path": rel,
                "size": p.stat().st_size,
                "sha256": sha256_file(p),
            })
    return files


# ── Commands ─────────────────────────────────────────────────────

def cmd_ensure_init(workspace_id: int):
    """为已有工作区补充 OSS 文件夹初始化（幂等）。"""
    url = _api_url(workspace_id, "/ensure-oss-init")
    _, body, _ = _request("POST", url)
    result = json.loads(body)
    data = result.get("data", result)
    if data.get("initialized"):
        print(f"[ensure-init] ✓ OSS 目录已初始化: {data.get('markerKey', '')}")
    else:
        print(f"[ensure-init] ✓ OSS 目录已存在，无需初始化")


def cmd_init(workspace_id: int, workspace_dir: Path):
    """全量拉取 OSS → 本地。"""
    print(f"[init] 开始从 OSS 拉取 workspace/{workspace_id} ...")

    # 1. 列出 OSS 文件
    url = _api_url(workspace_id, "/files")
    resp = _get_json(url)
    data = resp.get("data", resp)
    oss_files = data.get("files", [])
    print(f"[init] OSS 上有 {len(oss_files)} 个文件")

    if not oss_files:
        print("[init] OSS 上无文件，仅保存空状态")
        save_state(workspace_dir, {"files": {}})
        return

    # 2. 逐个下载
    downloaded = 0
    state = {"files": {}}
    for entry in oss_files:
        path = entry.get("path", "")
        if not path:
            continue
        try:
            dl_url = _api_url(workspace_id, f"/files/download?path={_url_quote(path)}")
            _, body, headers = _request("GET", dl_url)
            content = body

            local_path = workspace_dir / path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(content)

            file_sha256 = sha256_bytes(content)
            file_size = int(headers.get("X-File-Size", len(content)))
            file_lm = entry.get("lastModified", "")
            state["files"][path] = {"sha256": file_sha256, "size": file_size, "lastModified": file_lm}
            downloaded += 1
            print(f"  ✓ {path} ({file_size} bytes)")
        except Exception as e:
            print(f"  ✗ {path}: {e}", file=sys.stderr)

    save_state(workspace_dir, state)
    print(f"[init] 完成: 下载 {downloaded}/{len(oss_files)} 个文件")


def cmd_push(workspace_id: int, workspace_dir: Path, relative_path: str):
    """上传单个文件到 OSS。"""
    local_file = workspace_dir / relative_path
    if not local_file.exists():
        print(f"[ERROR] 文件不存在: {local_file}", file=sys.stderr)
        sys.exit(1)

    content = local_file.read_bytes()
    file_sha256 = sha256_bytes(content)

    url = _api_url(workspace_id, "/files/upload")
    # URL-encode 文件名：HTTP header 只支持 ASCII/latin-1，中文等需编码
    encoded_path = quote(relative_path, safe="/")
    headers = {
        "X-File-Path": encoded_path,
        "Content-Type": "application/octet-stream",
    }
    _, body, _ = _request("POST", url, data=content, headers=headers)
    result = json.loads(body)
    data = result.get("data", result)

    # 更新本地状态
    state = load_state(workspace_dir)
    state["files"][relative_path] = {"sha256": file_sha256, "size": len(content)}
    save_state(workspace_dir, state)

    print(f"[push] ✓ {relative_path} ({len(content)} bytes, sha256={file_sha256[:12]}...)")


def cmd_push_all(workspace_id: int, workspace_dir: Path):
    """扫描本地变更，批量推送。"""
    local_files = scan_local_files(workspace_dir)
    state = load_state(workspace_dir)

    to_push = []
    for f in local_files:
        path = f["path"]
        prev = state.get("files", {}).get(path)
        if prev and prev.get("sha256") == f["sha256"] and prev.get("size") == f["size"]:
            continue  # 未变化
        to_push.append(f)

    if not to_push:
        print("[push-all] 所有文件已同步，无变更")
        return

    print(f"[push-all] 发现 {len(to_push)} 个变更文件")
    pushed = 0
    for f in to_push:
        try:
            cmd_push(workspace_id, workspace_dir, f["path"])
            pushed += 1
        except SystemExit:
            print(f"  ✗ {f['path']}: 上传失败，跳过", file=sys.stderr)

    print(f"[push-all] 完成: 推送 {pushed}/{len(to_push)} 个文件")


def cmd_pull(workspace_id: int, workspace_dir: Path, relative_path: str):
    """下载单个文件到本地。"""
    dl_url = _api_url(workspace_id, f"/files/download?path={_url_quote(relative_path)}")
    _, body, headers = _request("GET", dl_url)

    local_path = workspace_dir / relative_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(body)

    file_sha256 = sha256_bytes(body)
    file_size = int(headers.get("X-File-Size", len(body)))

    # 更新状态
    state = load_state(workspace_dir)
    state["files"][relative_path] = {"sha256": file_sha256, "size": file_size}
    save_state(workspace_dir, state)

    print(f"[pull] ✓ {relative_path} ({file_size} bytes)")


def cmd_pull_all(workspace_id: int, workspace_dir: Path):
    """全量覆盖本地（等同于重新 init）。"""
    cmd_init(workspace_id, workspace_dir)


def cmd_sync_check(workspace_id: int, workspace_dir: Path):
    """快速检查 OSS 是否有变更（用于每轮对话前自动同步）。
    返回码: 0=已同步, 1=需要拉取, 2=错误
    """
    # 获取 OSS 文件列表及 lastModified
    url = _api_url(workspace_id, "/files")
    try:
        resp = _get_json(url)
    except Exception as e:
        print(f"[sync-check] ERROR: 无法获取 OSS 文件列表: {e}", file=sys.stderr)
        sys.exit(2)
    data = resp.get("data", resp)
    oss_files = data.get("files", [])

    # 构建 OSS 指纹：path|lastModified|size
    oss_fingerprints = []
    for f in oss_files:
        p = f.get("path", "")
        lm = f.get("lastModified", "")
        sz = f.get("size", 0)
        if p:
            oss_fingerprints.append(f"{p}|{lm}|{sz}")
    oss_fp = "\n".join(sorted(oss_fingerprints))

    # 本地指纹
    state = load_state(workspace_dir)
    local_fingerprints = []
    for p, info in state.get("files", {}).items():
        lm = info.get("lastModified", "")
        sz = info.get("size", 0)
        local_fingerprints.append(f"{p}|{lm}|{sz}")
    local_fp = "\n".join(sorted(local_fingerprints))

    if oss_fp == local_fp:
        print(f"[sync-check] ✓ 已同步 ({len(oss_files)} 文件)")
        sys.exit(0)
    else:
        new_files = [f for f in oss_files if f.get("path", "") not in state.get("files", {})]
        print(f"[sync-check] ⚠ 需要同步: OSS {len(oss_files)} 文件, 本地 {len(state.get('files', {}))} 文件" +
              (f", 新增 {len(new_files)}" if new_files else ""))
        sys.exit(1)


def cmd_status(workspace_id: int, workspace_dir: Path):
    """对比本地 manifest 与 OSS 状态。"""
    local_files = scan_local_files(workspace_dir)

    url = _api_url(workspace_id, "/sync")
    payload = json.dumps({"localFiles": local_files}).encode("utf-8")
    _, body, _ = _request("POST", url, data=payload,
                          headers={"Content-Type": "application/json"})
    result = json.loads(body)
    data = result.get("data", result)

    to_dl = data.get("toDownload", [])
    to_up = data.get("toUpload", [])
    conflict = data.get("toConflict", [])
    in_sync = data.get("inSync", [])

    print(f"=== 同步状态 (workspace/{workspace_id}) ===")
    print(f"  已同步: {len(in_sync)} 个文件")
    print(f"  需下载 (OSS→本地): {len(to_dl)} 个")
    for f in to_dl:
        print(f"    ↓ {f.get('path', '?')}")
    print(f"  需上传 (本地→OSS): {len(to_up)} 个")
    for f in to_up:
        print(f"    ↑ {f.get('path', '?')} ({f.get('size', 0)} bytes)")
    if conflict:
        print(f"  冲突: {len(conflict)} 个")
        for f in conflict:
            print(f"    ⚠ {f.get('path', '?')}")

    if not to_dl and not to_up and not conflict:
        print("  ✅ 全部同步一致")


# ── Helpers ───────────────────────────────────────────────────────

def _url_quote(path: str) -> str:
    """URL 编码路径（保留 / 不编码）。"""
    from urllib.parse import quote
    return quote(path, safe="/")


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Workspace OSS Sync CLI — Agent 工作区文件双向同步",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  ws_sync_cli.py init --workspace-id 1
  ws_sync_cli.py push --workspace-id 1 --path analysis/report.md
  ws_sync_cli.py push-all --workspace-id 1
  ws_sync_cli.py status --workspace-id 1
        """,
    )

    parser.add_argument("command", choices=["init", "push", "push-all", "pull", "pull-all", "status", "ensure-init", "sync-check"])
    parser.add_argument("--workspace-id", type=int, required=True,
                        help="工作区 ID")
    parser.add_argument("--workspace-dir", type=str, default=None,
                        help="本地 workspace 目录 (默认 /opt/data/workspace/{workspace_id})")
    parser.add_argument("--path", type=str, default=None,
                        help="文件相对路径 (push/pull 命令需要)")
    parser.add_argument("--api-base-url", type=str, default=None,
                        help="Backend API 基础 URL (默认 $CODESHARK_BOT_API_URL)")
    parser.add_argument("--api-key", type=str, default=None,
                        help="Bot API Key (默认 $CODESHARK_BOT_API_KEY)")

    args = parser.parse_args()

    # 全局配置覆盖
    global DEFAULT_API_BASE, DEFAULT_API_KEY
    if args.api_base_url:
        DEFAULT_API_BASE = args.api_base_url
    if args.api_key:
        DEFAULT_API_KEY = args.api_key

    # workspace 目录
    workspace_dir = Path(args.workspace_dir or
                         DEFAULT_WORKSPACE_DIR.format(workspace_id=args.workspace_id))

    # 执行命令
    cmd = args.command
    if cmd == "init":
        cmd_init(args.workspace_id, workspace_dir)
    elif cmd == "ensure-init":
        cmd_ensure_init(args.workspace_id)
    elif cmd == "push":
        if not args.path:
            print("[ERROR] push 命令需要 --path 参数", file=sys.stderr)
            sys.exit(1)
        cmd_push(args.workspace_id, workspace_dir, args.path)
    elif cmd == "push-all":
        cmd_push_all(args.workspace_id, workspace_dir)
    elif cmd == "pull":
        if not args.path:
            print("[ERROR] pull 命令需要 --path 参数", file=sys.stderr)
            sys.exit(1)
        cmd_pull(args.workspace_id, workspace_dir, args.path)
    elif cmd == "pull-all":
        cmd_pull_all(args.workspace_id, workspace_dir)
    elif cmd == "sync-check":
        cmd_sync_check(args.workspace_id, workspace_dir)
    elif cmd == "status":
        cmd_status(args.workspace_id, workspace_dir)


if __name__ == "__main__":
    main()
