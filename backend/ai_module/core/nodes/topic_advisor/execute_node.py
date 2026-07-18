"""Topic advisor execution node."""
from __future__ import annotations

from typing import Iterator

from ...state import ConversationState

from .base_step_node import TopicAdvisorStepNode


class TopicAdvisorExecuteNode(TopicAdvisorStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        return self.service.run_agent(state)

    def execute_stream(self, state: ConversationState) -> Iterator[str]:
        for token in self.service.run_agent_stream(state):
            yield token
