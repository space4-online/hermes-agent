"""阿里百炼 DashScope 万相图像生成后端.

通过 DashScope HTTP 同步接口调用万相（Wanxiang）文生图模型，将文本 prompt
转换为图像 URL。支持 wan2.6-t2i（推荐）、wan2.5-t2i-preview、wan2.2-t2i-flash
等多个模型。

配置方式:
  1. 设置环境变量 DASHSCOPE_API_KEY（从百炼控制台获取）
  2. config.yaml 中设置:
       image_gen:
         provider: dashscope
         model: wan2.6-t2i          # 可选，默认 wan2.6-t2i

模型选择优先级:
  1. image_gen.model（config.yaml）
  2. DASHSCOPE_IMAGE_MODEL 环境变量
  3. 默认 wan2.6-t2i
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    resolve_aspect_ratio,
    success_response,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model catalog
# ---------------------------------------------------------------------------

_MODELS: Dict[str, Dict[str, Any]] = {
    "wan2.6-t2i": {
        "display": "万相 2.6 文生图",
        "speed": "~8s",
        "strengths": "最新模型，支持同步调用，高质量",
        "price": "¥0.04/张",
    },
    "wan2.5-t2i-preview": {
        "display": "万相 2.5 Preview",
        "speed": "~10s",
        "strengths": "自由尺寸，高分辨率",
        "price": "¥0.04/张",
    },
    "wan2.2-t2i-flash": {
        "display": "万相 2.2 极速版",
        "speed": "~4s",
        "strengths": "速度快，适合快速迭代",
        "price": "¥0.02/张",
    },
    "wan2.2-t2i-plus": {
        "display": "万相 2.2 专业版",
        "speed": "~8s",
        "strengths": "稳定性与成功率全面提升",
        "price": "¥0.04/张",
    },
}

DEFAULT_MODEL = "wan2.6-t2i"

# wan2.6 同步接口端点
_SYNC_ENDPOINT = (
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/"
    "multimodal-generation/generation"
)

# 尺寸映射: aspect_ratio → "宽*高"
_SIZES: Dict[str, str] = {
    "landscape": "1696*960",
    "square": "1280*1280",
    "portrait": "960*1696",
}

# HTTP 超时（万相同步接口通常 5-20 秒返回）
_HTTP_TIMEOUT = 60.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_api_key() -> Optional[str]:
    """Read DASHSCOPE_API_KEY from environment."""
    return os.environ.get("DASHSCOPE_API_KEY", "").strip() or None


def _resolve_model() -> str:
    """Decide which model to use based on config and env."""
    # 1. config.yaml image_gen.model
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
        section = cfg.get("image_gen") if isinstance(cfg, dict) else None
        if isinstance(section, dict):
            value = section.get("model")
            if isinstance(value, str) and value.strip() in _MODELS:
                return value.strip()
    except Exception as exc:
        logger.debug("Could not load image_gen.model: %s", exc)

    # 2. env var override
    env_model = os.environ.get("DASHSCOPE_IMAGE_MODEL", "").strip()
    if env_model in _MODELS:
        return env_model

    # 3. default
    return DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class DashScopeImageGenProvider(ImageGenProvider):
    """阿里百炼 DashScope 万相文生图后端."""

    @property
    def name(self) -> str:
        return "dashscope"

    @property
    def display_name(self) -> str:
        return "阿里百炼（万相）"

    def is_available(self) -> bool:
        return bool(_get_api_key())

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": model_id,
                "display": meta["display"],
                "speed": meta["speed"],
                "strengths": meta["strengths"],
                "price": meta["price"],
            }
            for model_id, meta in _MODELS.items()
        ]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "阿里百炼（万相）",
            "badge": "paid",
            "tag": "万相 wan2.6 文生图，国内可用，无需翻墙",
            "env_vars": [
                {
                    "key": "DASHSCOPE_API_KEY",
                    "prompt": "百炼 API Key",
                    "url": "https://bailian.console.aliyun.com/",
                },
            ],
        }

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        prompt = (prompt or "").strip()
        aspect = resolve_aspect_ratio(aspect_ratio)
        model_id = kwargs.get("model") or _resolve_model()

        if not prompt:
            return error_response(
                error="Prompt is required and must be a non-empty string",
                error_type="invalid_argument",
                provider="dashscope",
                aspect_ratio=aspect,
            )

        api_key = _get_api_key()
        if not api_key:
            return error_response(
                error=(
                    "DASHSCOPE_API_KEY not set. "
                    "Get your key from https://bailian.console.aliyun.com/"
                ),
                error_type="auth_required",
                provider="dashscope",
                aspect_ratio=aspect,
            )

        size = _SIZES.get(aspect, _SIZES["square"])

        # Build request payload (wan2.6 同步接口格式)
        payload = {
            "model": model_id,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ]
            },
            "parameters": {
                "size": size,
                "n": 1,
                "prompt_extend": True,
                "watermark": False,
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            logger.info(
                "Generating image with DashScope %s — prompt: %s",
                model_id,
                prompt[:80],
            )
            response = httpx.post(
                _SYNC_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=_HTTP_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            # Try to extract error message from response body
            error_detail = ""
            try:
                err_body = exc.response.json()
                error_detail = err_body.get("message", str(exc))
            except Exception:
                error_detail = str(exc)
            logger.debug("DashScope API error: %s", error_detail, exc_info=True)
            return error_response(
                error=f"DashScope API error: {error_detail}",
                error_type="api_error",
                provider="dashscope",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )
        except Exception as exc:
            logger.debug("DashScope request failed", exc_info=True)
            return error_response(
                error=f"DashScope request failed: {exc}",
                error_type="network_error",
                provider="dashscope",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        # Extract image URL from response
        # Response shape: output.choices[0].message.content[0].image
        try:
            output = data.get("output", {})
            choices = output.get("choices", [])
            if not choices:
                raise ValueError("No choices in response")
            message = choices[0].get("message", {})
            content = message.get("content", [])
            if not content:
                raise ValueError("No content in response message")

            image_url = None
            for item in content:
                if isinstance(item, dict) and "image" in item:
                    image_url = item["image"]
                    break

            if not image_url:
                raise ValueError("No image URL found in response content")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.debug("DashScope response parsing failed: %s\nRaw: %s", exc, data)
            return error_response(
                error=f"Failed to parse DashScope response: {exc}",
                error_type="parse_error",
                provider="dashscope",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        logger.info("DashScope image generated successfully: %s", image_url[:80])

        return success_response(
            image=image_url,
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
            provider="dashscope",
            extra={"size": size},
        )


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------


def register(ctx) -> None:
    """Plugin entry point — wire DashScopeImageGenProvider into the registry."""
    ctx.register_image_gen_provider(DashScopeImageGenProvider())
