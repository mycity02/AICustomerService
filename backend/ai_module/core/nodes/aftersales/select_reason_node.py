"""Select-reason step node for aftersales workflow."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState
from ai_module.core.nodes.aftersales.constants import REASON_OPTIONS, TYPE_LABELS


class AftersalesSelectReasonNode(BaseNode):
    """Step 3: choose reason."""

    def execute(self, state: ConversationState) -> ConversationState:
        flow_data = state.get("aftersales_flow") or {}
        refund_type = flow_data.get("refund_type", "refund_only")
        type_label = TYPE_LABELS.get(refund_type, "售后")
        reasons = REASON_OPTIONS.get(refund_type, REASON_OPTIONS["refund_only"])

        state["aftersales_flow"] = {**flow_data, "step": "select_reason"}

        buttons = []
        for reason_key, reason_label in reasons:
            buttons.append(
                {
                    "type": "button",
                    "label": reason_label,
                    "action": "aftersales_flow",
                    "data": {**flow_data, "step": "input_description", "reason": reason_key},
                    "icon": "📝",
                }
            )

        state["response"] = f"您选择了「{type_label}」，请选择原因："
        state["quick_actions"] = buttons
        return state

__all__ = ["AftersalesSelectReasonNode"]
