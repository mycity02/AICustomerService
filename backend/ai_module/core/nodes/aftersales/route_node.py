"""Route step node for aftersales workflow."""
from __future__ import annotations

from typing import Dict

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState


class AftersalesRouteNode(BaseNode):
    """Resolve workflow step to a concrete step node key."""

    def __init__(self, step_to_node_key: Dict[str, str]):
        super().__init__()
        self.step_to_node_key = step_to_node_key

    def execute(self, state: ConversationState) -> ConversationState:
        step = state.get("_aftersales_step", "select_order")
        state["_aftersales_node_key"] = self.step_to_node_key.get(step)
        return state

__all__ = ["AftersalesRouteNode"]
