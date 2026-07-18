"""基于运行时工具集的函数调用节点。"""
from __future__ import annotations

import logging

from services.function_tools import all_tools

from ai_module.core.constants import (
    INTENT_CART_QUERY,
    INTENT_DOCUMENT_ANALYSIS,
    INTENT_PURCHASE_GUIDE,
    INTENT_QA,
    INTENT_RECOMMEND,
    INTENT_TICKET,
)
from ai_module.core.state import ConversationState
from ai_module.core.nodes.common.base import BaseNode

logger = logging.getLogger(__name__)

SKIP_INTENTS = {
    INTENT_QA,
    INTENT_DOCUMENT_ANALYSIS,
    INTENT_TICKET,
    INTENT_PURCHASE_GUIDE,
    INTENT_RECOMMEND,
    INTENT_CART_QUERY,
}

DEFAULT_SYSTEM_PROMPT = (
    "你是一个智能客服助手。根据用户问题和当前意图，选择合适的工具获取数据。"
    "\n如果不需要调用工具，直接回答即可。"
    "\n如果工具涉及当前用户的信息，必须基于系统已注入的执行上下文执行。"
)


class FunctionCallingNode(BaseNode):
    """让大模型为当前业务包选择并调用合适的工具。"""

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)
        self.tools = []
        self.tool_map = {}
        self.llm_with_tools = None
        self._refresh_tools()

    def _refresh_tools(self, execution_context=None):
        tools = []
        if self.runtime is not None:
            tools = self.runtime.get_langchain_tools(
                "default",
                execution_context=execution_context,
            )
        if not tools and self.runtime is None:
            tools = list(all_tools)

        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}
        self.llm_with_tools = self.llm.bind_tools(tools) if self.llm and tools else None

    def _get_system_prompt(self) -> str:
        if self.runtime is None:
            return DEFAULT_SYSTEM_PROMPT
        return self.runtime.get_prompt("function_calling_system_prompt", DEFAULT_SYSTEM_PROMPT)

    def _build_messages(self, state: ConversationState) -> list:
        user_id = state.get("user_id", "")
        business_id = state.get("business_id") or "default"
        system_message = (
            f"{self._get_system_prompt()}"
            f"\n当前业务包: {business_id}"
            f"\n当前用户ID: {user_id}。如果工具需要 user_id，优先使用系统上下文。"
        )

        messages = [("system", system_message)]
        for turn in state.get("conversation_history", [])[-3:]:
            messages.append(("human", turn.get("user", "")))
            messages.append(("assistant", turn.get("assistant", "")))

        intent = state.get("intent", "未知")
        messages.append(("human", f"[用户意图: {intent}] {state['user_message']}"))
        return messages

    def execute(self, state: ConversationState) -> ConversationState:
        self._refresh_tools(execution_context=state.get("execution_context"))

        if state.get("intent") in SKIP_INTENTS or state.get("confidence", 0) < 0.6:
            state["tool_result"] = None
            state["tool_used"] = None
            logger.info("Skipping tool calling for intent=%s", state.get("intent"))
            return state

        if self.llm_with_tools is None:
            state["tool_result"] = None
            state["tool_used"] = None
            return state

        try:
            response = self.llm_with_tools.invoke(self._build_messages(state))
            if not response.tool_calls:
                state["tool_result"] = None
                state["tool_used"] = None
                return state

            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                logger.info("Calling tool: %s args=%s", tool_name, tool_args)

                tool_fn = self.tool_map.get(tool_name)
                if tool_fn is None:
                    tool_results.append({"tool": tool_name, "error": f"工具不存在: {tool_name}"})
                    continue

                try:
                    result = tool_fn.invoke(tool_args)
                    tool_results.append({"tool": tool_name, "result": result})
                    logger.info("Tool call succeeded: %s", tool_name)
                except Exception as exc:
                    logger.error("Tool call failed: %s error=%s", tool_name, exc)
                    tool_results.append({"tool": tool_name, "error": str(exc)})

            state["tool_result"] = tool_results
            state["tool_used"] = ", ".join(tool_call["name"] for tool_call in response.tool_calls)
        except Exception as exc:
            logger.error("Function calling failed: %s", exc, exc_info=True)
            state["tool_result"] = None
            state["tool_used"] = None

        return state
