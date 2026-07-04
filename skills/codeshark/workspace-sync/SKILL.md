---
name: workspace-sync
description: CodeShark workspace 文件同步工具 — 在 Agent 本地与 Backend OSS 之间双向同步工作区文件。Agent 启动时 init 拉取已有文件，写入后 push 回传 OSS。
version: 1.0.0
author: codeshark
metadata:
  hermes:
    tags:
      - workspace
      - sync
      - oss
      - file
    auto_load:
      platform: codeshark
---

# Workspace Sync Skill

## 角色定义

你是 workspace 文件同步工具。在 Agent 本地文件系统 (`/opt/data/workspace/{workspace_id}/`) 与 Backend OSS 之间双向同步文件。

## 核心命令

| 命令 | 说明 |
|------|------|
| `ensure-init` | 为已有工作区补充 OSS 文件夹初始化（幂等） |
| `init` | 从 OSS 全量拉取文件到本地，创建 `.workspace_sync_state.json` 状态文件 |
| `push --path <p>` | 上传单个文件到 OSS |
| `push-all` | 扫描本地变更，批量上传 |
| `pull --path <p>` | 下载单个文件到本地 |
| `pull-all` | 全量拉取 OSS 覆盖本地 |
| `status` | 对比本地与 OSS 差异 |

## 使用方式

脚本位置: `skills/codeshark/workspace-sync/scripts/ws_sync_cli.py`

```bash
# 环境变量（与 CodesharkAdapter 共用）
export CODESHARK_BOT_API_URL="https://dev.codeshark.cn/api"
export CODESHARK_BOT_API_KEY="your-key"

# 启动时：拉取已有文件
python3 ws_sync_cli.py init --workspace-id {workspace_id}

# 写入后：上传单个文件
python3 ws_sync_cli.py push --workspace-id {workspace_id} --path analysis/report.md

# 批量：一次性推送所有变更
python3 ws_sync_cli.py push-all --workspace-id {workspace_id}

# 检查：查看同步状态
python3 ws_sync_cli.py status --workspace-id {workspace_id}
```

## 同步规则

1. **启动时必须 init** — 否则可能覆盖队友已在 OSS 上的文件
2. **每次 write_file 后 push** — 保持 OSS 实时更新
3. **push 失败重试一次** — 网络抖动容错，仍失败则告知用户
4. **不覆盖未变更文件** — push-all 通过 SHA256 对比跳过无变更文件
5. **所有路径均相对于 workspace 根目录** — 不要包含 `/opt/data/workspace/{wid}/` 前缀

## 认证

所有 API 请求使用 `X-Bot-Api-Key` header，密钥来自:
1. `--api-key` 参数
2. 环境变量 `CODESHARK_BOT_API_KEY`

## 目录结构

```
/opt/data/workspace/{workspace_id}/
  .workspace_sync_state.json    ← 本地同步状态（SHA256、size、路径）
  analysis/
    report.md
  generated/
    code.py
```
