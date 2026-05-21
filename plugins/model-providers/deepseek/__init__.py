"""DeepSeek provider profile.

deepseek-v4-pro and deepseek-v4-flash support the ``thinking`` toggle and
``reasoning_effort`` (low/medium/high) as of May 2026.  Older aliases like
``deepseek-chat`` / ``deepseek-reasoner`` are deprecated (→ v4-flash) and do
not accept these parameters, so we gate the extras by model name.
"""

from typing import Any

from providers import register_provider
from providers.base import ProviderProfile


def _is_thinking_capable(model: str) -> bool:
    """Return True for DeepSeek v4 models that accept thinking + reasoning_effort."""
    m = (model or "").lower()
    return "v4-pro" in m or "v4-flash" in m


class DeepSeekProfile(ProviderProfile):
    """DeepSeek native API — thinking + reasoning_effort for v4 models."""

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, model: str = "", **context: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Emit extra_body.thinking and top-level reasoning_effort for v4 models.

        DeepSeek v4-pro / v4-flash accept:
          - extra_body: {"thinking": {"type": "enabled" | "disabled"}}
          - top-level:  reasoning_effort = "low" | "medium" | "high"

        Older model aliases (deepseek-chat, deepseek-reasoner) do not support
        these parameters and are left unchanged.
        """
        if not _is_thinking_capable(model):
            return {}, {}

        extra_body: dict[str, Any] = {}
        top_level: dict[str, Any] = {}

        if not reasoning_config or not isinstance(reasoning_config, dict):
            # No explicit config → enable thinking at medium effort by default
            extra_body["thinking"] = {"type": "enabled"}
            top_level["reasoning_effort"] = "medium"
            return extra_body, top_level

        enabled = reasoning_config.get("enabled", True)
        if enabled is False:
            extra_body["thinking"] = {"type": "disabled"}
            return extra_body, top_level

        # Thinking enabled — map effort level
        extra_body["thinking"] = {"type": "enabled"}
        effort = (reasoning_config.get("effort") or "").strip().lower()
        top_level["reasoning_effort"] = effort if effort in ("low", "medium", "high") else "medium"
        return extra_body, top_level


deepseek = DeepSeekProfile(
    name="deepseek",
    aliases=("deepseek-chat",),
    env_vars=("DEEPSEEK_API_KEY",),
    display_name="DeepSeek",
    description="DeepSeek — native DeepSeek API",
    signup_url="https://platform.deepseek.com/",
    fallback_models=(
        "deepseek-chat",
        "deepseek-reasoner",
    ),
    base_url="https://api.deepseek.com/v1",
)

register_provider(deepseek)
