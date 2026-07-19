"""统一会话入口节点。

这个节点是对话层唯一的前门：

- 没有活动任务时，走全局意图识别
- 已有活动任务时，先判断当前输入对主任务的作用

设计目标不是把用户每句话都硬塞回原流程，而是先判断：
1. 这是继续主任务
2. 这是明确切到新任务
3. 这是顺手插入的侧话题，先自然接住
"""
from __future__ import annotations

import copy
import json
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate

from ai_module.core.capability_registry import find_unsupported_capability
from ai_module.core.domain_scope import classify_guarded_request, looks_out_of_business_scope
from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.nodes.understanding.intent_node import IntentRecognitionNode
from ai_module.core.nodes.understanding.turn_understanding_node import TurnUnderstandingNode
from ai_module.core.memory_builder import MemoryContextBuilder
from ai_module.core.constants import (
    DIALOGUE_ACT_NEW_REQUEST,
    DIALOGUE_ACT_REJECT,
    DIALOGUE_ACT_SWITCH_TOPIC,
    DIALOGUE_ACT_UNCLEAR,
    ENTRY_CLASSIFIER_GLOBAL,
    ENTRY_CLASSIFIER_INFLOW,
    INFLOW_CANCEL_FLOW,
    INFLOW_CORRECTION,
    INFLOW_HANDOFF,
    INFLOW_IRRELEVANT,
    INFLOW_RELATED_BLOCKER,
    INFLOW_RELATED_QUESTION,
    INFLOW_SWITCH_FLOW,
    INFLOW_TYPES,
    INFLOW_UNKNOWN,
    INFLOW_VALID_CURRENT_INPUT,
    INTENT_QA,
    INTENT_TICKET,
    RESUME_MODE_RESUME_EXACT,
    RESPONSE_MODE_ANSWER_THEN_RESUME,
)
from ai_module.core.state import ConversationState

logger = logging.getLogger(__name__)

_HANDOFF_RE = re.compile(r"(转人工|人工客服|客服介入|我要投诉|投诉|升级处理|找客服)", re.IGNORECASE)
_CANCEL_RE = re.compile(r"^(取消|不办了|先不弄了|先这样吧|算了|不用了|结束流程|退出流程)$", re.IGNORECASE)
_BLOCKER_RE = re.compile(r"(不会|不懂|不知道怎么|找不到|没找到|没有这个|上传不了|打不开|进不去|操作不了)", re.IGNORECASE)
_SMALLTALK_RE = re.compile(r"^(你好|hello|hi|在吗|谢谢|辛苦了|哈哈|好的谢谢|没事了)$", re.IGNORECASE)
_AMBIGUOUS_REFERENCE_RE = re.compile(r"^(这个|那个|这个呢|那个呢|然后呢|接着呢|怎么办|什么意思|啥意思|继续呢)[?？]?$")


