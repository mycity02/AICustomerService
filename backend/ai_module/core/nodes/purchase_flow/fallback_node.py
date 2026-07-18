"""Fallback node for unknown purchase flow steps."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState


class PurchaseFallbackNode(BaseNode):
    """Return a stable error when the purchase step cannot be resolved."""

    def execute(self, state: ConversationState) -> ConversationState:
        state["response"] = "抱歉，购买流程出现了问题，请重新开始。"
        return state
