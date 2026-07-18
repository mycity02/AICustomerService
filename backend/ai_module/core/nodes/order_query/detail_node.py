"""Order query detail node."""
from __future__ import annotations

from ...state import ConversationState

from .base_step_node import OrderQueryStepNode


class OrderQueryDetailNode(OrderQueryStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        return self.service.handle_order_detail(state)
