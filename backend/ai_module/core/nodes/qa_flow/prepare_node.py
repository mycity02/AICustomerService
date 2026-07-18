"""QA prepare node."""
from __future__ import annotations

from ...state import ConversationState

from .base_step_node import QAFlowStepNode


class QAPrepareNode(QAFlowStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        self.service.prepare_messages(state)
        return state
