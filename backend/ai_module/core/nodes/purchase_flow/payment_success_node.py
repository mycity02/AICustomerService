"""Purchase payment success step node."""
from __future__ import annotations

from ai_module.core.state import ConversationState

from .base_step_node import PurchaseFlowStepNode


class PurchasePaymentSuccessNode(PurchaseFlowStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        return self.service.handle_payment_success(state, self._get_flow_data(state))
