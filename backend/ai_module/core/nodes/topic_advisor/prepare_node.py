"""Topic advisor prepare node."""
from __future__ import annotations

from ...state import ConversationState

from .base_step_node import TopicAdvisorStepNode


class TopicAdvisorPrepareNode(TopicAdvisorStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        self.service.prepare_state(state)
        return state
