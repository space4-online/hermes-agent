# Hermes Agent 部署上下文

## 运行环境

你正在 **Docker 容器**中运行，部署在服务器上为多个用户提供服务。

**关键路径映射**：
- 容器内 `/opt/data` = 宿主机 `~/.hermes`（volume 挂载，双向修改实时生效）
- 配置文件：`/opt/data/.env`、`/opt/data/config.yaml`
- 日志输出：`/opt/data/logs/`
- Sessions / 记忆：`/opt/data/sessions/`、`/opt/data/memories/`

**环境变量来源**：
1. `/home/server/env/hermes.env`（通过 docker-compose `env_file` 注入，修改后需重启容器）
2. `/opt/data/.env`（即宿主机 `~/.hermes/.env`，load_hermes_dotenv 以 override=True 加载，修改后无需重启容器）

**向用户建议配置时**：
- API Key 类（DASHSCOPE_API_KEY 等）：修改 `/opt/data/.env`（即宿主机 `~/.hermes/.env`），无需重启
- 模型选择类（HERMES_MODEL 等）：修改 `/opt/data/.env` 即可（不需改 docker-compose）
- 运行时指不应要指导用户去编辑 `hermes.env`，那是部署层配置，用户应不负责

## Hermes Agent Persona

<!--
This file defines the agent's personality and tone.
The agent will embody whatever you write here.
Edit this to customize how Hermes communicates with you.

Examples:
  - "You are a warm, playful assistant who uses kaomoji occasionally."
  - "You are a concise technical expert. No fluff, just facts."
  - "You speak like a friendly coworker who happens to know everything."

This file is loaded fresh each message -- no restart needed.
Delete the contents (or this file) to use the default personality.
-->