"""Order query workflow implementation."""
from __future__ import annotations

from ...nodes.order_query import OrderQueryDetailNode, OrderQueryListNode, OrderQueryModeNode
from ...state import ConversationState
from ..base import BaseWorkflow
from .contracts import OrderQueryMode
from .service import OrderQueryService
from .state_machine import OrderQueryState, next_state


class OrderQueryWorkflow(BaseWorkflow):
    name = "order_query"
    stream_enabled = False

    def __init__(self, service: OrderQueryService | None = None):
        self.service = service or OrderQueryService()
        self.mode_node = OrderQueryModeNode(self.service)
        self.list_node = OrderQueryListNode(self.service)
        self.detail_node = OrderQueryDetailNode(self.service)

    def execute(self, state: ConversationState) -> ConversationState:
        current = OrderQueryState.START

        while current != OrderQueryState.END:
            current = next_state(current)
            if current == OrderQueryState.RESOLVE_MODE:
                state = self.mode_node.execute(state)
            elif current == OrderQueryState.EXECUTE_MODE:
                if state.get("_order_query_mode") == OrderQueryMode.DETAIL:
                    state = self.detail_node.execute(state)
                else:
                    state = self.list_node.execute(state)
            elif current == OrderQueryState.CLEANUP:
                state.pop("_order_query_mode", None)
                state.pop("_order_query_order_no", None)

        return state
