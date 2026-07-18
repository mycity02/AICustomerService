"""QA quick reply node."""
from __future__ import annotations

from ...state import ConversationState

from .base_step_node import QAFlowStepNode


class QAQuickReplyNode(QAFlowStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        self.service.apply_quick_reply(state)
        return state
