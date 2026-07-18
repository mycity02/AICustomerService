"""Select-order step node for aftersales workflow."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState
from ai_module.core.nodes.aftersales.constants import ORDER_STATUS_MAP


class AftersalesSelectOrderNode(BaseNode):
    """Step 1: list eligible orders."""

    def execute(self, state: ConversationState) -> ConversationState:
        from database.connection import get_db_context
        from services.refund_service import RefundService

        with get_db_context() as db:
            service = RefundService(db)
            orders = service.get_eligible_orders(state.get("user_id"))

        if not orders:
            state["response"] = "您暂时没有可以申请售后的订单。\n\n只有已支付、已送达或已完成的订单才能申请售后。"
            state["aftersales_flow"] = None
            state["quick_actions"] = [
                {"type": "button", "label": "查看我的订单", "action": "navigate", "data": {"path": "/orders"}, "icon": "📦"},
            ]
            return state

        order_cards = []
        for order in orders[:5]:
            product_name = order["items"][0]["product_title"] if order["items"] else "商品"
            order_cards.append(
                {
                    "type": "order_card_simple",
                    "label": product_name,
                    "action": "aftersales_flow",
                    "data": {
                        "step": "select_type",
                        "order_id": order["id"],
                        "order_no": order["order_no"],
                        "status": order["status"],
                        "status_text": ORDER_STATUS_MAP.get(order["status"], order["status"]),
                        "product_name": product_name,
                        "total_amount": order["total_amount"] / 100,
                        "created_at": order["created_at"],
                        "items": order["items"],
                    },
                }
            )

        state["response"] = f"请选择需要售后的订单（共 {len(orders)} 个可售后订单）："
        state["quick_actions"] = order_cards
        state["aftersales_flow"] = {"step": "select_order"}
        return state

__all__ = ["AftersalesSelectOrderNode"]
