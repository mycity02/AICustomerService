"""Topic advisor refinement node."""
from __future__ import annotations

from ...state import ConversationState

from .base_step_node import TopicAdvisorStepNode


class TopicAdvisorRefineNode(TopicAdvisorStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        self.service.prepare_refinement_response(state)
        return state
