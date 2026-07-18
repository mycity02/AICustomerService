"""Compatibility wrapper for aftersales workflow.

Legacy imports may still reference ``AftersalesFlowNode`` directly. The actual
business logic now lives in dedicated step nodes under ``nodes/aftersales`` and
is orchestrated by ``workflows/aftersales_flow/workflow.py``.
"""
from __future__ import annotations

try:
    from ai_module.core.nodes.common.base import BaseNode
    from ai_module.core.state import ConversationState
    from ai_module.core.workflows.aftersales_flow.workflow import AftersalesFlowWorkflow
except Exception:  # pragma: no cover - compatibility path for isolated tests
    from backend.ai_module.core.nodes.common.base import BaseNode
    from backend.ai_module.core.state import ConversationState
    from backend.ai_module.core.workflows.aftersales_flow.workflow import AftersalesFlowWorkflow


class AftersalesFlowNode(BaseNode):
    """Backward-compatible facade delegating to AftersalesFlowWorkflow."""

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)
        self.workflow = AftersalesFlowWorkflow()

    def execute(self, state: ConversationState) -> ConversationState:
        return self.workflow.execute(state)
