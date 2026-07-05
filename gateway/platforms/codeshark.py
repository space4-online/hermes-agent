"""
CodeShark workspace platform adapter.

Connects CodeShark backend to Hermes gateway using the standard Platform Adapter
pattern — equivalent to DingTalk/Feishu/Telegram adapters but with HTTP push
as the transport layer.

Message flow:
  1. Backend POST /incoming → adapter receives user message
  2. Adapter emits MessageEvent → gateway routes to SessionStore → AIAgent
  3. Agent produces reply → Adapter.send() → POST to backend Bot API

Requires:
  - aiohttp (already available in the gateway)
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    web = None  # type: ignore[assignment]

try:
    import aiohttp
    AIOHTTP_CLIENT_AVAILABLE = True
except ImportError:
    AIOHTTP_CLIENT_AVAILABLE = False
    aiohttp = None  # type: ignore[assignment]

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import (
    BasePlatformAdapter,
    MessageType,
    SendResult,
)

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8645
# 幂等缓存：记录已处理的 message_id，防止后端重复推送
_DEDUP_CACHE_MAX = 2000
_DEDUP_TTL_SECONDS = 300  # 5 分钟


class CodesharkAdapter(BasePlatformAdapter):
    """CodeShark workspace platform adapter.

    消息接收：后端 POST /incoming 推送用户消息到此 adapter
    消息回复：调用后端 Bot API POST /v2/workspace/bot/{wid}/messages
    """

    def __init__(self, config: PlatformConfig):
        super().__init__(config, Platform.CODESHARK)
        extra = config.extra or {}

        # HTTP 服务端配置（接收后端推送）
        self._host = str(extra.get("host", os.getenv("CODESHARK_ADAPTER_HOST", DEFAULT_HOST)))
        self._port = int(extra.get("port", os.getenv("CODESHARK_ADAPTER_PORT", str(DEFAULT_PORT))))
        self._secret = str(extra.get("secret", os.getenv("CODESHARK_ADAPTER_SECRET", "")))

        # Bot API 配置（发送回复到后端）
        self._bot_api_url = str(extra.get("bot_api_url", os.getenv("CODESHARK_BOT_API_URL", "")))
        self._bot_api_key = str(extra.get("bot_api_key", os.getenv("CODESHARK_BOT_API_KEY", "")))

        # aiohttp 运行时
        self._app = None
        self._runner = None
        self._site = None
        self._http_session: Optional[Any] = None

        # 幂等去重缓存：{message_id: timestamp}
        self._dedup_cache: Dict[str, float] = {}

    # ────────────────────────────────────────────────────────────
    # Source building
    # ────────────────────────────────────────────────────────────

    def _build_source(
        self,
        chat_id: str,
        chat_name: Optional[str] = None,
        chat_type: str = "dm",
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        message_id: Optional[str] = None,
    ):
        """构建 SessionSource 用于 session 路由和上下文管理。"""
        return self.build_source(
            chat_id=chat_id,
            chat_name=chat_name,
            chat_type=chat_type,
            user_id=user_id,
            user_name=user_name,
            message_id=message_id,
        )

    # ────────────────────────────────────────────────────────────
    # Lifecycle
    # ────────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """启动 HTTP 端点，接收后端推送的用户消息。"""
        if not AIOHTTP_AVAILABLE:
            logger.error("[Codeshark] aiohttp not installed, cannot start adapter")
            return False

        try:
            self._app = web.Application()
            self._app.router.add_post("/incoming", self._handle_incoming)
            self._app.router.add_get("/health", self._handle_health)

            self._runner = web.AppRunner(self._app)
            await self._runner.setup()
            self._site = web.TCPSite(self._runner, self._host, self._port)
            await self._site.start()

            # 初始化 HTTP 客户端（用于 Bot API 回复）
            if AIOHTTP_CLIENT_AVAILABLE:
                self._http_session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30)
                )

            self._mark_connected()
            logger.info(
                "[Codeshark] Adapter listening on http://%s:%d",
                self._host, self._port,
            )
            return True

        except Exception as e:
            logger.error("[Codeshark] Failed to start adapter: %s", e)
            return False

    async def disconnect(self) -> None:
        """停止 HTTP 端点。"""
        self._mark_disconnected()
        if self._http_session:
            await self._http_session.close()
            self._http_session = None
        if self._site:
            await self._site.stop()
            self._site = None
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._app = None
        logger.info("[Codeshark] Adapter stopped")

    # ────────────────────────────────────────────────────────────
    # Incoming message handler
    # ────────────────────────────────────────────────────────────

    async def _handle_incoming(self, request: "web.Request") -> "web.Response":
        """处理后端推送的用户消息。

        请求体:
            {
                "workspace_id": 123,
                "message_id": 456,
                "sender_id": "78",
                "sender_name": "张三",
                "content": "@Hermes 帮我分析代码",
                "message_type": "TEXT",
                "reply_to_id": null
            }
        """
        try:
            # 读取请求体
            body_bytes = await request.read()
            body_text = body_bytes.decode("utf-8")

            # HMAC 验签
            if self._secret:
                signature = request.headers.get("X-Signature", "")
                expected = hmac.new(
                    self._secret.encode("utf-8"),
                    body_bytes,
                    hashlib.sha256,
                ).hexdigest()
                if not hmac.compare_digest(signature, expected):
                    logger.warning("[Codeshark] Invalid signature, rejecting request")
                    return web.json_response({"ok": False, "error": "invalid signature"}, status=403)

            body = json.loads(body_text)

            # 幂等去重
            message_id = str(body.get("message_id", ""))
            if message_id and self._is_duplicate(message_id):
                logger.debug("[Codeshark] Duplicate message_id=%s, skipping", message_id)
                return web.json_response({"ok": True, "deduplicated": True})

            # 解析消息字段
            workspace_id = str(body.get("workspace_id", ""))
            conversation_id = str(body.get("conversation_id", ""))
            sender_id = str(body.get("sender_id", ""))
            sender_name = str(body.get("sender_name", sender_id))
            content = str(body.get("content", ""))
            message_type_raw = str(body.get("message_type", "TEXT")).upper()

            if not workspace_id or not content:
                return web.json_response(
                    {"ok": False, "error": "missing workspace_id or content"}, status=400
                )

            # 去除 @Hermes 前缀（保留实际指令内容）
            text = self._strip_mention(content)

            # 构造 MessageEvent
            # chat_id 格式: codeshark:{wid}[:{cid}]（conversation_id 可选，向后兼容）
            from gateway.platforms.base import MessageEvent
            _chat_id = f"codeshark:{workspace_id}"
            if conversation_id:
                _chat_id = f"codeshark:{workspace_id}:{conversation_id}"
            source = self._build_source(
                chat_id=_chat_id,
                chat_name=f"Workspace {workspace_id}",
                chat_type="group",
                user_id=sender_id,
                user_name=sender_name,
                message_id=message_id,
            )

            # 注入 workspace 上下文
            workspace_dir = f"/opt/data/workspace/{workspace_id}"
            api_url = self._bot_api_url or ""
            api_key = self._bot_api_key or ""
            sync_base = (
                f"python3 skills/codeshark/workspace-sync/scripts/ws_sync_cli.py"
                f" --api-base-url {api_url}"
                f" --api-key {api_key}"
                f" --workspace-id {workspace_id}"
            )
            channel_prompt = (
                f"Workspace {workspace_id}. Work dir: {workspace_dir}/. "
                f"Use this dir for all file ops. "
                f"On start: {sync_base} init. "
                f"After write_file: {sync_base} push --path <path>."
            )
            event = MessageEvent(
                text=text,
                message_type=MessageType.TEXT,
                source=source,
                message_id=message_id,
                timestamp=datetime.now(),
                channel_prompt=channel_prompt,
            )

            # 触发 gateway 消息处理流程
            await self.handle_message(event)

            return web.json_response({"ok": True})

        except json.JSONDecodeError:
            return web.json_response({"ok": False, "error": "invalid JSON"}, status=400)
        except Exception as e:
            logger.error("[Codeshark] Error handling incoming message: %s", e, exc_info=True)
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def _handle_health(self, request: "web.Request") -> "web.Response":
        """健康检查端点。"""
        return web.json_response({
            "status": "ok",
            "platform": "codeshark",
            "connected": self.is_connected,
        })

    # ────────────────────────────────────────────────────────────
    # Send (reply to backend via Bot API)
    # ────────────────────────────────────────────────────────────

    # ── 合法的 messageType 白名单 ──
    _VALID_MESSAGE_TYPES = frozenset({
        "TEXT", "FILE", "ERROR", "TASK_EVENT",
        "AGENT_PROGRESS", "SYSTEM_NOTICE", "CARD",
    })

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        """通过 Bot API 发送回复消息到后端。

        chat_id 格式: "codeshark:{workspace_id}"

        metadata 约定（统一格式协议）：
          - message_type: 从 metadata 中提取，默认为 "TEXT"
          - content_format: "markdown"（Hermes 默认）| "plain" | "json" | "card"
          - card_type: CARD 消息的卡片类型（status/task/analysis/result）
          - 其他字段：透传给前端对应渲染组件
        """
        if not self._bot_api_url:
            logger.warning("[Codeshark] bot_api_url not configured, cannot send reply")
            return SendResult(success=False, error="bot_api_url not configured")

        try:
            # 解析 workspace_id 和 conversation_id
            # chat_id 格式: codeshark:{wid} 或 codeshark:{wid}:{cid}
            _parts = chat_id.split(":") if ":" in chat_id else [chat_id]
            workspace_id = _parts[1] if len(_parts) >= 2 else _parts[0]
            conversation_id = _parts[2] if len(_parts) >= 3 else None

            # ── 平台消息格式化（一站式：去内部块 + 转 ASCII）──
            raw_len = len(content)
            raw_preview = content[:100].replace("\n", "\\n")
            logger.info(
                "[Codeshark] send() raw=%d chars, preview: %s...",
                raw_len, raw_preview,
            )
            try:
                content = self._format_for_platform(content)
            except Exception as fmt_err:
                logger.error("[Codeshark] _format_for_platform failed: %s", fmt_err, exc_info=True)
            clean_preview = content[:100].replace("\n", "\\n") if content else "(empty)"
            logger.info(
                "[Codeshark] send() clean=%d chars, preview: %s...",
                len(content), clean_preview,
            )

            # ── 从 metadata 中提取 message_type ──
            out_meta = dict(metadata) if metadata else {}

            message_type = out_meta.pop("message_type", "TEXT")
            if message_type not in self._VALID_MESSAGE_TYPES:
                logger.warning(
                    "[Codeshark] Unknown message_type=%s, fallback to TEXT",
                    message_type,
                )
                message_type = "TEXT"

            # ── 设置默认 content_format ──
            if "content_format" not in out_meta:
                if message_type == "CARD":
                    out_meta["content_format"] = "card"
                else:
                    out_meta["content_format"] = "markdown"

            # ── CARD 类型校验：必须有 card_type ──
            if message_type == "CARD" and "card_type" not in out_meta:
                logger.warning(
                    "[Codeshark] CARD message missing card_type, fallback to TEXT"
                )
                message_type = "TEXT"
                out_meta["content_format"] = "markdown"

            payload = {
                "senderType": "HERMES",
                "senderId": "hermes",
                "content": content,
                "messageType": message_type,
                "metadata": json.dumps(out_meta, ensure_ascii=False) if out_meta else None,
            }
            if reply_to:
                try:
                    payload["replyToId"] = int(reply_to)
                except (ValueError, TypeError):
                    pass

            # 构造 Bot API URL（带 conversation_id 时使用新路径）
            _api_base = self._bot_api_url.rstrip('/')
            if conversation_id:
                url = f"{_api_base}/v2/workspace/bot/{workspace_id}/conversation/{conversation_id}/messages"
            else:
                url = f"{_api_base}/v2/workspace/bot/{workspace_id}/messages"
            headers = {
                "Content-Type": "application/json",
                "X-Bot-Api-Key": self._bot_api_key,
            }

            if self._http_session and not self._http_session.closed:
                async with self._http_session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        msg_id = str(data.get("data", {}).get("id", ""))
                        logger.info(
                            "[Codeshark] Reply sent | wid=%s msgId=%s type=%s fmt=%s",
                            workspace_id, msg_id, message_type,
                            out_meta.get("content_format", "-"),
                        )
                        return SendResult(success=True, message_id=msg_id)
                    else:
                        body = await resp.text()
                        logger.warning(
                            "[Codeshark] Bot API returned %d | wid=%s body=%s",
                            resp.status, workspace_id, body[:200],
                        )
                        return SendResult(success=False, error=f"HTTP {resp.status}")
            else:
                logger.warning("[Codeshark] HTTP session not available for send()")
                return SendResult(success=False, error="HTTP session unavailable")

        except Exception as e:
            logger.error("[Codeshark] send() failed: %s", e, exc_info=True)
            return SendResult(success=False, error=str(e))

    # ────────────────────────────────────────────────────────────
    # Abstract method: get_chat_info
    # ────────────────────────────────────────────────────────────

    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """返回 workspace 基本信息。"""
        _parts = chat_id.split(":") if ":" in chat_id else [chat_id]
        workspace_id = _parts[1] if len(_parts) >= 2 else _parts[0]
        conversation_id = _parts[2] if len(_parts) >= 3 else None
        info = {
            "name": f"Workspace {workspace_id}",
            "type": "group",
            "platform": "codeshark",
        }
        if conversation_id:
            info["name"] = f"Workspace {workspace_id} / Conv {conversation_id}"
        return info

    # ────────────────────────────────────────────────────────────
    # Text normalization
    # ────────────────────────────────────────────────────────────

    @staticmethod
    def _format_for_platform(text: str) -> str:
        """Post-process agent output before delivering to the Codeshark frontend.

        All platform-specific formatting lives here, at the adapter boundary.
        Agent internal processing stays clean.
        """
        if not text:
            return text
        import re

        # ── 1. Strip <tool_calls>...<invoke>...</invoke>...</tool_calls> ──
        text = re.sub(
            r"<tool_calls>\s*(?:<invoke[^>]*>.*?</invoke>\s*)*</tool_calls>",
            "", text, flags=re.DOTALL,
        )
        # Standalone invoke blocks
        text = re.sub(r"<invoke[^>]*>.*?</invoke>", "", text, flags=re.DOTALL)

        # ── 2. Strip reasoning lines (💭 prefix) ──
        # Remove lines starting with 💭 and their continuation (until blank line)
        text = re.sub(r"💭[^\n]*(?:\n(?!\n|💭)[^\n]*)*", "", text)

        # ── 3. Replace typographic characters with ASCII ──
        for typo, ascii_char in [
            ("“", '"'),   # "
            ("”", '"'),   # "
            ("‘", "'"),   # '
            ("’", "'"),   # '
            ("–", "--"),  # –
            ("—", "---"), # —
            ("…", "..."), # …
        ]:
            text = text.replace(typo, ascii_char)

        # ── 4. Clean up ──
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # ────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────

    def _strip_mention(self, content: str) -> str:
        """去除 @Hermes/@hermes 前缀，保留实际指令。"""
        text = content.strip()
        for prefix in ("@Hermes ", "@hermes ", "@Hermes\n", "@hermes\n"):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                break
        # 仅有 @Hermes 无后续内容时，当作打招呼
        if text in ("@Hermes", "@hermes"):
            text = "你好"
        return text

    def _is_duplicate(self, message_id: str) -> bool:
        """检测是否为重复推送（幂等缓存）。"""
        now = time.time()

        # 清理过期条目
        if len(self._dedup_cache) > _DEDUP_CACHE_MAX:
            expired = [k for k, v in self._dedup_cache.items() if now - v > _DEDUP_TTL_SECONDS]
            for k in expired:
                del self._dedup_cache[k]

        if message_id in self._dedup_cache:
            return True
        self._dedup_cache[message_id] = now
        return False
