"""Select-type step node for aftersales workflow."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState


class AftersalesSelectTypeNode(BaseNode):
    """Step 2: choose aftersales type."""

    def execute(self, state: ConversationState) -> ConversationState:
        flow_data = state.get("aftersales_flow") or {}
        order_id = flow_data.get("order_id")
        order_status = flow_data.get("status", "paid")

        if not order_id:
            state["response"] = "请先选择要售后的订单"
            return state

        product_name = flow_data.get("product_name", "商品")
        order_no = flow_data.get("order_no", "")
        state["aftersales_flow"] = {**flow_data, "step": "select_type"}

        buttons = []
        if order_status in ("paid",):
            buttons.append(
                {
                    "type": "button",
                    "label": "仅退款",
                    "action": "aftersales_flow",
                    "data": {**flow_data, "step": "select_reason", "refund_type": "refund_only"},
                    "icon": "💰",
                }
            )

        if order_status in ("delivered", "completed"):
            buttons.extend(
                [
                    {
                        "type": "button",
                        "label": "仅退款",
                        "action": "aftersales_flow",
                        "data": {**flow_data, "step": "select_reason", "refund_type": "refund_only"},
                        "icon": "💰",
                    },
                    {
                        "type": "button",
                        "label": "退货退款",
                        "action": "aftersales_flow",
                        "data": {**flow_data, "step": "select_reason", "refund_type": "return_refund"},
                        "icon": "📦",
                    },
                    {
                        "type": "button",
                        "label": "换货",
                        "action": "aftersales_flow",
                        "data": {**flow_data, "step": "select_reason", "refund_type": "exchange"},
                        "icon": "🔄",
                    },
                ]
            )

        buttons.append(
            {
                "type": "button",
                "label": "取消售后",
                "action": "aftersales_flow",
                "data": {"step": "cancel"},
                "icon": "❌",
            }
        )

        state["response"] = f"订单 {order_no} - {product_name}\n\n请选择售后类型："
        state["quick_actions"] = buttons
        return state

__all__ = ["AftersalesSelectTypeNode"]
