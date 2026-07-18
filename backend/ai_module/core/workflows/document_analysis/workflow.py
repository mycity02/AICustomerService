"""Document analysis workflow implementation."""
from __future__ import annotations

from typing import Iterator

from ...nodes.document_analysis import DocumentExtractNode, DocumentRespondNode
from ...state import ConversationState
from ..base import BaseWorkflow
from .service import DocumentAnalysisService
from .state_machine import DocumentAnalysisState, next_state


class DocumentAnalysisWorkflow(BaseWorkflow):
    name = "document_analysis"
    stream_enabled = True

    def __init__(self, llm, runtime=None, service: DocumentAnalysisService | None = None):
        self.service = service or DocumentAnalysisService(llm, runtime=runtime)
        self.extract_node = DocumentExtractNode(self.service)
        self.respond_node = DocumentRespondNode(self.service)

    def execute(self, state: ConversationState) -> ConversationState:
        current = DocumentAnalysisState.START

        while current != DocumentAnalysisState.END:
            current = next_state(current)
            if current == DocumentAnalysisState.EXTRACT:
                state = self.extract_node.execute(state)
            elif current == DocumentAnalysisState.RESPOND:
                state = self.respond_node.execute(state)

        self._cleanup(state)
        return state

    def execute_stream(self, state: ConversationState) -> Iterator[str]:
        current = DocumentAnalysisState.START

        while current != DocumentAnalysisState.END:
            current = next_state(current)
            if current == DocumentAnalysisState.EXTRACT:
                state = self.extract_node.execute(state)
            elif current == DocumentAnalysisState.RESPOND:
                for token in self.respond_node.execute_stream(state):
                    yield token

        self._cleanup(state)

    def _cleanup(self, state: ConversationState) -> None:
        state.pop("_document_attachment_texts", None)
        state.pop("_document_attachment_names", None)
        state.pop("_document_image_context", None)
