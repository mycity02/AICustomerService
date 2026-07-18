"""Order query mode resolution node."""
from __future__ import annotations

from ...state import ConversationState

from .base_step_node import OrderQueryStepNode


class OrderQueryModeNode(OrderQueryStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        state["_order_query_mode"] = self.service.resolve_mode(state)
        return state
