"""对话策略节点。

这个节点位于对话理解和具体业务执行之间，
负责把当前轮的语义信号转换成系统真正要执行的策略：
- 继续上一轮任务
- 新开任务
- 恢复挂起任务
- 先澄清再执行

目标是把“用户这句话是什么意思”和“系统下一步该怎么做”明确拆开。
"""
from __future__ import annotations

from typing import List, Optional

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.constants import (
    DEFAULT_INTENT_LABELS,
    DIALOGUE_ACT_NEW_REQUEST,
    DIALOGUE_ACT_RESUME_TASK,
)
from ai_module.core.state import ConversationState


class PolicyNode(BaseNode):
    """在旧意图兜底逻辑运行前先确定任务策略。"""

    def _get_valid_intents(self) -> List[str]:
        if self.runtime is None:
            return list(DEFAULT_INTENT_LABELS)
        return self.runtime.get_intent_labels()

    def _pick_resumed_intent(self, state: ConversationState) -> Optional[str]:
        hinted_intent = state.get("domain_intent")
        task_stack = list(state.get("task_stack") or [])
        if hinted_intent:
            for task in reversed(task_stack):
                if task.get("intent") == hinted_intent:
                    return hinted_intent

        if task_stack:
            return task_stack[-1].get("intent")
        return None

    def execute(self, state: ConversationState) -> ConversationState:
        valid_intents = set(self._get_valid_intents())
        active_task = state.get("active_task") or {}
        active_intent = active_task.get("intent")
        last_intent = state.get("last_intent") or active_intent
        hinted_intent = state.get("domain_intent")
        dialogue_act = state.get("dialogue_act")
        self_contained_request = bool(state.get("self_contained_request"))
        continue_previous_task = bool(state.get("continue_previous_task"))
        need_clarification = bool(state.get("need_clarification"))
        confidence = float(state.get("understanding_confidence") or 0.0)
        preselected_intent = state.get("intent")

        # 策略层先产出第一版意图判断；
        # 只有语义理解无法稳定落定时，才交给意图节点兜底。
        if preselected_intent in valid_intents:
            state["confidence"] = float(state.get("confidence") or confidence or 0.9)
            if state.get("self_contained_request"):
                state["continue_previous_task"] = False
            return state

        state["intent"] = None
        state["confidence"] = None

        if dialogue_act == DIALOGUE_ACT_RESUME_TASK:
            resumed_intent = self._pick_resumed_intent(state)
            if resumed_intent in valid_intents:
                state["intent"] = resumed_intent
                state["confidence"] = max(confidence, 0.9)
                state["continue_previous_task"] = True
                state["self_contained_request"] = False
            return state

        if self_contained_request:
            state["continue_previous_task"] = False
            if hinted_intent in valid_intents:
                state["intent"] = hinted_intent
                state["confidence"] = max(confidence, 0.9)
            elif confidence > 0:
                state["confidence"] = max(confidence, 0.7)
            return state

        if continue_previous_task:
            inherited_intent = active_intent or last_intent
            if hinted_intent in valid_intents and hinted_intent != inherited_intent:
                state["continue_previous_task"] = False
                state["self_contained_request"] = True
                state["dialogue_act"] = DIALOGUE_ACT_NEW_REQUEST
                state["intent"] = hinted_intent
                state["confidence"] = max(confidence, 0.9)
                return state

            if inherited_intent in valid_intents:
                state["intent"] = inherited_intent
                state["confidence"] = max(confidence, 0.88)
                return state

        if hinted_intent in valid_intents:
            state["intent"] = hinted_intent
            state["confidence"] = max(confidence, 0.85)
            state["self_contained_request"] = True
            return state

        if need_clarification:
            state["confidence"] = min(confidence, 0.4) if confidence else 0.3
            return state

        if confidence > 0:
            state["confidence"] = max(confidence, 0.55)
        return state
