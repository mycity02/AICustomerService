"""Topic advisor mode resolution node."""
from __future__ import annotations

from ...state import ConversationState

from .base_step_node import TopicAdvisorStepNode


class TopicAdvisorModeNode(TopicAdvisorStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        state["_topic_advisor_mode"] = self.service.resolve_mode(state)
        return state
