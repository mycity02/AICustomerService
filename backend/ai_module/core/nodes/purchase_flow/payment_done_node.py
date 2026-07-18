"""Purchase payment done step node."""
from __future__ import annotations

from ai_module.core.state import ConversationState

from .base_step_node import PurchaseFlowStepNode


class PurchasePaymentDoneNode(PurchaseFlowStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        return self.service.handle_payment_done(state, self._get_flow_data(state))
