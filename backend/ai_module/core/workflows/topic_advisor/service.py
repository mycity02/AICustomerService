"""Topic advisor service helpers."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from ai_module.core.tea_preferences import (
    build_preference_search_keyword,
    has_tea_preference_slots,
)

from services.function_tools import topic_advisor_tools

from ...constants import DIALOGUE_ACT_REJECT, INTENT_RECOMMEND
from ...state import ConversationState
from .contracts import TopicAdvisorMode

logger = logging.getLogger(__name__)

MAX_AGENT_ITERATIONS = 5

DEFAULT_SYSTEM_PROMPT = """你是云岫茶坊的 AI 选茶顾问。
你的目标是根据饮用场景、预算、茶类、香型和口感偏好推荐合适茶品。

工具名保持兼容，其业务含义如下：
- search_projects: 搜索茶叶商品
- get_project_detail: 查看单款茶叶详情
- compare_projects: 对比多款茶叶
- check_tech_stack_match: 匹配风味偏好
- get_personalized_recommendations: 基于浏览历史推荐茶品

规则：
1. 简单需求直接给结果，不要过度调用工具。
2. 信息不足时询问自饮或送礼、预算、香型与口感浓淡。
3. 最终回复简洁，说明推荐理由和冲泡建议。
4. 不宣传无法验证的保健或治疗功效。"""


class TopicAdvisorService:
    """Operational logic behind the topic advisor workflow."""

    def __init__(self, llm=None, runtime=None):
        self.llm = llm
        self.runtime = runtime
        self.tools = []
        self.tool_map = {}
        self.llm_with_tools = None
        self._refresh_tools()

    def prepare_state(self, state: ConversationState) -> None:
        state.setdefault("topic_advisor_projects", [])
        state.setdefault("topic_advisor_tool_results", [])

    def _refresh_tools(self, execution_context=None):
        tools = []
        if self.runtime is not None:
            tools = self.runtime.get_langchain_tools(
                "topic_advisor",
                execution_context=execution_context,
            )
        if not tools:
            tools = list(topic_advisor_tools)

        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools) if self.llm and self.tools else None

    def _build_history_str(self, history: List[Dict[str, Any]]) -> str:
        if not history:
            return "无"
        return "\n".join(
            f"用户: {turn.get('user', '')}\n助手: {turn.get('assistant', '')}"
            for turn in history[-5:]
        )

    def _get_system_prompt(self) -> str:
        if self.runtime is None:
            return DEFAULT_SYSTEM_PROMPT
        return self.runtime.get_prompt("topic_advisor_system_prompt", DEFAULT_SYSTEM_PROMPT)

    def _build_messages(self, state: ConversationState) -> List[Any]:
        history_str = self._build_history_str(state.get("conversation_history", []))
        user_id = state.get("user_id", "")
        business_id = state.get("business_id") or "default"
        business_name = business_id
        execution_context = state.get("execution_context") or {}
        if isinstance(execution_context, dict):
            business_name = execution_context.get("business_name", business_name)

        slot_updates = state.get("slot_updates") or {}
        reference_resolution = state.get("reference_resolution") or {}
        active_task = state.get("active_task") or {}
        task_stack = state.get("task_stack") or []
        dialogue_context = (
            f"入口分类器: {state.get('entry_classifier') or 'unknown'}\n"
            f"流程内分类: {state.get('inflow_type') or 'none'}\n"
            f"当前步骤: {state.get('current_step') or 'none'}\n"
            f"本轮对话动作: {state.get('dialogue_act') or 'unknown'}\n"
            f"是否延续上一轮任务: {'是' if state.get('continue_previous_task') else '否'}\n"
            f"补充条件: {json.dumps(slot_updates, ensure_ascii=False)}\n"
            f"引用解析: {json.dumps(reference_resolution, ensure_ascii=False)}\n"
            f"当前任务: {json.dumps(active_task, ensure_ascii=False)}\n"
            f"挂起任务数量: {len(task_stack)}\n"
        )

        return [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(
                content=(
                    f"业务包: {business_id}\n"
                    f"业务名称: {business_name}\n"
                    f"用户ID: {user_id}\n"
                    f"历史对话:\n{history_str}\n\n"
                    f"{dialogue_context}"
                    f"用户最新消息: {state.get('user_message', '')}"
                )
            ),
        ]

    def _get_recommended_product_actions(self, state: ConversationState) -> List[Dict[str, Any]]:
        return [
            action
            for action in (state.get("last_quick_actions") or [])
            if action.get("type") == "product"
        ]

    def resolve_mode(self, state: ConversationState) -> TopicAdvisorMode:
        active_task = state.get("active_task") or {}
        active_intent = state.get("intent") or active_task.get("intent") or state.get("last_intent")
        if active_intent != INTENT_RECOMMEND:
            return TopicAdvisorMode.DIRECT_RECOMMEND
        if state.get("dialogue_act") != DIALOGUE_ACT_REJECT:
            return TopicAdvisorMode.DIRECT_RECOMMEND
        if state.get("slot_updates"):
            return TopicAdvisorMode.DIRECT_RECOMMEND
        if self._get_recommended_product_actions(state):
            return TopicAdvisorMode.REFINE_PREFERENCES
        if (active_task.get("slots") or {}).get("rejected_product_ids"):
            return TopicAdvisorMode.REFINE_PREFERENCES
        return TopicAdvisorMode.DIRECT_RECOMMEND

    def _remember_rejected_products(self, state: ConversationState) -> None:
        active_task = state.get("active_task") or {}
        if not active_task:
            return

        product_ids = [
            action.get("data", {}).get("product_id")
            for action in self._get_recommended_product_actions(state)
            if action.get("data", {}).get("product_id") is not None
        ]
        if not product_ids:
            return

        slots = dict(active_task.get("slots", {}))
        existing = list(slots.get("rejected_product_ids") or [])
        slots["rejected_product_ids"] = list(dict.fromkeys(existing + product_ids))
        active_task["slots"] = slots
        state["active_task"] = active_task

    def _build_refinement_quick_actions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "button",
                "label": "换清淡一点",
                "action": "send_question",
                "data": {"question": "换一款口感清淡鲜爽的茶"},
                "icon": "lightbulb",
            },
            {
                "type": "button",
                "label": "换便宜一点",
                "action": "send_question",
                "data": {"question": "换便宜一点的，预算再低一点"},
                "icon": "wallet",
            },
            {
                "type": "button",
                "label": "换个香型",
                "action": "send_question",
                "data": {"question": "换个香型，我不太喜欢这一类香气"},
                "icon": "cpu",
            },
            {
                "type": "button",
                "label": "换个茶类",
                "action": "send_question",
                "data": {"question": "换个茶类，不要这一类茶"},
                "icon": "grid",
            },
        ]

    def prepare_refinement_response(self, state: ConversationState) -> None:
        self._remember_rejected_products(state)
        state["topic_advisor_projects"] = []
        state["response"] = (
            "明白了，这一批都不太合适。我先不继续盲目重推。"
            "您更想调整哪一块：茶类、香型、口感浓淡还是预算？"
            "也可以直接告诉我，比如“换成乌龙茶”“想要花香”“清淡一点”或“300 元以内”。"
        )
        state["quick_actions"] = self._build_refinement_quick_actions()
        state["topic_advisor_tool_results"] = []

    def _run_agent_loop_stream(self, messages: list):
        tool_call_log = []

        for iteration in range(MAX_AGENT_ITERATIONS):
            logger.info("Topic advisor iteration=%s", iteration + 1)
            response = self.llm_with_tools.invoke(messages)

            if not response.tool_calls:
                for char in response.content:
                    yield {"type": "token", "content": char}
                yield {"type": "done", "tool_call_log": tool_call_log}
                return

            messages.append(response)
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call.get("id", f"call_{iteration}_{tool_name}")

                yield {"type": "status", "message": self._get_tool_description(tool_name, tool_args)}

                try:
                    tool = self.tool_map.get(tool_name)
                    result = tool.invoke(tool_args) if tool else {"error": f"未知工具: {tool_name}"}
                except Exception as exc:
                    logger.error("Topic advisor tool failed: %s error=%s", tool_name, exc)
                    result = {"error": str(exc)}

                tool_call_log.append(
                    {
                        "iteration": iteration + 1,
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result,
                    }
                )
                messages.append(
                    ToolMessage(
                        content=json.dumps(result, ensure_ascii=False, default=str),
                        tool_call_id=tool_call_id,
                    )
                )

        logger.warning("Topic advisor reached max iterations, forcing final summary")
        messages.append(HumanMessage(content="请直接给出最终推荐结论，不要再调用工具。"))
        final = self.llm_with_tools.invoke(messages)
        for char in final.content:
            yield {"type": "token", "content": char}
        yield {"type": "done", "tool_call_log": tool_call_log}

    def _run_agent_loop(self, messages: list) -> tuple[str, list]:
        tool_call_log = []

        for iteration in range(MAX_AGENT_ITERATIONS):
            logger.info("Topic advisor iteration=%s", iteration + 1)
            response = self.llm_with_tools.invoke(messages)

            if not response.tool_calls:
                return response.content, tool_call_log

            messages.append(response)
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call.get("id", f"call_{iteration}_{tool_name}")

                try:
                    tool = self.tool_map.get(tool_name)
                    result = tool.invoke(tool_args) if tool else {"error": f"未知工具: {tool_name}"}
                except Exception as exc:
                    logger.error("Topic advisor tool failed: %s error=%s", tool_name, exc)
                    result = {"error": str(exc)}

                tool_call_log.append(
                    {
                        "iteration": iteration + 1,
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result,
                    }
                )
                messages.append(
                    ToolMessage(
                        content=json.dumps(result, ensure_ascii=False, default=str),
                        tool_call_id=tool_call_id,
                    )
                )

        logger.warning("Topic advisor reached max iterations, forcing final summary")
        messages.append(HumanMessage(content="请直接给出最终推荐结论，不要再调用工具。"))
        final = self.llm_with_tools.invoke(messages)
        return final.content, tool_call_log

    def _get_tool_description(self, tool_name: str, tool_args: dict) -> str:
        if tool_name == "search_projects":
            keyword = tool_args.get("keyword", "")
            max_price = tool_args.get("max_price")
            if max_price:
                return f"正在搜索茶品: {keyword} (预算 <= {max_price})..."
            return f"正在搜索茶品: {keyword}..."
        if tool_name == "get_project_detail":
            return "正在查看茶品详情..."
        if tool_name == "compare_projects":
            return f"正在对比 {len(tool_args.get('project_ids', []))} 款茶品..."
        if tool_name == "check_tech_stack_match":
            return "正在分析风味偏好匹配度..."
        if tool_name == "get_personalized_recommendations":
            return "正在分析用户偏好并生成个性化推荐..."
        return f"正在执行工具: {tool_name}..."

    def _inject_project_actions(self, state: ConversationState, tool_call_log: List[Dict[str, Any]]):
        for log_entry in tool_call_log:
            if log_entry["tool"] not in ("search_projects", "get_personalized_recommendations"):
                continue

            result = log_entry.get("result", {})
            projects = result.get("projects", []) or result.get("products", [])
            if not projects:
                continue

            state["topic_advisor_projects"] = projects
            quick_actions = []

            for project in projects[:5]:
                quick_actions.append(
                    {
                        "type": "product",
                        "data": {
                            "product_id": project.get("id"),
                            "title": project.get("title"),
                            "price": project.get("price"),
                            "rating": project.get("rating"),
                            "sales_count": project.get("sales_count", 0),
                            "tech_stack": project.get("tech_stack", []),
                            "description": project.get("description", "")[:150],
                        },
                    }
                )

            for project in projects[:3]:
                product_title = project.get("title", "")[:12]
                quick_actions.append(
                    {
                        "type": "button",
                        "label": f"立即购买: {product_title}",
                        "action": "purchase_flow",
                        "data": {"step": "confirm_product", "product_id": project.get("id")},
                        "icon": "📝",
                    }
                )
                quick_actions.append(
                    {
                        "type": "button",
                        "label": f"加入购物车: {product_title}",
                        "action": "add_to_cart",
                        "data": {"product_id": project.get("id"), "product": project},
                        "icon": "🛒",
                    }
                )

            state["quick_actions"] = quick_actions
            return

    @staticmethod
    def _merged_preference_slots(state: ConversationState) -> Dict[str, Any]:
        slots = dict((state.get("active_task") or {}).get("slots") or {})
        slots.update(state.get("slot_updates") or {})
        return slots

    @staticmethod
    def _preference_search_response(
        projects: List[Dict[str, Any]],
        keyword: str,
        slots: Dict[str, Any],
    ) -> str:
        if not projects:
            return (
                f"我按“{keyword}”查询了当前在售茶品，暂时没有找到明确匹配的商品。"
                "您可以换一个相近香型，或者再补充茶类和预算，我继续为您筛选。"
            )

        lines = [f"按您喜欢的“{keyword}”，目前匹配到这 {len(projects[:5])} 款在售茶品："]
        for index, project in enumerate(projects[:5], start=1):
            details = [f"¥{float(project.get('price') or 0):.2f}"]
            tags = "、".join((project.get("tech_stack") or [])[:3])
            if tags:
                details.append(tags)
            lines.append(
                f"{index}. **{project.get('title', '未命名茶品')}**｜{'｜'.join(details)}"
            )

        if slots.get("brewing_constraint") == "low_boiling_point":
            lines.extend(
                [
                    "",
                    "考虑到您在高原或水温受限，具体仍以商品冲泡说明为准；"
                    "香气不足时可适当增加投茶量或延长浸泡时间。",
                ]
            )
        lines.extend(
            [
                "",
                "您可以直接点击商品卡片查看详情，也可以继续补充预算或口感浓淡。",
            ]
        )
        return "\n".join(lines)

    def _prepare_preference_search_response(self, state: ConversationState) -> bool:
        slot_updates = state.get("slot_updates") or {}
        if not has_tea_preference_slots(slot_updates):
            return False

        slots = self._merged_preference_slots(state)
        keyword = build_preference_search_keyword(slots)
        if not keyword:
            return False

        tool = self.tool_map.get("search_projects")
        if tool is None:
            return False

        arguments: Dict[str, Any] = {"keyword": keyword}
        budget = slots.get("budget_max")
        if budget is not None:
            arguments["max_price"] = budget

        try:
            result = tool.invoke(arguments)
        except Exception as exc:
            logger.warning("Deterministic tea preference search failed: %s", exc)
            state["response"] = (
                f"我已经记下您喜欢“{keyword}”，但当前库存查询暂时不可用。"
                "请稍后再试；在确认实际在售商品前，我不会凭空给您推荐。"
            )
            state["topic_advisor_tool_results"] = [
                {
                    "iteration": 0,
                    "tool": "search_projects",
                    "args": arguments,
                    "result": {"success": False, "error": str(exc)},
                }
            ]
            state["topic_advisor_projects"] = []
            state["quick_actions"] = None
            return True

        projects = result.get("projects", []) if isinstance(result, dict) else []
        tool_call_log = [
            {
                "iteration": 0,
                "tool": "search_projects",
                "args": arguments,
                "result": result,
            }
        ]
        state["response"] = self._preference_search_response(projects, keyword, slots)
        state["topic_advisor_tool_results"] = tool_call_log
        state["topic_advisor_projects"] = projects
        self._inject_project_actions(state, tool_call_log)
        return True
    def run_agent(self, state: ConversationState) -> ConversationState:
        self._refresh_tools(execution_context=state.get("execution_context"))
        if self._prepare_preference_search_response(state):
            return state
        messages = self._build_messages(state)

        try:
            final_response, tool_call_log = self._run_agent_loop(messages)
            state["response"] = (
                final_response
                or "请告诉我您的选茶需求，例如：想买一款花香明显的乌龙茶，预算 300 元以内。"
            )
            state["topic_advisor_tool_results"] = tool_call_log
            self._inject_project_actions(state, tool_call_log)
        except Exception as exc:
            logger.error("Topic advisor failed: %s", exc, exc_info=True)
            state["response"] = "抱歉，分析您的选茶需求时出现了问题，请稍后重试。"

        return state

    def run_agent_stream(self, state: ConversationState):
        self._refresh_tools(execution_context=state.get("execution_context"))
        if self._prepare_preference_search_response(state):
            for char in state.get("response", ""):
                yield char
            return
        messages = self._build_messages(state)

        try:
            final_response = ""
            tool_call_log = []
            for event in self._run_agent_loop_stream(messages):
                if event["type"] == "token":
                    final_response += event["content"]
                    yield event["content"]
                elif event["type"] == "status":
                    yield f"\n[{event['message']}]\n"
                elif event["type"] == "done":
                    tool_call_log = event.get("tool_call_log", [])

            state["response"] = final_response
            state["topic_advisor_tool_results"] = tool_call_log
            self._inject_project_actions(state, tool_call_log)
        except Exception as exc:
            logger.error("Topic advisor stream failed: %s", exc, exc_info=True)
            yield "抱歉，分析您的选茶需求时出现了问题，请稍后重试。"


__all__ = ["TopicAdvisorService", "TopicAdvisorMode"]
