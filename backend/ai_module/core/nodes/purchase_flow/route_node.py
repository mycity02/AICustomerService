"""Purchase flow route node."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState


class PurchaseRouteNode(BaseNode):
    """Resolve purchase flow step to a concrete node key."""

    def __init__(self, step_to_node_key: dict[str, str]):
        super().__init__()
        self.step_to_node_key = step_to_node_key

    def execute(self, state: ConversationState) -> ConversationState:
        flow = state.get("purchase_flow") or {}
        step = flow.get("step")
        state["_purchase_flow_step"] = step
        state["_purchase_flow_node_key"] = self.step_to_node_key.get(step)
        return state
