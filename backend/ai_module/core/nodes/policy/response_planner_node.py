"""会话控制规划节点。

这一层不负责“理解用户在说什么”，而负责把入口分类结果
映射成系统下一步的回复模式。

边界约束：
- 这里只决定动作类型
- 不在这里挑选具体业务技能
- 不在这里直接生成自然语言
"""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.constants import (
    INFLOW_CANCEL_FLOW,
    INFLOW_CORRECTION,
    INFLOW_HANDOFF,
    INFLOW_IRRELEVANT,
    INFLOW_RELATED_BLOCKER,
    INFLOW_RELATED_QUESTION,
    INFLOW_SWITCH_FLOW,
    INFLOW_UNKNOWN,
    INFLOW_VALID_CURRENT_INPUT,
    INTENT_QA,
    RESUME_MODE_RESTART_FLOW,
    RESUME_MODE_RESUME_EXACT,
    RESUME_MODE_RESUME_FROM_SAFE_STEP,
    RESPONSE_MODE_ANSWER_THEN_RESUME,
    RESPONSE_MODE_CANCEL_CURRENT_TASK,
    RESPONSE_MODE_CLARIFY_BEFORE_RESUME,
    RESPONSE_MODE_CONTINUE_CURRENT_TASK,
    RESPONSE_MODE_HANDOFF,
    RESPONSE_MODE_HELP_CURRENT_TASK,
    RESPONSE_MODE_SWITCH_TASK,
)
from ai_module.core.state import ConversationState


class ResponsePlannerNode(BaseNode):
    """根据流程内分类结果选择回复模式和恢复策略。"""

    def _looks_like_ambiguous_reference(self, state: ConversationState) -> bool:
        message = (state.get("user_message") or "").strip()
        if not message:
            return True
        if len(message) <= 4 and any(token in message for token in ("这", "那", "继续", "然后", "咋", "怎么")):
            return True
        return message in {"这个", "那个", "这个呢", "那个呢", "然后呢", "继续呢", "怎么办", "啥意思", "什么意思"}

    def execute(self, state: ConversationState) -> ConversationState:
        state["response_mode"] = RESPONSE_MODE_CONTINUE_CURRENT_TASK
        state["resume_mode"] = None

        if not state.get("has_active_flow"):
            return state

        inflow_type = state.get("inflow_type")

        if inflow_type in {INFLOW_VALID_CURRENT_INPUT, INFLOW_CORRECTION}:
            state["response_mode"] = RESPONSE_MODE_CONTINUE_CURRENT_TASK
            state["resume_mode"] = RESUME_MODE_RESUME_EXACT
            return state

        if inflow_type == INFLOW_RELATED_QUESTION:
            if state.get("continue_previous_task"):
                state["response_mode"] = RESPONSE_MODE_CONTINUE_CURRENT_TASK
                state["resume_mode"] = RESUME_MODE_RESUME_EXACT
            else:
                state["response_mode"] = RESPONSE_MODE_ANSWER_THEN_RESUME
                state["resume_mode"] = RESUME_MODE_RESUME_EXACT
                state["continue_previous_task"] = False
                state["need_clarification"] = False
            return state

        if inflow_type == INFLOW_RELATED_BLOCKER:
            state["response_mode"] = RESPONSE_MODE_HELP_CURRENT_TASK
            state["resume_mode"] = RESUME_MODE_RESUME_FROM_SAFE_STEP
            state["continue_previous_task"] = False
            state["need_clarification"] = False
            return state

        if inflow_type == INFLOW_IRRELEVANT:
            state["response_mode"] = RESPONSE_MODE_ANSWER_THEN_RESUME
            state["resume_mode"] = RESUME_MODE_RESUME_EXACT
            state["continue_previous_task"] = False
            state["need_clarification"] = False
            return state

        if inflow_type == INFLOW_UNKNOWN:
            # unknown 默认先自然接住，而不是强迫用户做“继续 / 切换”的二选一。
            # 只有极短、明显指代不清的话，才退回澄清。
            if self._looks_like_ambiguous_reference(state):
                state["response_mode"] = RESPONSE_MODE_CLARIFY_BEFORE_RESUME
                state["resume_mode"] = RESUME_MODE_RESUME_FROM_SAFE_STEP
                state["continue_previous_task"] = False
                state["need_clarification"] = False
            else:
                state["response_mode"] = RESPONSE_MODE_ANSWER_THEN_RESUME
                state["resume_mode"] = RESUME_MODE_RESUME_EXACT
                state["continue_previous_task"] = False
                state["need_clarification"] = False
            return state

        if inflow_type == INFLOW_CANCEL_FLOW:
            state["response_mode"] = RESPONSE_MODE_CANCEL_CURRENT_TASK
            state["resume_mode"] = None
            state["continue_previous_task"] = False
            state["need_clarification"] = False
            return state

        if inflow_type == INFLOW_HANDOFF:
            state["response_mode"] = RESPONSE_MODE_HANDOFF
            state["resume_mode"] = None
            state["continue_previous_task"] = False
            return state

        if inflow_type == INFLOW_SWITCH_FLOW:
            state["response_mode"] = RESPONSE_MODE_SWITCH_TASK
            state["resume_mode"] = RESUME_MODE_RESTART_FLOW
            state["continue_previous_task"] = False
            return state

        return state
