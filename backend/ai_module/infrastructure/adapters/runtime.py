"""Concrete adapters that satisfy the application ports."""
from __future__ import annotations

from typing import Any, Optional

from ...application.ports import RuntimePort, WorkflowPort
from ...core.runtime import AIRuntimeFactory, runtime_factory


class RuntimePortAdapter:
    """Thin adapter around AIRuntime for application-layer consumers."""

    def __init__(self, runtime):
        self._runtime = runtime

    def __getattr__(self, item: str) -> Any:
        return getattr(self._runtime, item)


class WorkflowPortAdapter:
    """Thin adapter around AIWorkflow for application-layer consumers."""

    def __init__(self, workflow):
        self._workflow = workflow

    def __getattr__(self, item: str) -> Any:
        return getattr(self._workflow, item)

    def process_message(self, **kwargs):
        return self._workflow.process_message(**kwargs)

    def process_message_stream(self, **kwargs):
        for event in self._workflow.process_message_stream(**kwargs):
            yield event


class RuntimeFactoryAdapter:
    """Adapter exposing AIRuntimeFactory behind explicit application ports."""

    def __init__(self, factory: AIRuntimeFactory):
        self._factory = factory

    def get_runtime(self, business_id: Optional[str] = None) -> RuntimePort:
        return RuntimePortAdapter(self._factory.get_runtime(business_id))

    def get_workflow(self, business_id: Optional[str] = None) -> WorkflowPort:
        return WorkflowPortAdapter(self._factory.get_workflow(business_id))

    def clear(self, business_id: Optional[str] = None) -> None:
        self._factory.clear(business_id)


runtime_factory_adapter = RuntimeFactoryAdapter(runtime_factory)
