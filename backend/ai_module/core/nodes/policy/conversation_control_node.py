"""会话控制回复节点。"""
from __future__ import annotations

from typing import Optional

from langchain_core.prompts import ChatPromptTemplate

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.domain_scope import looks_out_of_business_scope
from ai_module.core.memory_builder import MemoryContextBuilder
from ai_module.core.out_of_scope_reply import compose_out_of_scope_reply
from ai_module.core.constants import (
    INTENT_RECOMMEND,
    RESPONSE_MODE_ANSWER_THEN_RESUME,
    RESPONSE_MODE_CANCEL_CURRENT_TASK,
    RESPONSE_MODE_CLARIFY_BEFORE_RESUME,
    RESPONSE_MODE_HELP_CURRENT_TASK,
)
from ai_module.core.state import ConversationState

_FLOW_LABELS = {
    "purchase_flow": "购买流程",
    "aftersales_flow": "售后流程",
}

_STEP_HINTS = {
    "select_recommended_item": "刚才那批推荐里更偏向哪一个",
    "select_order": "您要处理的是哪一个订单",
    "select_coupon": "想使用哪一张优惠券",
    "select_address": "收货地址该怎么选",
    "answer_follow_up": "上一轮还差哪部分信息",
    "choose_next_step": "下一步想继续哪种操作",
}

class ConversationControlNode(BaseNode):
    """生成打断、接话、帮助、取消时的统一回复。"""

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)
        self.memory_builder = MemoryContextBuilder()

    def _build_reference_clarification(self, state: ConversationState, step_hint: Optional[str]) -> str:
        user_message = (state.get("user_message") or "").strip()
        quoted = f"“{user_message}”" if user_message else "这句话"

        if state.get("current_step") == "select_recommended_item":
            return (
                f"{quoted}里指的对象我还没对上。"
                "你可以直接说“第一个”“第二个”，或者说“那个 Java 的”，我就能顺着接下去。"
            )

        if step_hint:
            return (
                f"{quoted}里指的内容还不够具体。"
                f"你把和“{step_hint}”相关的对象再说清一点，我就直接接着答。"
            )

        return (
            f"{quoted}里有个指代我还没完全对上。"
            "你把对象或者想问的内容再说具体一点，我就直接接着回复。"
        )

    def _flow_label(self, state: ConversationState) -> str:
        active_flow = state.get("active_flow")
        if active_flow in _FLOW_LABELS:
            return _FLOW_LABELS[active_flow]
        if active_flow:
            return f"{active_flow}任务"
        return "当前任务"

    def _step_hint(self, state: ConversationState) -> Optional[str]:
        current_step = state.get("current_step")
        if current_step in _STEP_HINTS:
            return _STEP_HINTS[current_step]
        pending_question = (state.get("pending_question") or "").strip()
        if pending_question:
            return pending_question
        return None

    def _looks_out_of_business_scope(self, state: ConversationState) -> bool:
        return looks_out_of_business_scope(
            state.get("user_message", ""),
            runtime=self.runtime,
        )

    def _business_name(self, state: ConversationState) -> str:
        execution_context = state.get("execution_context") or {}
        if isinstance(execution_context, dict):
            business_name = execution_context.get("business_name")
            if business_name:
                return business_name

        if self.runtime is not None:
            business_pack = getattr(self.runtime, "business_pack", None)
            if business_pack is not None:
                return getattr(business_pack, "business_name", "") or "当前业务"

        return "当前业务"

    def _build_topic_advisor_fallback_reply(self, state: ConversationState) -> str:
        active_task = state.get("active_task") or {}
        slots = active_task.get("slots") or {}
        language = slots.get("language")
        if language:
            return f"说回刚才在看的 {language} 茶品，您更在意香型、预算还是口感浓淡？"
        return "说回刚才选茶这件事，您更在意茶类、香型、预算还是口感浓淡？"

    def _build_generic_fallback_reply(self, state: ConversationState, flow_label: str) -> str:
        return f"顺着刚才的{flow_label}，您可以继续往下说，我接着帮您处理。"

    def _build_scope_redirect_text(self, state: ConversationState, flow_label: str) -> str:
        if state.get("active_flow") == INTENT_RECOMMEND:
            return self._build_topic_advisor_fallback_reply(state)
        return self._build_generic_fallback_reply(state, flow_label)

    def _build_context_hint(self, state: ConversationState) -> str:
        parts = []
        step_hint = self._step_hint(state)
        if step_hint:
            parts.append(f"当前停留点：{step_hint}")
        history = state.get("conversation_history") or []
        if history:
            last = history[-1]
            last_assistant = (last.get("assistant") or "").strip()
            if last_assistant:
                parts.append(f"上一轮助手说：{last_assistant[:80]}")
        return "；".join(parts) if parts else "用户刚进入业务流程"

    def _build_scope_redirect_reply(self, state: ConversationState, flow_label: str) -> str:
        return compose_out_of_scope_reply(
            state.get("user_message", ""),
            self._build_scope_redirect_text(state, flow_label),
            llm=self.llm,
            business_name=self._business_name(state),
            task_hint=flow_label,
            context_hint=self._build_context_hint(state),
        )

    def _generate_side_topic_reply(self, state: ConversationState, flow_label: str, step_hint: Optional[str]) -> str:
        if self._looks_out_of_business_scope(state):
            return self._build_scope_redirect_reply(state, flow_label)

        if self.llm is None:
            return self._build_scope_redirect_reply(state, flow_label)

        short_term_memory = self.memory_builder.build_short_term_memory_text(state)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一个自然、克制、会收主线的中文 AI 助手。
