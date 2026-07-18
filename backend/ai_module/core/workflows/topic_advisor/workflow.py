"""Topic advisor workflow implementation."""
from __future__ import annotations

from typing import Iterator

from ...nodes.topic_advisor import (
    TopicAdvisorExecuteNode,
    TopicAdvisorModeNode,
    TopicAdvisorPrepareNode,
)
from ...state import ConversationState
from ..base import BaseWorkflow
from .contracts import TopicAdvisorMode
from .service import TopicAdvisorService
from .state_machine import TopicAdvisorState, next_state
from .steps import build_mode_nodes, cleanup_runtime_keys


class TopicAdvisorWorkflow(BaseWorkflow):
    name = "topic_advisor"
    stream_enabled = True

    def __init__(self, llm, runtime=None, service: TopicAdvisorService | None = None):
        self.service = service or TopicAdvisorService(llm, runtime=runtime)
        self.prepare_node = TopicAdvisorPrepareNode(self.service)
        self.mode_node = TopicAdvisorModeNode(self.service)
        self.mode_nodes = build_mode_nodes(self.service)
        self.execute_node = self.mode_nodes[TopicAdvisorMode.DIRECT_RECOMMEND]

    def execute(self, state: ConversationState) -> ConversationState:
        current = TopicAdvisorState.START

        while current != TopicAdvisorState.END:
            current = next_state(current)
            if current == TopicAdvisorState.PREPARE:
                state = self.prepare_node.execute(state)
            elif current == TopicAdvisorState.RESOLVE_MODE:
                state = self.mode_node.execute(state)
            elif current == TopicAdvisorState.EXECUTE_MODE:
                mode = state.get("_topic_advisor_mode", TopicAdvisorMode.DIRECT_RECOMMEND)
                state = self.mode_nodes[mode].execute(state)
            elif current == TopicAdvisorState.CLEANUP:
                state = cleanup_runtime_keys(state)

        return state

    def execute_stream(self, state: ConversationState) -> Iterator[str]:
        current = TopicAdvisorState.START

        while current != TopicAdvisorState.END:
            current = next_state(current)
            if current == TopicAdvisorState.PREPARE:
                state = self.prepare_node.execute(state)
            elif current == TopicAdvisorState.RESOLVE_MODE:
                state = self.mode_node.execute(state)
            elif current == TopicAdvisorState.EXECUTE_MODE:
                mode = state.get("_topic_advisor_mode", TopicAdvisorMode.DIRECT_RECOMMEND)
                if mode == TopicAdvisorMode.REFINE_PREFERENCES:
                    state = self.mode_nodes[mode].execute(state)
                    if state.get("response"):
                        yield state["response"]
                else:
                    for token in self.execute_node.execute_stream(state):
                        yield token
            elif current == TopicAdvisorState.CLEANUP:
                state = cleanup_runtime_keys(state)
