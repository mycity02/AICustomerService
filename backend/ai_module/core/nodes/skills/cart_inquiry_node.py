"""
Shopping cart inquiry fallback node.
"""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState


class CartInquiryNode(BaseNode):
    """Provide a safe response for cart questions before full cart workflow exists."""

    def execute(self, state: ConversationState) -> ConversationState:
        state["response"] = (
            "目前助手还不支持通过对话直接查询购物车内容，"
            "不过您可以直接打开购物车页面查看商品、数量和金额。"
        )
        state["quick_actions"] = [
            {
                "type": "button",
                "label": "查看购物车",
                "action": "navigate",
                "data": {"path": "/cart"},
                "icon": "🛒",
                "color": "primary",
            },
            {
                "type": "button",
                "label": "查看我的订单",
                "action": "send_question",
                "data": {"question": "查看我的订单"},
                "icon": "📦",
            },
        ]
        return state
