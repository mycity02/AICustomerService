"""Runtime and workflow application ports."""
from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Protocol

from .plugins import PluginManagerPort


class RuntimePort(Protocol):
    business_pack: Any
    adapter: Any
    plugin_manager: PluginManagerPort

    def build_context(
        self,
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Any: ...

    def get_chat_model(self, role: str = "chat") -> Any: ...

    def get_langchain_tools(
        self,
        group: str = "default",
        execution_context: Optional[dict] = None,
    ) -> List[Any]: ...

    def list_plugins(self, group: Optional[str] = None) -> List[Dict[str, Any]]: ...

    def get_handler_for_intent(self, intent: Optional[str]) -> str: ...

    def get_business_info(self) -> Dict[str, Any]: ...

    def get_prompt(self, prompt_name: str, default: Optional[str] = None) -> Optional[str]: ...

    def get_intent_labels(self) -> List[str]: ...

    def get_intent_rules(self) -> Dict[str, List[str]]: ...

    def get_intent_examples(self) -> List[Dict[str, str]]: ...


class WorkflowPort(Protocol):
    def process_message(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        purchase_flow: Optional[Dict[str, Any]] = None,
        aftersales_flow: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]: ...

    def process_message_stream(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        purchase_flow: Optional[Dict[str, Any]] = None,
        aftersales_flow: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]: ...


class RuntimeFactoryPort(Protocol):
    def get_runtime(self, business_id: Optional[str] = None) -> RuntimePort: ...

    def get_workflow(self, business_id: Optional[str] = None) -> WorkflowPort: ...

    def clear(self, business_id: Optional[str] = None) -> None: ...
