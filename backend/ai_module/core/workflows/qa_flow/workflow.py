"""QA workflow implementation."""
from __future__ import annotations

from typing import Iterator

from ...nodes.qa_flow import QAPrepareNode, QAQuickReplyNode, QARespondNode
from ...state import ConversationState
from ..base import BaseWorkflow
from .service import QAFlowService
from .state_machine import QAFlowState, next_state


class QAFlowWorkflow(BaseWorkflow):
    name = "qa_flow"
    stream_enabled = True

    def __init__(self, llm, runtime=None, service: QAFlowService | None = None):
        self.service = service or QAFlowService(llm, runtime=runtime)
        self.quick_reply_node = QAQuickReplyNode(self.service)
        self.prepare_node = QAPrepareNode(self.service)
        self.respond_node = QARespondNode(self.service)

    def execute(self, state: ConversationState) -> ConversationState:
        current = QAFlowState.START

        while current != QAFlowState.END:
            current = next_state(current)
            if current == QAFlowState.QUICK_REPLY:
                state = self.quick_reply_node.execute(state)
            elif current == QAFlowState.PREPARE:
                if state.get("_qa_quick_reply"):
                    continue
                state = self.prepare_node.execute(state)
            elif current == QAFlowState.RESPOND:
                state = self.respond_node.execute(state)

        state.pop("_qa_quick_reply", None)
        state.pop("_qa_messages", None)
        return state

    def execute_stream(self, state: ConversationState) -> Iterator[str]:
        current = QAFlowState.START

        while current != QAFlowState.END:
            current = next_state(current)
            if current == QAFlowState.QUICK_REPLY:
                state = self.quick_reply_node.execute(state)
            elif current == QAFlowState.PREPARE:
                if state.get("_qa_quick_reply"):
                    continue
                state = self.prepare_node.execute(state)
            elif current == QAFlowState.RESPOND:
                if state.get("_qa_quick_reply"):
                    yield state["response"]
                else:
                    for token in self.respond_node.execute_stream(state):
                        yield token

        state.pop("_qa_quick_reply", None)
        state.pop("_qa_messages", None)
