"""Compatibility wrapper for purchase flow workflow.

Legacy imports may still reference ``PurchaseFlowNode`` directly. The actual
business logic now lives in dedicated step nodes under ``nodes/purchase_flow``
and is orchestrated by ``workflows/purchase_flow/workflow.py``.
"""
from __future__ import annotations

try:
    from ai_module.core.nodes.common.base import BaseNode
    from ai_module.core.state import ConversationState
    from ai_module.core.workflows.purchase_flow.workflow import PurchaseFlowWorkflow
except Exception:  # pragma: no cover - compatibility path for isolated tests
    from backend.ai_module.core.nodes.common.base import BaseNode
    from backend.ai_module.core.state import ConversationState
    from backend.ai_module.core.workflows.purchase_flow.workflow import PurchaseFlowWorkflow


class PurchaseFlowNode(BaseNode):
    """Backward-compatible facade delegating to PurchaseFlowWorkflow."""

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)
        self.workflow = PurchaseFlowWorkflow()

    def execute(self, state: ConversationState) -> ConversationState:
        return self.workflow.execute(state)
