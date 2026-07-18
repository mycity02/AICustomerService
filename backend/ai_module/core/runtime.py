"""
智能助手运行时与业务包装配层。

运行时负责把通用工作流骨架与业务差异配置连接起来，
例如工具、提示词、意图规则以及模型覆盖配置。

在骨架设计中：
- 工作流层维护稳定的内核执行顺序
- 运行时层负责把业务差异注入内核
- 插件与适配器也在这一层完成装配，避免内核感知当前业务包细节
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from adapters import EcommerceAdapter
from config import config_loader, init_chat_model, init_intent_model, settings
from ai_module.infrastructure.plugins import PluginManager, register_builtin_tool_plugins

from .constants import DEFAULT_INTENT_HANDLER_MAP, DEFAULT_INTENT_LABELS, DEFAULT_INTENT_RULES


@dataclass(frozen=True)
class ExecutionContext:
    """跨运行时边界传递的标准执行上下文。"""

    business_id: str
    business_name: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class BusinessPack:
    """业务配置包装器。

    业务包是业务差异的最小装配单元，可以在不分叉工作流内核的前提下，
    覆盖提示词、启用插件、意图标签和处理器映射。
    """

    def __init__(self, business_id: str, config: Dict[str, Any]):
        self.business_id = business_id
        self.config = config

    @property
    def business_name(self) -> str:
        return self.config.get("business_name", self.business_id)

    @property
    def business_type(self) -> str:
        return self.config.get("business_type", "")

    def get_llm_overrides(self) -> Dict[str, Any]:
        return dict(self.config.get("llm", {}))

    def get_prompt(self, prompt_name: str, default: Optional[str] = None) -> Optional[str]:
        return self.config.get("prompts", {}).get(prompt_name, default)

    def get_enabled_plugin_names(self, group: Optional[str] = None) -> Optional[List[str]]:
        plugin_configs = self.config.get("plugins", [])
        if not plugin_configs:
            return []

        names: List[str] = []
        for plugin in plugin_configs:
            if not plugin.get("enabled", True):
                continue

            groups = plugin.get("groups")
            if groups is None:
                legacy_group = plugin.get("group")
                groups = [legacy_group] if legacy_group else ["default"]

            if group and group not in groups:
                continue

            name = plugin.get("name")
            if name:
                names.append(name)

        return names

    def get_intent_labels(self) -> List[str]:
        classifier = self.config.get("intent_classifier", {})
        labels = list(classifier.get("labels") or [])
        merged: List[str] = []
        for label in labels + list(DEFAULT_INTENT_LABELS):
            if label not in merged:
                merged.append(label)
        return merged

    def get_intent_rules(self) -> Dict[str, List[str]]:
        classifier = self.config.get("intent_classifier", {})
        rules = classifier.get("rules") or {}
        merged: Dict[str, List[str]] = {
            intent: list(keywords)
            for intent, keywords in DEFAULT_INTENT_RULES.items()
        }
        for intent, keywords in rules.items():
            combined = list(merged.get(intent, []))
            for keyword in list(keywords):
                if keyword not in combined:
                    combined.append(keyword)
            merged[intent] = combined
        return merged

    def get_intent_examples(self) -> List[Dict[str, str]]:
        classifier = self.config.get("intent_classifier", {})
        return list(classifier.get("examples", []))

    def get_handler_for_intent(self, intent: Optional[str]) -> str:
        handler_overrides = self.config.get("intent_handlers", {})
        if intent in handler_overrides:
            return handler_overrides[intent]
        return DEFAULT_INTENT_HANDLER_MAP.get(intent, "clarify")

    def get_business_info(self) -> Dict[str, Any]:
        return {
            "business_id": self.business_id,
            "business_name": self.business_name,
            "business_type": self.business_type,
            "features": self.config.get("features", {}),
            "custom_intents": self.config.get("custom_intents", []),
            "plugins": self.config.get("plugins", []),
            "intent_handlers": self.config.get("intent_handlers", {}),
        }


class AIRuntime:
    """供工作流和节点使用的运行时对象。

    各节点应通过运行时获取模型、提示词和工具，而不是把业务知识直接写死。
    """

    def __init__(self, business_pack: BusinessPack, adapter: Any):
        self.business_pack = business_pack
        self.adapter = adapter
        self.plugin_manager = PluginManager()
        self.plugin_manager.set_adapter(adapter)
        register_builtin_tool_plugins(self.plugin_manager)
        self._model_cache: Dict[tuple[str, tuple[tuple[str, Any], ...]], Any] = {}

    def build_context(
        self,
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> ExecutionContext:
        return ExecutionContext(
            business_id=self.business_pack.business_id,
            business_name=self.business_pack.business_name,
            user_id=user_id,
            session_id=session_id,
            extra=extra or {},
        )

    def get_chat_model(self, role: str = "chat"):
        # 按角色和覆盖配置缓存模型实例，避免同一业务包的请求重复初始化模型。
        overrides = self.business_pack.get_llm_overrides()
        cache_key = (role, tuple(sorted(overrides.items())))
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        if role == "intent":
            model = init_intent_model(
                provider=overrides.get("provider"),
                model=overrides.get("intent_model") or overrides.get("model"),
                api_key=overrides.get("api_key"),
                base_url=overrides.get("base_url"),
            )
        else:
            model = init_chat_model(
                provider=overrides.get("provider"),
                model=overrides.get("model"),
                api_key=overrides.get("api_key"),
                base_url=overrides.get("base_url"),
                temperature=overrides.get("temperature"),
                max_tokens=overrides.get("max_tokens"),
            )

        self._model_cache[cache_key] = model
        return model

    def get_langchain_tools(
        self,
        group: str = "default",
        execution_context: Optional[dict] = None,
    ) -> List[Any]:
        # 通过工具分组，让同一业务包在不同节点暴露不同能力集合，
        # 例如默认路由使用一组工具，AI 选茶顾问使用另一组工具。
        names = self.business_pack.get_enabled_plugin_names(group=group)
        plugins = self.plugin_manager.get_plugins(names=names, group=group)
        return [
            plugin.to_langchain_tool(execution_context=execution_context)
            for plugin in plugins
            if hasattr(plugin, "to_langchain_tool")
        ]

    def list_plugins(self, group: Optional[str] = None) -> List[Dict[str, Any]]:
        names = self.business_pack.get_enabled_plugin_names(group=group)
        plugins = self.plugin_manager.get_plugins(names=names, group=group)
        return [plugin.get_metadata() for plugin in plugins]

    def get_handler_for_intent(self, intent: Optional[str]) -> str:
        return self.business_pack.get_handler_for_intent(intent)

    def get_business_info(self) -> Dict[str, Any]:
        return self.business_pack.get_business_info()

    def get_prompt(self, prompt_name: str, default: Optional[str] = None) -> Optional[str]:
        return self.business_pack.get_prompt(prompt_name, default)

    def get_intent_labels(self) -> List[str]:
        return self.business_pack.get_intent_labels()

    def get_intent_rules(self) -> Dict[str, List[str]]:
        return self.business_pack.get_intent_rules()

    def get_intent_examples(self) -> List[Dict[str, str]]:
        return self.business_pack.get_intent_examples()


class AIRuntimeFactory:
    """按业务包缓存运行时和工作流。

    这样可以复用“一套内核、多套业务包”的骨架设计：
    每个业务拥有独立的运行时与工作流对象，但不会在每次请求时重复构建。
    """

    def __init__(self):
        self._runtimes: Dict[str, AIRuntime] = {}
        self._workflows: Dict[str, Any] = {}

    def get_default_business_id(self) -> str:
        configured = getattr(settings, "DEFAULT_BUSINESS_ID", None)
        if configured:
            return configured

        businesses = config_loader.list_businesses()
        if businesses:
            return businesses[0]
        return "tea-retail"

    def _create_adapter(self, business_id: str, config: Dict[str, Any]):
        adapter_class_name = config.get("adapter", {}).get("class", "adapters.EcommerceAdapter")
        if adapter_class_name == "adapters.EcommerceAdapter":
            return EcommerceAdapter(business_id, config)
        return EcommerceAdapter(business_id, config)

    def get_runtime(self, business_id: Optional[str] = None) -> AIRuntime:
        resolved_business_id = business_id or self.get_default_business_id()
        if resolved_business_id in self._runtimes:
            return self._runtimes[resolved_business_id]

        config = config_loader.get_config(resolved_business_id)
        if not config:
            raise ValueError(f"Business pack not configured: {resolved_business_id}")

        runtime = AIRuntime(
            business_pack=BusinessPack(resolved_business_id, config),
            adapter=self._create_adapter(resolved_business_id, config),
        )
        self._runtimes[resolved_business_id] = runtime
        return runtime

    def get_workflow(self, business_id: Optional[str] = None):
        resolved_business_id = business_id or self.get_default_business_id()
        if resolved_business_id in self._workflows:
            return self._workflows[resolved_business_id]

        runtime = self.get_runtime(resolved_business_id)

        from .orchestration import AIWorkflow

        workflow = AIWorkflow(runtime=runtime)
        self._workflows[resolved_business_id] = workflow
        return workflow

    def clear(self, business_id: Optional[str] = None):
        if business_id is None:
            self._runtimes.clear()
            self._workflows.clear()
            return

        self._runtimes.pop(business_id, None)
        self._workflows.pop(business_id, None)


runtime_factory = AIRuntimeFactory()
