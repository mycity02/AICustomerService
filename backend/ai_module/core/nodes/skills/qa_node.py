"""Compatibility wrapper for QA workflow.

Legacy imports may still reference ``QANode`` directly. The actual orchestration
now lives under ``workflows/qa_flow`` and uses dedicated nodes from
``nodes/qa_flow``.
"""
from __future__ import annotations

import sys
import types
from importlib import import_module
from pathlib import Path

try:
    from ai_module.core.nodes.common.base import BaseNode
    from ai_module.core.state import ConversationState
except Exception:  # pragma: no cover - compatibility path for isolated tests
    from backend.ai_module.core.nodes.common.base import BaseNode
    from backend.ai_module.core.state import ConversationState


def _ensure_package(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        sys.modules[name] = module
    if not hasattr(module, "__path__"):
        module.__path__ = [str(path)]


def _load_service_class():
    try:
        return import_module("ai_module.core.workflows.qa_flow.service").QAFlowService
    except Exception:
        core_dir = Path(__file__).resolve().parents[2]
        ai_dir = core_dir.parent
        workflows_dir = core_dir / "workflows"
        _ensure_package("backend.ai_module", ai_dir)
        _ensure_package("backend.ai_module.core", core_dir)
        _ensure_package("backend.ai_module.core.workflows", workflows_dir)
        _ensure_package("backend.ai_module.core.workflows.qa_flow", workflows_dir / "qa_flow")
        return import_module("backend.ai_module.core.workflows.qa_flow.service").QAFlowService


def _load_workflow_class():
    try:
        return import_module("ai_module.core.workflows.qa_flow.workflow").QAFlowWorkflow
    except Exception:
        return None


class QANode(BaseNode):
    """Backward-compatible facade delegating to QAFlowWorkflow."""

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)
        workflow_cls = _load_workflow_class()
        service_cls = _load_service_class()
        self.workflow = workflow_cls(llm, runtime=runtime) if workflow_cls is not None else None
        self.service = self.workflow.service if self.workflow is not None else service_cls(llm, runtime=runtime)

    def __getattr__(self, item: str):
        return getattr(self.service, item)

    def _prepare_messages(self, state: ConversationState):
        return self.service.prepare_messages(state)

    def execute(self, state: ConversationState) -> ConversationState:
        if self.workflow is not None:
            return self.workflow.execute(state)

        self.service.apply_quick_reply(state)
        return self.service.generate_response(state)

    def execute_stream(self, state: ConversationState):
        if self.workflow is not None:
            for token in self.workflow.execute_stream(state):
                yield token
            return

        for token in self.service.generate_response_stream(state):
            yield token
