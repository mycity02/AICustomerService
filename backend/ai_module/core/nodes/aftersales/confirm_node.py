"""Confirm step node for aftersales workflow."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState
from ai_module.core.nodes.aftersales.constants import REASON_LABELS, TYPE_LABELS


class AftersalesConfirmNode(BaseNode):
    """Step 5: confirmation message."""

    def execute(self, state: ConversationState) -> ConversationState:
        flow_data = state.get("aftersales_flow") or {}
        order_no = flow_data.get("order_no", "")
        product_name = flow_data.get("product_name", "商品")
        refund_type = flow_data.get("refund_type", "refund_only")
        reason = flow_data.get("reason", "other")
        description = flow_data.get("description", "")
        items = flow_data.get("items", [])

        if items:
            refund_amount = items[0].get("price", 0)
        else:
            refund_amount = int(flow_data.get("total_amount", 0) * 100)

        flow_data["refund_amount"] = refund_amount
        state["aftersales_flow"] = {**flow_data, "step": "confirm"}

        type_label = TYPE_LABELS.get(refund_type, "售后")
        reason_label = REASON_LABELS.get(reason, "其他")
        amount_display = f"¥{refund_amount / 100:.2f}" if refund_type != "exchange" else "换货不涉及退款"

        response = f"""📋 售后申请确认

订单号：{order_no}
商品：{product_name}
售后类型：{type_label}
原因：{reason_label}
退款金额：{amount_display}"""
        if description:
            response += f"\n问题描述：{description}"
        response += "\n\n请确认以上信息："

        state["response"] = response
        state["quick_actions"] = [
            {
                "type": "button",
                "label": "确认提交",
                "action": "aftersales_flow",
                "data": {**flow_data, "step": "submit"},
                "icon": "✅",
            },
            {
                "type": "button",
                "label": "返回修改",
                "action": "aftersales_flow",
                "data": {**flow_data, "step": "select_type"},
                "icon": "✏️",
            },
        ]
        return state

__all__ = ["AftersalesConfirmNode"]