class MessageEntryNode(BaseNode):
    """根据会话状态选择识别路径的统一入口。"""

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)
        self.global_intent_classifier = IntentRecognitionNode(llm=llm, runtime=runtime)
        self.inflow_understanding = TurnUnderstandingNode(llm=llm, runtime=runtime)
        self.memory_builder = MemoryContextBuilder()

    def _reset_entry_fields(self, state: ConversationState) -> None:
        state["entry_classifier"] = None
        state["has_active_flow"] = False
        state["active_flow"] = None
        state["current_step"] = None
        state["expected_user_acts"] = []
        state["inflow_type"] = None
        state["flow_relation"] = None
        state["response_mode"] = None
        state["resume_mode"] = None
        state["dialogue_act"] = None
        state["domain_intent"] = None
        state["skill_route"] = None
        state["unsupported_capability"] = None
        state["unsupported_capability_label"] = None
        state["unsupported_capability_action"] = None
        state["semantic_source"] = None
        state["guard_category"] = None
        state["self_contained_request"] = False
        state["continue_previous_task"] = False
        state["need_clarification"] = False
        state["understanding_confidence"] = None
        state["slot_updates"] = {}
        state["reference_resolution"] = None
        state["selected_quick_action"] = None
        state["intent"] = None
        state["confidence"] = None

    def _has_active_flow(self, state: ConversationState) -> bool:
        if state.get("purchase_flow") or state.get("aftersales_flow"):
            return True

        active_task = state.get("active_task") or {}
        if active_task.get("status") in {"active", "awaiting_user"}:
            return True

        return bool(state.get("pending_action") or state.get("pending_question"))

    def _resolve_active_flow(self, state: ConversationState) -> tuple[Optional[str], Optional[str]]:
        if state.get("purchase_flow"):
            flow = state["purchase_flow"] or {}
            return "purchase_flow", flow.get("step")

        if state.get("aftersales_flow"):
            flow = state["aftersales_flow"] or {}
            return "aftersales_flow", flow.get("step")

        active_task = state.get("active_task") or {}
        active_flow = active_task.get("intent") or state.get("last_intent")
        current_step = active_task.get("pending_action") or state.get("pending_action")
        return active_flow, current_step

    def _derive_expected_user_acts(self, state: ConversationState, current_step: Optional[str]) -> List[str]:
        if current_step == "select_recommended_item":
            return [
                INFLOW_VALID_CURRENT_INPUT,
                INFLOW_CORRECTION,
                INFLOW_RELATED_QUESTION,
                INFLOW_SWITCH_FLOW,
                INFLOW_CANCEL_FLOW,
            ]
        if current_step in {"select_order", "select_coupon", "select_address"}:
            return [
                INFLOW_VALID_CURRENT_INPUT,
                INFLOW_RELATED_QUESTION,
                INFLOW_RELATED_BLOCKER,
                INFLOW_SWITCH_FLOW,
                INFLOW_CANCEL_FLOW,
            ]
        if current_step in {"purchase_flow_step", "aftersales_flow_step"}:
            return [
                INFLOW_VALID_CURRENT_INPUT,
                INFLOW_RELATED_QUESTION,
                INFLOW_RELATED_BLOCKER,
                INFLOW_CORRECTION,
                INFLOW_SWITCH_FLOW,
                INFLOW_CANCEL_FLOW,
                INFLOW_HANDOFF,
            ]
        if current_step in {"answer_follow_up", "choose_next_step"}:
            return [
                INFLOW_VALID_CURRENT_INPUT,
                INFLOW_RELATED_QUESTION,
                INFLOW_RELATED_BLOCKER,
                INFLOW_SWITCH_FLOW,
                INFLOW_CANCEL_FLOW,
                INFLOW_HANDOFF,
                INFLOW_IRRELEVANT,
            ]

        if self._has_active_flow(state):
            return [
                INFLOW_VALID_CURRENT_INPUT,
                INFLOW_RELATED_QUESTION,
                INFLOW_RELATED_BLOCKER,
                INFLOW_CORRECTION,
                INFLOW_SWITCH_FLOW,
                INFLOW_CANCEL_FLOW,
                INFLOW_HANDOFF,
                INFLOW_IRRELEVANT,
                INFLOW_UNKNOWN,
            ]
        return []

    def _append_preselected_intent(self, state: ConversationState, intent: Optional[str], confidence: float) -> None:
        if not intent:
            return
        intent_history = state.get("intent_history") or []
        self.global_intent_classifier._append_intent_history(state, intent_history, intent, confidence)

    def _has_supported_business_signal(self, message: str) -> bool:
        rule_result = self.global_intent_classifier._match_by_rules(message or "")
        return bool(rule_result and rule_result[0] != INTENT_QA)

    def _looks_out_of_business_scope(self, state: ConversationState) -> bool:
        return looks_out_of_business_scope(
            state.get("user_message", ""),
            runtime=self.runtime,
        )

    def _build_domain_scope_state(self, state: ConversationState) -> ConversationState:
        guard_category = classify_guarded_request(state.get("user_message", ""))
        state["skill_route"] = "domain_scope_guard"
        state["guard_category"] = guard_category
        state["semantic_source"] = "safety_guard" if guard_category else "domain_scope_guard"
        state["intent"] = None
        state["domain_intent"] = None
        state["confidence"] = 0.98
        state["understanding_confidence"] = 0.98
        state["need_clarification"] = False
        state["continue_previous_task"] = False
        state["self_contained_request"] = True

        if state.get("has_active_flow"):
            state["entry_classifier"] = ENTRY_CLASSIFIER_INFLOW
            state["inflow_type"] = INFLOW_IRRELEVANT
            state["flow_relation"] = "interrupt"
            state["dialogue_act"] = DIALOGUE_ACT_SWITCH_TOPIC
            state["response_mode"] = RESPONSE_MODE_ANSWER_THEN_RESUME
            state["resume_mode"] = RESUME_MODE_RESUME_EXACT
        else:
            state["entry_classifier"] = ENTRY_CLASSIFIER_GLOBAL
            state["flow_relation"] = "no_flow"
            state["dialogue_act"] = DIALOGUE_ACT_NEW_REQUEST

        return state

    def _find_unsupported_capability(self, state: ConversationState) -> Optional[Dict[str, Any]]:
        if self.runtime is None:
            return None

        business_info = self.runtime.get_business_info() if hasattr(self.runtime, "get_business_info") else {}
        features = business_info.get("features") if isinstance(business_info, dict) else {}
        business_pack = getattr(self.runtime, "business_pack", None)
        config = getattr(business_pack, "config", {}) if business_pack is not None else {}
        return find_unsupported_capability(
            state.get("user_message", ""),
            features=features if isinstance(features, dict) else {},
            config=config if isinstance(config, dict) else {},
        )

    def _build_unsupported_capability_state(
        self,
        state: ConversationState,
        capability: Dict[str, Any],
    ) -> ConversationState:
        state["skill_route"] = "unsupported_capability"
        state["unsupported_capability"] = capability.get("key")
        state["unsupported_capability_label"] = capability.get("label")
        state["unsupported_capability_action"] = capability.get("fallback_action")
        state["semantic_source"] = "capability_registry"
        state["intent"] = None
        state["domain_intent"] = None
        state["confidence"] = 0.98
        state["understanding_confidence"] = 0.98
        state["need_clarification"] = False
        state["continue_previous_task"] = False
        state["self_contained_request"] = True

        if state.get("has_active_flow"):
            state["entry_classifier"] = ENTRY_CLASSIFIER_INFLOW
            state["inflow_type"] = INFLOW_IRRELEVANT
            state["flow_relation"] = "interrupt"
            state["dialogue_act"] = DIALOGUE_ACT_SWITCH_TOPIC
            state["response_mode"] = RESPONSE_MODE_ANSWER_THEN_RESUME
            state["resume_mode"] = RESUME_MODE_RESUME_EXACT
        else:
            state["entry_classifier"] = ENTRY_CLASSIFIER_GLOBAL
            state["flow_relation"] = "no_flow"
            state["dialogue_act"] = DIALOGUE_ACT_NEW_REQUEST

        return state

    def _format_recent_history(self, history: List[Dict[str, Any]], limit: int = 3) -> str:
        formatted = self.memory_builder.build_recent_history_text(history, limit=max(limit, 6))
        return formatted.replace("用户：", "user: ").replace("助手：", "assistant: ")

    def _extract_json_block(self, text: str) -> Optional[str]:
        if not text:
            return None
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            return fenced.group(1)
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return text[start : end + 1]

    def _normalize_inflow_llm_result(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        inflow_type = payload.get("inflow_type")
        if inflow_type not in INFLOW_TYPES:
            return None

        confidence = payload.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = None

        return {
            "inflow_type": inflow_type,
            "domain_intent": payload.get("domain_intent"),
            "continue_previous_task": bool(payload.get("continue_previous_task", False)),
            "need_clarification": bool(payload.get("need_clarification", False)),
            "confidence": confidence,
        }

    def _build_inflow_prompt(self) -> ChatPromptTemplate:
        system_prompt = """你负责识别“已有活动流程中的用户输入”。
只输出 JSON，不要输出解释。

输出字段：
- inflow_type: 必须是 valid_current_input/related_question/related_blocker/correction/switch_flow/cancel_flow/handoff/irrelevant/unknown 之一
- domain_intent: 业务意图标签，无法确定时输出 null
- continue_previous_task: 布尔值
- need_clarification: 布尔值
- confidence: 0 到 1 之间的数字

判断原则：
1. 只有当消息可以被当前流程直接消费时，才使用 valid_current_input。
2. 只有当用户明确开启不同业务任务时，才使用 switch_flow。
3. irrelevant 用于不会直接替换当前任务、但值得自然接住的插话或顺手聊天。
4. 如果消息过于模糊，无法安全执行，就使用 unknown。
5. 除非切换任务非常明确，否则 domain_intent 保持为 null。
"""
        return ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input_payload}")])

    def _infer_inflow_with_llm(
        self,
        state: ConversationState,
        *,
        active_flow: Optional[str],
        current_step: Optional[str],
        expected_user_acts: List[str],
        rule_guess: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if self.llm is None:
            return None

        prompt = self._build_inflow_prompt()
        payload = {
            "message": state.get("user_message"),
            "active_flow": active_flow,
            "current_step": current_step,
            "pending_action": state.get("pending_action"),
            "pending_question": state.get("pending_question"),
            "expected_user_acts": expected_user_acts,
            "rule_guess": rule_guess,
            "recent_history": self._format_recent_history(state.get("conversation_history") or []),
            "task_snapshot": self.memory_builder.build_task_snapshot_text(state),
        }
        try:
            response = self.llm.invoke(
                prompt.format_messages(input_payload=json.dumps(payload, ensure_ascii=False, indent=2))
            )
            raw = response.content if hasattr(response, "content") else str(response)
            json_block = self._extract_json_block(raw)
            if not json_block:
                return None
            parsed = json.loads(json_block)
            if not isinstance(parsed, dict):
                return None
            return self._normalize_inflow_llm_result(parsed)
        except Exception as exc:
            logger.warning("Message entry inflow LLM fallback failed: %s", exc)
            return None

    def _run_global_intent(self, state: ConversationState) -> ConversationState:
        state["entry_classifier"] = ENTRY_CLASSIFIER_GLOBAL
        state["flow_relation"] = "no_flow"
        state["dialogue_act"] = DIALOGUE_ACT_NEW_REQUEST
        state["self_contained_request"] = True
        state["continue_previous_task"] = False

        result = self.global_intent_classifier.execute(state)
        if result.get("intent"):
            confidence = float(result.get("confidence") or 0.9)
            result["domain_intent"] = result.get("intent")
            result["understanding_confidence"] = confidence
            result["need_clarification"] = False
        else:
            result["need_clarification"] = True
            result["understanding_confidence"] = float(result.get("confidence") or 0.3)
        return result

    def _is_switch_request(self, state: ConversationState, active_flow: Optional[str]) -> bool:
        hinted_intent = state.get("domain_intent")
        if not state.get("self_contained_request"):
            return False
        if not hinted_intent:
            return False
        if hinted_intent == INTENT_QA:
            return False
        if not self._has_supported_business_signal(state.get("user_message", "")):
            return False
        return hinted_intent != active_flow

    def _build_switch_state(
        self,
        state: ConversationState,
        *,
        active_flow: Optional[str],
        current_step: Optional[str],
        expected_user_acts: List[str],
    ) -> ConversationState:
        switched = self.global_intent_classifier.execute(state)
        switched["entry_classifier"] = ENTRY_CLASSIFIER_INFLOW
        switched["has_active_flow"] = True
        switched["active_flow"] = active_flow
        switched["current_step"] = current_step
        switched["expected_user_acts"] = expected_user_acts
        switched["inflow_type"] = INFLOW_SWITCH_FLOW
        switched["flow_relation"] = "switch"
        switched["continue_previous_task"] = False
        switched["self_contained_request"] = True
        switched["dialogue_act"] = DIALOGUE_ACT_SWITCH_TOPIC
        if not switched.get("intent") and state.get("domain_intent"):
            switched["intent"] = state["domain_intent"]
            switched["confidence"] = max(float(state.get("understanding_confidence") or 0.0), 0.85)
            self._append_preselected_intent(switched, switched["intent"], float(switched["confidence"]))
        switched["domain_intent"] = switched.get("intent") or state.get("domain_intent")
        switched["understanding_confidence"] = float(
            switched.get("confidence") or state.get("understanding_confidence") or 0.85
        )
        switched["need_clarification"] = not bool(switched.get("intent"))
        return switched

    def _try_soft_switch_to_global_intent(
        self,
        state: ConversationState,
        *,
        active_flow: Optional[str],
        current_step: Optional[str],
        expected_user_acts: List[str],
        min_confidence: float = 0.78,
    ) -> Optional[ConversationState]:
        if not self._has_supported_business_signal(state.get("user_message", "")):
            return None

        probe_state = copy.deepcopy(state)
        probe_state["entry_classifier"] = ENTRY_CLASSIFIER_GLOBAL
        probe_state["has_active_flow"] = False
        probe_state["active_flow"] = None
        probe_state["current_step"] = None
        probe_state["expected_user_acts"] = []
        probe_state["dialogue_act"] = DIALOGUE_ACT_NEW_REQUEST
        probe_state["self_contained_request"] = True
        probe_state["continue_previous_task"] = False
        probe_state["intent"] = None
        probe_state["confidence"] = None
        probe_state["domain_intent"] = None
        probe_state["need_clarification"] = False

        result = self.global_intent_classifier.execute(probe_state)
        intent = result.get("intent")
        confidence = float(result.get("confidence") or 0.0)

        if not intent or confidence < min_confidence:
            return None
        if intent == active_flow:
            return None
        if intent == INTENT_QA:
            return None

        result["entry_classifier"] = ENTRY_CLASSIFIER_INFLOW
        result["has_active_flow"] = True
        result["active_flow"] = active_flow
        result["current_step"] = current_step
        result["expected_user_acts"] = expected_user_acts
        result["inflow_type"] = INFLOW_SWITCH_FLOW
        result["flow_relation"] = "switch"
        result["dialogue_act"] = DIALOGUE_ACT_SWITCH_TOPIC
        result["self_contained_request"] = True
        result["continue_previous_task"] = False
        result["domain_intent"] = intent
        result["understanding_confidence"] = confidence
        result["need_clarification"] = False
        return result

    def _looks_like_ambiguous_reference(self, message: str) -> bool:
        normalized = (message or "").strip()
        if not normalized:
            return True
        if _AMBIGUOUS_REFERENCE_RE.match(normalized):
            return True
        return len(normalized) <= 4 and any(token in normalized for token in ("这", "那", "继续", "然后", "咋", "怎么"))

    def _apply_non_switch_inflow(
        self,
        state: ConversationState,
        active_flow: Optional[str],
        inflow_type: str,
    ) -> ConversationState:
        state["inflow_type"] = inflow_type
        state["self_contained_request"] = False
        if inflow_type in {INFLOW_VALID_CURRENT_INPUT, INFLOW_CORRECTION}:
            state["continue_previous_task"] = True
        elif inflow_type == INFLOW_RELATED_QUESTION:
            state["continue_previous_task"] = bool(state.get("continue_previous_task"))
        else:
            state["continue_previous_task"] = False

        if inflow_type in {INFLOW_VALID_CURRENT_INPUT, INFLOW_CORRECTION}:
            state["flow_relation"] = "continue"
        elif inflow_type == INFLOW_RELATED_QUESTION:
            state["flow_relation"] = "continue" if state.get("continue_previous_task") else "interrupt"
        elif inflow_type == INFLOW_RELATED_BLOCKER:
            state["flow_relation"] = "pause"
        elif inflow_type == INFLOW_CANCEL_FLOW:
            state["flow_relation"] = "cancel"
        elif inflow_type == INFLOW_IRRELEVANT:
            state["flow_relation"] = "interrupt"
        else:
            state["flow_relation"] = "clarify"

        if inflow_type == INFLOW_UNKNOWN:
            state["need_clarification"] = True
            state["dialogue_act"] = DIALOGUE_ACT_UNCLEAR
            state["confidence"] = float(state.get("understanding_confidence") or 0.3)
            return state

        should_bind_active_flow = inflow_type in {
            INFLOW_VALID_CURRENT_INPUT,
            INFLOW_CORRECTION,
            INFLOW_RELATED_BLOCKER,
        } or (inflow_type == INFLOW_RELATED_QUESTION and state.get("continue_previous_task"))

        if active_flow and should_bind_active_flow:
            confidence = float(state.get("confidence") or state.get("understanding_confidence") or 0.88)
            state["intent"] = active_flow
            state["confidence"] = confidence
            self._append_preselected_intent(state, active_flow, confidence)
        return state

    def _run_inflow_classifier(self, state: ConversationState) -> ConversationState:
        active_flow = state.get("active_flow")
        current_step = state.get("current_step")
        expected_user_acts = state.get("expected_user_acts") or []
        message = (state.get("user_message") or "").strip()

        state["entry_classifier"] = ENTRY_CLASSIFIER_INFLOW

        if _HANDOFF_RE.search(message):
            state["inflow_type"] = INFLOW_HANDOFF
            state["flow_relation"] = "handoff"
            state["dialogue_act"] = DIALOGUE_ACT_SWITCH_TOPIC
            state["self_contained_request"] = True
            state["continue_previous_task"] = False
            state["intent"] = INTENT_TICKET
            state["domain_intent"] = INTENT_TICKET
            state["understanding_confidence"] = 0.96
            state["confidence"] = 0.96
            self._append_preselected_intent(state, INTENT_TICKET, 0.96)
            return state

        if _CANCEL_RE.match(message):
            state["inflow_type"] = INFLOW_CANCEL_FLOW
            state["flow_relation"] = "cancel"
            state["dialogue_act"] = DIALOGUE_ACT_REJECT
            state["self_contained_request"] = False
            state["continue_previous_task"] = True
            state["understanding_confidence"] = 0.95
            return self._apply_non_switch_inflow(state, active_flow, INFLOW_CANCEL_FLOW)

        state = self.inflow_understanding.execute(state)

        if not state.get("continue_previous_task"):
            if self._looks_out_of_business_scope(state):
                return self._build_domain_scope_state(state)

            unsupported_capability = self._find_unsupported_capability(state)
            if unsupported_capability is not None:
                return self._build_unsupported_capability_state(state, unsupported_capability)

        if self._is_switch_request(state, active_flow):
            state["inflow_type"] = INFLOW_SWITCH_FLOW
            state["flow_relation"] = "switch"
            state["dialogue_act"] = DIALOGUE_ACT_SWITCH_TOPIC
            state["continue_previous_task"] = False
            state["self_contained_request"] = True
            return self._build_switch_state(
                state,
                active_flow=active_flow,
                current_step=current_step,
                expected_user_acts=expected_user_acts,
            )

        if state.get("continue_previous_task"):
            inflow_type = INFLOW_CORRECTION if state.get("dialogue_act") == "correct" else INFLOW_VALID_CURRENT_INPUT
            return self._apply_non_switch_inflow(state, active_flow, inflow_type)

        if (
            state.get("self_contained_request")
            and state.get("domain_intent") == active_flow
            and active_flow
        ):
            state["continue_previous_task"] = True
            inflow_type = INFLOW_CORRECTION if state.get("dialogue_act") == "correct" else INFLOW_VALID_CURRENT_INPUT
            return self._apply_non_switch_inflow(state, active_flow, inflow_type)

        llm_result = self._infer_inflow_with_llm(
            state,
            active_flow=active_flow,
            current_step=current_step,
            expected_user_acts=expected_user_acts,
            rule_guess=None,
        )
        if llm_result:
            inflow_type = llm_result["inflow_type"]
            state["inflow_type"] = inflow_type
            state["domain_intent"] = state.get("domain_intent") or llm_result.get("domain_intent")
            state["continue_previous_task"] = llm_result.get("continue_previous_task", state.get("continue_previous_task"))
            state["need_clarification"] = llm_result["need_clarification"]
            if llm_result.get("confidence") is not None:
                state["understanding_confidence"] = llm_result["confidence"]

            if inflow_type == INFLOW_SWITCH_FLOW:
                state["self_contained_request"] = True
                state["continue_previous_task"] = False
                state["dialogue_act"] = DIALOGUE_ACT_SWITCH_TOPIC
                state["flow_relation"] = "switch"
                return self._build_switch_state(
                    state,
                    active_flow=active_flow,
                    current_step=current_step,
                    expected_user_acts=expected_user_acts,
                )

            if inflow_type == INFLOW_HANDOFF:
                state["intent"] = INTENT_TICKET
                state["domain_intent"] = INTENT_TICKET
                state["confidence"] = max(float(state.get("understanding_confidence") or 0.0), 0.9)
                self._append_preselected_intent(state, INTENT_TICKET, float(state["confidence"]))
                state["flow_relation"] = "handoff"
                return state

            if inflow_type in {INFLOW_IRRELEVANT, INFLOW_UNKNOWN, INFLOW_RELATED_QUESTION}:
                switched = self._try_soft_switch_to_global_intent(
                    state,
                    active_flow=active_flow,
                    current_step=current_step,
                    expected_user_acts=expected_user_acts,
                )
                if switched is not None:
                    return switched

            return self._apply_non_switch_inflow(state, active_flow, inflow_type)

        if not self._looks_like_ambiguous_reference(message):
            switched = self._try_soft_switch_to_global_intent(
                state,
                active_flow=active_flow,
                current_step=current_step,
                expected_user_acts=expected_user_acts,
                min_confidence=0.74,
            )
            if switched is not None:
                return switched

        if _BLOCKER_RE.search(message):
            return self._apply_non_switch_inflow(state, active_flow, INFLOW_RELATED_BLOCKER)
        if message.endswith(("?", "？")):
            return self._apply_non_switch_inflow(state, active_flow, INFLOW_RELATED_QUESTION)
        if _SMALLTALK_RE.match(message):
            return self._apply_non_switch_inflow(state, active_flow, INFLOW_IRRELEVANT)

        state["understanding_confidence"] = float(state.get("understanding_confidence") or 0.3)
        return self._apply_non_switch_inflow(state, active_flow, INFLOW_UNKNOWN)

    def execute(self, state: ConversationState) -> ConversationState:
        self._reset_entry_fields(state)

        has_active_flow = self._has_active_flow(state)
        active_flow, current_step = self._resolve_active_flow(state)
        expected_user_acts = self._derive_expected_user_acts(state, current_step)

        state["has_active_flow"] = has_active_flow
        state["active_flow"] = active_flow
        state["current_step"] = current_step
        state["expected_user_acts"] = expected_user_acts

        if not has_active_flow:
            if self._looks_out_of_business_scope(state):
                return self._build_domain_scope_state(state)

            unsupported_capability = self._find_unsupported_capability(state)
            if unsupported_capability is not None:
                return self._build_unsupported_capability_state(state, unsupported_capability)

            return self._run_global_intent(state)

        return self._run_inflow_classifier(state)
