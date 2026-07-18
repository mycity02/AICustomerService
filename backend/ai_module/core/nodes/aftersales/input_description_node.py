"""Input-description step node for aftersales workflow."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState
from ai_module.core.nodes.aftersales.constants import REASON_LABELS


class AftersalesInputDescriptionNode(BaseNode):
    """Step 4: input optional description."""

    def execute(self, state: ConversationState) -> ConversationState:
        flow_data = state.get("aftersales_flow") or {}
        reason = flow_data.get("reason", "other")
        reason_label = REASON_LABELS.get(reason, "其他")

        user_msg = state.get("user_message", "").strip()
        has_description = user_msg and not user_msg.startswith("[售后流程]")

        if has_description:
            flow_data["description"] = user_msg
            flow_data["step"] = "confirm"
            state["aftersales_flow"] = flow_data
            return state

        state["aftersales_flow"] = {**flow_data, "step": "input_description"}
        state["response"] = f"原因：{reason_label}\n\n您可以补充描述问题详情（直接输入文字发送），或跳过直接提交："
        state["quick_actions"] = [
            {
                "type": "button",
                "label": "跳过，直接确认",
                "action": "aftersales_flow",
                "data": {**flow_data, "step": "confirm", "description": None},
                "icon": "⏭️",
            },
        ]
        return state

__all__ = ["AftersalesInputDescriptionNode"]
