"""Validate step node for aftersales workflow."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState


class AftersalesValidateNode(BaseNode):
    """Ensure flow payload is present and contains a valid step key."""

    def __init__(self, default_step: str = "select_order"):
        super().__init__()
        self.default_step = default_step

    def execute(self, state: ConversationState) -> ConversationState:
        flow = state.get("aftersales_flow") or {}
        step = flow.get("step") or self.default_step
        state["aftersales_flow"] = {**flow, "step": step}
        state["_aftersales_step"] = step
        return state

__all__ = ["AftersalesValidateNode"]
