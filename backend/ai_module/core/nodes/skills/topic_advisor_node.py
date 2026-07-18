"""Compatibility wrapper for topic advisor workflow.

Legacy imports may still reference ``TopicAdvisorNode`` directly. The actual
workflow orchestration now lives under ``workflows/topic_advisor`` and uses
dedicated nodes from ``nodes/topic_advisor``.
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


def _load_service_and_mode():
    try:
        service_mod = import_module("ai_module.core.workflows.topic_advisor.service")
        contracts_mod = import_module("ai_module.core.workflows.topic_advisor.contracts")
    except Exception:
        core_dir = Path(__file__).resolve().parents[2]
        ai_dir = core_dir.parent
        workflows_dir = core_dir / "workflows"
        _ensure_package("backend.ai_module", ai_dir)
        _ensure_package("backend.ai_module.core", core_dir)
        _ensure_package("backend.ai_module.core.workflows", workflows_dir)
        _ensure_package("backend.ai_module.core.workflows.topic_advisor", workflows_dir / "topic_advisor")
        service_mod = import_module("backend.ai_module.core.workflows.topic_advisor.service")
        contracts_mod = import_module("backend.ai_module.core.workflows.topic_advisor.contracts")
    return service_mod.TopicAdvisorService, contracts_mod.TopicAdvisorMode


def _load_workflow_class():
    try:
        return import_module("ai_module.core.workflows.topic_advisor.workflow").TopicAdvisorWorkflow
    except Exception:
        return None


class TopicAdvisorNode(BaseNode):
    """Backward-compatible facade delegating to TopicAdvisorWorkflow."""

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)
        service_cls, mode_enum = _load_service_and_mode()
        workflow_cls = _load_workflow_class()
        self.workflow = workflow_cls(llm, runtime=runtime) if workflow_cls is not None else None
        self.service = self.workflow.service if self.workflow is not None else service_cls(llm, runtime=runtime)
        self.mode_enum = mode_enum

    def execute(self, state: ConversationState) -> ConversationState:
        if self.workflow is not None:
            return self.workflow.execute(state)

        self.service.prepare_state(state)
        mode = self.service.resolve_mode(state)
        if mode == self.mode_enum.REFINE_PREFERENCES:
            self.service.prepare_refinement_response(state)
            return state
        return self.service.run_agent(state)

    def execute_stream(self, state: ConversationState):
        if self.workflow is not None:
            for token in self.workflow.execute_stream(state):
                yield token
            return

        self.service.prepare_state(state)
        mode = self.service.resolve_mode(state)
        if mode == self.mode_enum.REFINE_PREFERENCES:
            self.service.prepare_refinement_response(state)
            if state.get("response"):
                yield state["response"]
            return

        for token in self.service.run_agent_stream(state):
            yield token
