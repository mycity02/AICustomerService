"""
Built-in tool plugins.

These wrappers let the runtime manage LangChain tools as first-class plugins
without forcing the business layer to depend directly on ``@tool``.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from .base import AIPlugin
from .manager import PluginManager
from services.function_tools import (
    all_tools,
    get_logistics,
    get_personalized_recommendations,
    get_user_info,
    query_order,
    topic_advisor_tools,
)


PLUGIN_ALIASES = {
    "query_order": {"query_orders"},
    "get_personalized_recommendations": {"recommend_products"},
}

ToolExecutor = Callable[[Optional[dict], "LangChainToolPlugin"], Any]


class CurrentUserInfoInput(BaseModel):
    """Use the authenticated user from the runtime context."""


class PersonalizedRecommendationsInput(BaseModel):
    limit: int = Field(default=5, ge=1, le=20, description="返回推荐商品数量")


def _context_value(execution_context: Optional[dict], key: str, default: Any = None) -> Any:
    if execution_context is None:
        return default
    if isinstance(execution_context, dict):
        return execution_context.get(key, default)
    return getattr(execution_context, key, default)


def _resolve_scoped_user_id(
    execution_context: Optional[dict],
    explicit_user_id: Optional[str] = None,
    *,
    required: bool = False,
) -> Optional[str]:
    context_user_id = _context_value(execution_context, "user_id")

    if explicit_user_id and context_user_id and explicit_user_id != context_user_id:
        raise PermissionError("tool user_id does not match the authenticated execution context")

    resolved_user_id = explicit_user_id or context_user_id
    if required and not resolved_user_id:
        raise PermissionError("this tool requires an authenticated user context")
    return resolved_user_id


class LangChainToolPlugin(AIPlugin):
    """Wrap a LangChain tool in the project plugin contract."""

    def __init__(
        self,
        tool,
        *,
        aliases: Iterable[str] | None = None,
        groups: Iterable[str] | None = None,
        adapter=None,
        args_schema=None,
        description: Optional[str] = None,
        executor: Optional[Callable[..., Any]] = None,
    ):
        super().__init__(adapter=adapter)
        self._tool = tool
        self.aliases = set(aliases or ())
        self.groups = set(groups or ("default",))
        self._args_schema = args_schema or getattr(tool, "args_schema", None)
        self._description = description or getattr(tool, "description", "") or ""
        self._executor = executor

    @property
    def name(self) -> str:
        return self._tool.name

    @property
    def description(self) -> str:
        return self._description

    def matches(self, plugin_name: str) -> bool:
        return plugin_name == self.name or plugin_name in self.aliases

    def supports_group(self, group: str) -> bool:
        return group in self.groups

    def get_schema(self) -> dict:
        args_schema = self._args_schema
        if args_schema is None:
            return super().get_schema()
        if hasattr(args_schema, "model_json_schema"):
            return args_schema.model_json_schema()
        if hasattr(args_schema, "schema"):
            return args_schema.schema()
        return super().get_schema()

    def execute(self, execution_context: Optional[dict] = None, **kwargs):
        if self._executor is not None:
            return self._executor(
                execution_context=execution_context,
                plugin=self,
                **kwargs,
            )
        return self._tool.invoke(kwargs)

    def to_langchain_tool(self, execution_context: Optional[dict] = None):
        def _bound_executor(**kwargs):
            return self.execute(execution_context=execution_context, **kwargs)

        return StructuredTool.from_function(
            func=_bound_executor,
            name=self.name,
            description=self.description,
            args_schema=self._args_schema,
        )

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata.update(
            {
                "plugin_type": "tool",
                "aliases": sorted(self.aliases),
                "groups": sorted(self.groups),
            }
        )
        return metadata


def _execute_query_order(
    *,
    execution_context: Optional[dict],
    plugin: LangChainToolPlugin,
    order_no: str,
):
    user_id = _resolve_scoped_user_id(execution_context, required=True)

    if plugin.adapter and hasattr(plugin.adapter, "get_order_by_no"):
        order = plugin.adapter.get_order_by_no(order_no, user_id=user_id)
    else:
        from database.connection import get_db_context
        from services.order_service import OrderService

        with get_db_context() as db:
            order = OrderService(db).get_order_by_no(order_no, user_id=user_id)

    if not order:
        return {
            "success": False,
            "error": "订单不存在或无权访问",
            "order_no": order_no,
        }

    return {
        "success": True,
        "order_no": order["order_no"],
        "status": order["status"],
        "total_amount": float(order["total_amount"]),
        "created_at": str(order["created_at"]),
        "items": order.get("items", []),
        "buyer_name": order.get("buyer_name", ""),
        "buyer_phone": order.get("buyer_phone", ""),
    }


def _execute_get_logistics(
    *,
    execution_context: Optional[dict],
    plugin: LangChainToolPlugin,
    order_no: str,
):
    query_result = _execute_query_order(
        execution_context=execution_context,
        plugin=plugin,
        order_no=order_no,
    )
    if not query_result.get("success"):
        return query_result

    status = query_result["status"]
    if status == "delivered":
        return {
            "success": True,
            "order_no": order_no,
            "delivery_type": "physical",
            "message": "茶品订单已签收，如商品或包装有问题请及时申请售后。",
            "status": "已签收",
        }
    if status == "paid":
        return {
            "success": True,
            "order_no": order_no,
            "delivery_type": "physical",
            "message": "订单已支付，茶坊正在备货并安排发货。",
            "status": "备货中",
        }
    return {
        "success": True,
        "order_no": order_no,
        "delivery_type": "physical",
        "message": f"订单状态：{status}",
        "status": status,
    }


def _execute_get_user_info(
    *,
    execution_context: Optional[dict],
    plugin: LangChainToolPlugin,
):
    user_id = _resolve_scoped_user_id(execution_context, required=True)

    if plugin.adapter and hasattr(plugin.adapter, "get_user_info"):
        user = plugin.adapter.get_user_info(user_id)
    else:
        from database.connection import get_db_context
        from database.models import User
        from sqlalchemy import select

        with get_db_context() as db:
            result = db.execute(select(User).where(User.id == user_id))
            db_user = result.scalar_one_or_none()
            user = None
            if db_user:
                user = {
                    "user_id": db_user.id,
                    "username": db_user.username,
                    "email": db_user.email,
                    "role": getattr(db_user.role, "value", db_user.role),
                    "created_at": str(db_user.created_at),
                }

    if not user:
        return {"success": False, "error": "用户不存在"}

    return {
        "success": True,
        "user_id": user.get("user_id") or user.get("id"),
        "username": user.get("username", ""),
        "email": user.get("email", ""),
        "role": user.get("role", ""),
        "created_at": str(user.get("created_at", "")),
    }


def _execute_get_personalized_recommendations(
    *,
    execution_context: Optional[dict],
    plugin: LangChainToolPlugin,
    limit: int = 5,
):
    user_id = _resolve_scoped_user_id(execution_context, required=True)

    if plugin.adapter and hasattr(plugin.adapter, "get_personalized_recommendations"):
        recommendations = plugin.adapter.get_personalized_recommendations(user_id, limit=limit)
    else:
        from database.connection import get_db_context
        from services.recommendation_service import RecommendationService

        with get_db_context() as db:
            rec_service = RecommendationService(db)
            recommendations = rec_service.get_personalized_recommendations(
                user_id=user_id,
                limit=limit,
            )

    if not recommendations:
        return {
            "success": True,
            "message": "暂无个性化推荐结果",
            "products": [],
            "is_personalized": False,
        }

    return {
        "success": True,
        "message": "为您推荐以下商品",
        "products": recommendations,
        "is_personalized": True,
    }


def _build_specialized_plugins() -> dict[str, LangChainToolPlugin]:
    return {
        query_order.name: LangChainToolPlugin(
            query_order,
            description="查询当前登录用户的订单详情和状态。",
            executor=_execute_query_order,
        ),
        get_logistics.name: LangChainToolPlugin(
            get_logistics,
            description="查询当前登录用户茶叶订单的备货、配送或签收状态。",
            executor=_execute_get_logistics,
        ),
        get_user_info.name: LangChainToolPlugin(
            get_user_info,
            args_schema=CurrentUserInfoInput,
            description="获取当前登录用户的基本信息。",
            executor=_execute_get_user_info,
        ),
        get_personalized_recommendations.name: LangChainToolPlugin(
            get_personalized_recommendations,
            args_schema=PersonalizedRecommendationsInput,
            description="基于当前登录用户的浏览历史获取个性化推荐。",
            executor=_execute_get_personalized_recommendations,
        ),
    }


def register_builtin_tool_plugins(manager: PluginManager) -> PluginManager:
    """Register the built-in tool catalogue once for a runtime."""
    catalogue: dict[str, dict] = {}

    def _upsert(tool, group: str):
        entry = catalogue.setdefault(
            tool.name,
            {
                "tool": tool,
                "groups": set(),
                "aliases": set(PLUGIN_ALIASES.get(tool.name, set())),
            },
        )
        entry["groups"].add(group)

    for tool in all_tools:
        _upsert(tool, "default")

    for tool in topic_advisor_tools:
        _upsert(tool, "topic_advisor")

    specialized_plugins = _build_specialized_plugins()

    for tool_name, entry in catalogue.items():
        plugin = specialized_plugins.get(tool_name)
        if plugin is None:
            plugin = LangChainToolPlugin(entry["tool"])

        plugin.aliases.update(entry["aliases"])
        plugin.groups.update(entry["groups"])
        manager.register(plugin)

    return manager
