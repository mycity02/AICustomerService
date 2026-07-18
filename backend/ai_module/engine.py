"""Unified AI module facade used by HTTP APIs and external callers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.loader import config_loader
from ai_module.application.ports import RuntimeFactoryPort, RuntimePort, WorkflowPort
from ai_module.infrastructure.adapters import runtime_factory_adapter


class AIEngine:
    """Single entrypoint for runtime/workflow access and business discovery."""

    def __init__(
        self,
        *,
        runtime_factory_instance: RuntimeFactoryPort = runtime_factory_adapter,
        config_loader_instance=config_loader,
    ):
        self._runtime_factory = runtime_factory_instance
        self._config_loader = config_loader_instance

    def get_workflow(self, business_id: Optional[str] = None) -> WorkflowPort:
        return self._runtime_factory.get_workflow(business_id)

    def get_runtime(self, business_id: Optional[str] = None) -> RuntimePort:
        return self._runtime_factory.get_runtime(business_id)

    def process_message(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        purchase_flow: Optional[Dict[str, Any]] = None,
        aftersales_flow: Optional[Dict[str, Any]] = None,
        business_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        workflow = self.get_workflow(business_id)
        return workflow.process_message(
            user_id=user_id,
            session_id=session_id,
            message=message,
            attachments=attachments,
            purchase_flow=purchase_flow,
            aftersales_flow=aftersales_flow,
        )

    def process_message_stream(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        purchase_flow: Optional[Dict[str, Any]] = None,
        aftersales_flow: Optional[Dict[str, Any]] = None,
        business_id: Optional[str] = None,
    ):
        workflow = self.get_workflow(business_id)
        for event in workflow.process_message_stream(
            user_id=user_id,
            session_id=session_id,
            message=message,
            attachments=attachments,
            purchase_flow=purchase_flow,
            aftersales_flow=aftersales_flow,
        ):
            yield event

    def list_businesses(self) -> List[Dict[str, Any]]:
        businesses: List[Dict[str, Any]] = []
        for business_id in self._config_loader.list_businesses():
            config = self._config_loader.get_config(business_id)
            if not config:
                continue

            businesses.append(
                {
                    "business_id": business_id,
                    "business_name": config.get("business_name", ""),
                    "business_type": config.get("business_type", ""),
                    "features": config.get("features", {}),
                }
            )
        return businesses

    def get_business_info(self, business_id: str) -> Dict[str, Any]:
        runtime = self.get_runtime(business_id)
        info = runtime.get_business_info()
        info["plugins"] = runtime.list_plugins()
        return info

    def list_plugins(self, *, business_id: Optional[str] = None, group: Optional[str] = None) -> Dict[str, Any]:
        runtime = self.get_runtime(business_id)
        return {
            "business_id": runtime.business_pack.business_id,
            "plugins": runtime.list_plugins(group=group),
        }


ai_engine = AIEngine()
