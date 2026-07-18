"""Document extraction node."""
from __future__ import annotations

from ...state import ConversationState

from .base_step_node import DocumentAnalysisStepNode


class DocumentExtractNode(DocumentAnalysisStepNode):
    def execute(self, state: ConversationState) -> ConversationState:
        self.service.prepare_attachments(state)
        return state
