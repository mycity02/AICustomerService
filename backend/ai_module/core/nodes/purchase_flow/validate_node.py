"""Purchase flow validation node."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState


class PurchaseValidateNode(BaseNode):
    """Validate purchase flow state before routing."""

    def execute(self, state: ConversationState) -> ConversationState:
        flow = state.get("purchase_flow") or {}
        if not flow.get("step"):
            raise ValueError("purchase_flow.step is required")
        return state
