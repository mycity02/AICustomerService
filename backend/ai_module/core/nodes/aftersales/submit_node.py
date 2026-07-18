"""Submit step node for aftersales workflow."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState


class AftersalesSubmitNode(BaseNode):
    """Step 6: submit request and auto-review."""

    def execute(self, state: ConversationState) -> ConversationState:
        from database.connection import get_db_context
        from services.refund_service import RefundService

        flow_data = state.get("aftersales_flow") or {}
        user_id = state.get("user_id")
        order_id = flow_data.get("order_id")
        items = flow_data.get("items", [])
        order_item_id = items[0].get("id") if items else None

        with get_db_context() as db:
            service = RefundService(db)
            refund = service.create_refund_request(
                user_id=user_id,
                order_id=order_id,
                order_item_id=order_item_id,
                refund_type=flow_data.get("refund_type", "refund_only"),
                reason=flow_data.get("reason", "other"),
                description=flow_data.get("description"),
                evidence_images=flow_data.get("evidence_images"),
                refund_amount=flow_data.get("refund_amount", 0),
            )
            review_result = service.auto_review(refund["id"])

        flow_data["refund_id"] = refund["id"]
        flow_data["refund_no"] = refund["refund_no"]
        flow_data["review_result"] = review_result
        flow_data["step"] = "result"
        state["aftersales_flow"] = flow_data
        return state

__all__ = ["AftersalesSubmitNode"]
