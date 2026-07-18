"""Purchase confirm coupon step node."""
from __future__ import annotations

from ai_module.core.state import ConversationState

from .base_step_node import PurchaseFlowStepNode


class PurchaseConfirmCouponNode(PurchaseFlowStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        return self.service.handle_confirm_coupon(state, self._get_flow_data(state))
