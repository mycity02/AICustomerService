"""对话状态管理节点。

这个节点是对话层中负责“持久状态”的一半：
对话理解节点负责说明本轮发生了什么，
而这里负责决定这些信号如何改变长期存在的任务状态。
"""
from __future__ import annotations

import copy
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.constants import (
    CONTINUATION_DIALOGUE_ACTS,
    DIALOGUE_ACT_NEW_REQUEST,
    DIALOGUE_ACT_RESUME_TASK,
    DIALOGUE_ACT_SWITCH_TOPIC,
)
from ai_module.core.state import ConversationState


class DialogueStateNode(BaseNode):
    """维护当前任务、待处理状态以及挂起任务栈。

    当前任务表示“助手此刻正在协助什么事情”；
    挂起任务栈用于保存被中断的任务，便于后续通过“继续刚才那个”
    之类的话术恢复现场。
    """

    MAX_TASK_STACK = 5

    def _now(self, state: ConversationState) -> str:
        return state.get("timestamp") or datetime.now().isoformat()

    def _copy_task(self, task: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not task:
            return None
        return copy.deepcopy(task)

    def _copy_task_stack(self, task_stack: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        return [copy.deepcopy(task) for task in (task_stack or [])]

    def _selected_action_slots(self, selected_action: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not selected_action:
            return {}

        action_type = selected_action.get("type")
        data = selected_action.get("data", {})
        slots: Dict[str, Any] = {"selected_action_type": action_type}

        if action_type == "product":
            if data.get("product_id") is not None:
                slots["selected_product_id"] = data.get("product_id")
            if data.get("title"):
                slots["selected_product_title"] = data.get("title")
        elif action_type in {"order_card", "order_card_simple"}:
            if data.get("order_id") is not None:
                slots["selected_order_id"] = data.get("order_id")
            if data.get("order_no"):
                slots["selected_order_no"] = data.get("order_no")
        elif action_type == "button":
            if selected_action.get("action"):
                slots["selected_button_action"] = selected_action.get("action")
            if selected_action.get("label"):
                slots["selected_button_label"] = selected_action.get("label")

        return slots

    def _build_task(
        self,
        state: ConversationState,
        *,
        intent: Optional[str],
        inherited_slots: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not intent:
            return None

        slot_updates = dict(inherited_slots or {})
        slot_updates.update(state.get("slot_updates") or {})
        slot_updates.update(self._selected_action_slots(state.get("selected_quick_action")))
        now = self._now(state)

        return {
            "id": str(uuid.uuid4()),
            "intent": intent,
            "status": "active",
            "slots": slot_updates,
            "selected_action": copy.deepcopy(state.get("selected_quick_action")),
            "last_dialogue_act": state.get("dialogue_act"),
            "last_user_message": state.get("user_message"),
            "started_at": now,
            "updated_at": now,
        }

    def _merge_into_task(self, task: Dict[str, Any], state: ConversationState) -> Dict[str, Any]:
        merged = self._copy_task(task) or {}
        slots = dict(merged.get("slots", {}))
        slots.update(state.get("slot_updates") or {})
        slots.update(self._selected_action_slots(state.get("selected_quick_action")))
        merged["slots"] = slots

        if state.get("selected_quick_action") is not None:
            merged["selected_action"] = copy.deepcopy(state.get("selected_quick_action"))

        merged["intent"] = state.get("intent") or merged.get("intent")
        merged["status"] = "active"
        merged["last_dialogue_act"] = state.get("dialogue_act")
        merged["last_user_message"] = state.get("user_message")
        merged["updated_at"] = self._now(state)
        return merged

    def _suspend_task(self, task: Dict[str, Any], state: ConversationState) -> Dict[str, Any]:
        suspended = self._copy_task(task) or {}
        suspended["status"] = "suspended"
        suspended["updated_at"] = self._now(state)
        return suspended

    def _push_task(self, task_stack: List[Dict[str, Any]], task: Optional[Dict[str, Any]], state: ConversationState) -> List[Dict[str, Any]]:
        if not task:
            return task_stack

        suspended = self._suspend_task(task, state)
        task_id = suspended.get("id")
        filtered = [item for item in task_stack if item.get("id") != task_id]
        filtered.append(suspended)
        return filtered[-self.MAX_TASK_STACK :]

    def _pop_task_by_intent(
        self,
        task_stack: List[Dict[str, Any]],
        intent: Optional[str],
    ) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        if not intent:
            return None, task_stack

        for index in range(len(task_stack) - 1, -1, -1):
            task = task_stack[index]
            if task.get("intent") == intent:
                restored = copy.deepcopy(task)
                remaining = task_stack[:index] + task_stack[index + 1 :]
                return restored, remaining
        return None, task_stack

    def execute(self, state: ConversationState) -> ConversationState:
        intent = state.get("intent")
        dialogue_act = state.get("dialogue_act")
        continue_previous_task = bool(state.get("continue_previous_task"))
        active_task = self._copy_task(state.get("active_task"))
        task_stack = self._copy_task_stack(state.get("task_stack"))

        # 当前轮语义已经明确后，先清理过期的待追问状态，
        # 再计算下一步的活动任务。
        if dialogue_act in CONTINUATION_DIALOGUE_ACTS | {DIALOGUE_ACT_NEW_REQUEST, DIALOGUE_ACT_SWITCH_TOPIC, DIALOGUE_ACT_RESUME_TASK}:
            state["pending_question"] = None
            state["pending_action"] = None

        if dialogue_act == DIALOGUE_ACT_RESUME_TASK:
            # “恢复任务”会显式从挂起栈恢复旧任务；
            # 如果当前任务尚未完成，则先把它挂起到栈里。
            restored_task, task_stack = self._pop_task_by_intent(task_stack, intent)
            if active_task and active_task.get("status") != "completed":
                task_stack = self._push_task(task_stack, active_task, state)
            active_task = self._merge_into_task(restored_task, state) if restored_task else self._build_task(state, intent=intent)
        elif continue_previous_task:
            # 延续上一轮时，优先原地更新当前任务；
            # 如果当前活动任务不是同一主题，则尝试从挂起栈中恢复匹配任务。
            if active_task and active_task.get("intent") == intent:
                active_task = self._merge_into_task(active_task, state)
            else:
                restored_task, task_stack = self._pop_task_by_intent(task_stack, intent)
                if restored_task:
                    active_task = self._merge_into_task(restored_task, state)
                else:
                    active_task = self._build_task(state, intent=intent, inherited_slots=(active_task or {}).get("slots"))
        else:
            # 确认是新请求时，先挂起旧任务，
            # 这样用户后面还能回来继续之前的上下文。
            if active_task and active_task.get("status") != "completed":
                task_stack = self._push_task(task_stack, active_task, state)
            active_task = self._build_task(state, intent=intent)

        if active_task:
            active_task["updated_at"] = self._now(state)
            active_task["status"] = "active"

        state["active_task"] = active_task
        state["task_stack"] = task_stack[-self.MAX_TASK_STACK :]
        return state
