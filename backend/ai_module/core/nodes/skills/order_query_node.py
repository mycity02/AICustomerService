"""Compatibility wrapper for order query workflow.

Legacy imports may still reference ``OrderQueryNode`` directly. The actual
orchestration now lives under ``workflows/order_query`` and uses dedicated
nodes from ``nodes/order_query``.
"""
from __future__ import annotations

try:
    from ai_module.core.nodes.common.base import BaseNode
    from ai_module.core.state import ConversationState
    from ai_module.core.workflows.order_query.workflow import OrderQueryWorkflow
except Exception:  # pragma: no cover - compatibility path for isolated tests
    from backend.ai_module.core.nodes.common.base import BaseNode
    from backend.ai_module.core.state import ConversationState
    from backend.ai_module.core.workflows.order_query.workflow import OrderQueryWorkflow


class OrderQueryNode(BaseNode):
    """Backward-compatible facade delegating to OrderQueryWorkflow."""

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)
        self.workflow = OrderQueryWorkflow()
        self.service = self.workflow.service

    def __getattr__(self, item: str):
        return getattr(self.service, item)

    def execute(self, state: ConversationState) -> ConversationState:
        return self.workflow.execute(state)