当前有一个尚未完成的主任务，用户这轮临时插入了别的话题。

你的目标：
1. 先自然接住用户当前这句话，给出简短、有帮助的回应。
2. 如果这是明显离开主任务的侧话题，只做高层、简短回答，不要深聊成一个新任务。
3. 回复控制在 2 到 4 句，尽量短。
4. 最后一句主动拉回刚才的主任务，或者顺势追问一个推进主任务的问题。
5. 不要让用户做“继续还是切换”的二选一，也不要完全忘掉主任务。
6. 如果你对事实不确定，就给稳妥、泛化的建议，不要编造细节。

风格要求：
- 像真人顺手接话，但始终记得主任务。
- 可以有一句轻微过渡，但不要直接说“我先简单说一下”“我先接一下”这类提示词式表述。
- 禁止把侧话题展开成长篇回答。
- 对于“你好/谢谢/在吗”这类轻寒暄，可以更简短。""",
                ),
                (
                    "human",
                    """当前业务：{business_name}
当前主任务：{flow_label}
当前停留点：{step_hint}
短期记忆：{short_term_memory}

用户这一轮说：{message}

请直接输出给用户的回复：""",
                ),
            ]
        )

        response = self.llm.invoke(
            prompt.format_messages(
                business_name=self._business_name(state),
                flow_label=flow_label,
                step_hint=step_hint or "未显式记录",
                short_term_memory=short_term_memory,
                message=state.get("user_message", ""),
            )
        )
        content = response.content if hasattr(response, "content") else str(response)
        return (content or "").strip()

    def execute(self, state: ConversationState) -> ConversationState:
        response_mode = state.get("response_mode")
        flow_label = self._flow_label(state)
        step_hint = self._step_hint(state)

        if response_mode == RESPONSE_MODE_ANSWER_THEN_RESUME:
            state["response"] = self._generate_side_topic_reply(state, flow_label, step_hint)
            state["quick_actions"] = None
            return state

        if response_mode == RESPONSE_MODE_CANCEL_CURRENT_TASK:
            state["response"] = (
                f"好的，我先把刚才的{flow_label}停在这里。"
                "后面如果还想接着办，直接说“继续刚才那个”就行。"
            )
            state["quick_actions"] = None
            return state

        if response_mode == RESPONSE_MODE_HELP_CURRENT_TASK:
            extra = f" 当前看起来更像是卡在“{step_hint}”这一步。" if step_hint else ""
            state["response"] = (
                f"我先不继续推进刚才的{flow_label}。{extra}"
                "你直接告诉我具体卡在哪、哪一步不会操作，"
                "我先把这一步讲清楚，再陪你往下走。"
            )
            state["quick_actions"] = None
            return state

        if response_mode == RESPONSE_MODE_CLARIFY_BEFORE_RESUME:
            state["response"] = self._build_reference_clarification(state, step_hint)
            state["quick_actions"] = None
            return state

        state["response"] = (
            f"我先把刚才的{flow_label}保留着。"
            "你想继续就顺着说，想补充新的信息我也能接着处理。"
        )
        state["quick_actions"] = None
        return state
