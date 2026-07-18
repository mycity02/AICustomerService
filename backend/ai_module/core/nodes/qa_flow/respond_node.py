"""QA response node."""
from __future__ import annotations

from ...state import ConversationState

from .base_step_node import QAFlowStepNode


class QARespondNode(QAFlowStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        return self.service.generate_response(state)

    def execute_stream(self, state: ConversationState):
        for token in self.service.generate_response_stream(state):
            yield token
