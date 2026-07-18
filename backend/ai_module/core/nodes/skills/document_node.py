"""Compatibility wrapper for document analysis workflow.

Legacy imports may still reference ``DocumentNode`` directly. The actual
orchestration now lives under ``workflows/document_analysis`` and uses
dedicated nodes from ``nodes/document_analysis``.
"""
from __future__ import annotations

try:
    from ai_module.core.nodes.common.base import BaseNode
    from ai_module.core.state import ConversationState
    from ai_module.core.workflows.document_analysis.workflow import DocumentAnalysisWorkflow
except Exception:  # pragma: no cover - compatibility path for isolated tests
    from backend.ai_module.core.nodes.common.base import BaseNode
    from backend.ai_module.core.state import ConversationState
    from backend.ai_module.core.workflows.document_analysis.workflow import DocumentAnalysisWorkflow


class DocumentNode(BaseNode):
    """Backward-compatible facade delegating to DocumentAnalysisWorkflow."""

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)
        self.workflow = DocumentAnalysisWorkflow(llm, runtime=runtime)
        self.service = self.workflow.service

    def __getattr__(self, item: str):
        return getattr(self.service, item)

    def execute(self, state: ConversationState) -> ConversationState:
        return self.workflow.execute(state)

    def execute_stream(self, state: ConversationState):
        for token in self.workflow.execute_stream(state):
            yield token
