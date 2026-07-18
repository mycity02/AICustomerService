"""Cancel step node for aftersales workflow."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState


class AftersalesCancelNode(BaseNode):
    """Cancel action within aftersales workflow context."""

    def execute(self, state: ConversationState) -> ConversationState:
        state["aftersales_flow"] = None
        state["response"] = "已为您取消本次售后申请。需要的话我可以帮您重新发起。"
        state["quick_actions"] = [
            {"type": "button", "label": "重新申请售后", "action": "send_question", "data": {"question": "我要申请售后"}},
            {"type": "button", "label": "查看我的订单", "action": "navigate", "data": {"path": "/orders"}, "icon": "📦"},
        ]
        return state

__all__ = ["AftersalesCancelNode"]
