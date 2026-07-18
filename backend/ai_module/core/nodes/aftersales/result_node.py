"""Result step node for aftersales workflow."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState
from ai_module.core.nodes.aftersales.constants import TYPE_LABELS


class AftersalesResultNode(BaseNode):
    """Step 7: render aftersales result."""

    def execute(self, state: ConversationState) -> ConversationState:
        flow_data = state.get("aftersales_flow") or {}
        refund_no = flow_data.get("refund_no", "")
        review_result = flow_data.get("review_result", {})
        approved = review_result.get("approved", False)
        review_reason = review_result.get("reason", "")
        refund_type = flow_data.get("refund_type", "refund_only")
        type_label = TYPE_LABELS.get(refund_type, "售后")

        if approved:
            if refund_type == "refund_only":
                response = f"""✅ 售后申请已通过，退款处理中！

售后单号：{refund_no}
类型：{type_label}
审核结果：{review_reason}

退款将在1-3个工作日内原路退回。"""
            else:
                response = f"""✅ 售后申请已通过！

售后单号：{refund_no}
类型：{type_label}
审核结果：{review_reason}

请将商品寄回，并在系统中填写退货快递单号。"""
        else:
            response = f"""📝 售后申请已提交，等待审核

售后单号：{refund_no}
类型：{type_label}
状态：待人工审核

我们会在1-2个工作日内完成审核，请耐心等待。"""

        state["response"] = response
        state["aftersales_flow"] = None
        state["quick_actions"] = [
            {
                "type": "refund_card",
                "label": "售后详情",
                "action": "aftersales_flow",
                "data": {
                    "refund_no": refund_no,
                    "status": review_result.get("status", "pending"),
                    "status_text": "已通过" if approved else "待审核",
                    "refund_type_text": type_label,
                    "product_name": flow_data.get("product_name", "商品"),
                    "refund_amount": flow_data.get("refund_amount", 0) / 100,
                    "created_at": "",
                },
            },
            {"type": "button", "label": "查看我的订单", "action": "navigate", "data": {"path": "/orders"}, "icon": "📦"},
            {"type": "button", "label": "继续购物", "action": "navigate", "data": {"path": "/products"}, "icon": "🛒"},
        ]
        return state

__all__ = ["AftersalesResultNode"]
