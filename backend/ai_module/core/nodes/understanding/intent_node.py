"""意图识别节点。"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List

from langchain_core.prompts import ChatPromptTemplate

from config import settings

from ai_module.core.domain_scope import looks_like_catalog_query
from ai_module.core.constants import (
    CONTINUATION_DIALOGUE_ACTS,
    DEFAULT_INTENT_LABELS,
    DEFAULT_INTENT_RULES,
    DIALOGUE_ACT_NEW_REQUEST,
    DIALOGUE_ACT_RESUME_TASK,
    INTENT_DOCUMENT_ANALYSIS,
    INTENT_PRODUCT_INQUIRY,
    INTENT_QA,
    INTENT_RECOMMEND,
)
from ai_module.core.state import ConversationState
from ai_module.core.nodes.common.base import BaseNode

logger = logging.getLogger(__name__)

_SMALLTALK_RE = re.compile(
    r"^(你好|您好|hello|hi|在吗|哈喽|谢谢|感谢|好的|ok|再见|拜拜|早上好|晚上好)[!！。.?？]*$",
    re.IGNORECASE,
)


def _format_intent_history(intent_history: List[dict], max_entries: int) -> str:
    if not intent_history:
        return "（无历史记录）"

    recent = intent_history[-max_entries:]
    lines = []
    for entry in recent:
        intent = entry.get("intent", "未知")
        confidence = entry.get("confidence", 0.0)
        turn = entry.get("turn", 0)
        lines.append(f"第 {turn} 轮: {intent} (置信度 {confidence:.1f})")
    return "\n".join(lines)


def _find_fallback_intent(intent_history: List[dict], threshold: float) -> str | None:
    for entry in reversed(intent_history):
        if entry.get("confidence", 0.0) >= threshold:
            return entry["intent"]
    return None


class IntentRecognitionNode(BaseNode):
    """带运行时可配置提示词和标签的兜底意图分类器。"""

    _intent_cache: Dict[str, Dict[str, float | str]] = {}
    _cache_max_size = 1000

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)

    def _get_valid_intents(self) -> List[str]:
        if self.runtime is None:
            return list(DEFAULT_INTENT_LABELS)
        return self.runtime.get_intent_labels()

    def _get_intent_rules(self) -> Dict[str, List[str]]:
        if self.runtime is None:
            return {intent: list(keywords) for intent, keywords in DEFAULT_INTENT_RULES.items()}
        return self.runtime.get_intent_rules()

    def _get_examples(self) -> List[Dict[str, str]]:
        if self.runtime is None:
            return []
        return self.runtime.get_intent_examples()

    def _build_prompt_template(self, include_history: bool) -> ChatPromptTemplate:
        if self.runtime is not None:
            prompt_key = "intent_history_system_prompt" if include_history else "intent_system_prompt"
            configured = self.runtime.get_prompt(prompt_key)
            if configured:
                messages = [("system", configured), ("human", "{message}")]
                return ChatPromptTemplate.from_messages(messages)

        labels = self._get_valid_intents()
        rules = self._get_intent_rules()
        examples = self._get_examples()
        label_text = "|".join(labels)

        rule_lines = []
        for intent, keywords in rules.items():
            rule_lines.append(f"- {intent}: {', '.join(keywords[:10])}")

        example_lines = []
        for example in examples[:12]:
            user_message = example.get("message")
            intent = example.get("intent")
            if user_message and intent:
                example_lines.append(f'"{user_message}" -> {intent}')

        system_parts = [
            "只输出一个意图标签，不要输出任何其他内容。",
            "",
            f"可选标签：{label_text}",
        ]

        if include_history:
            system_parts.extend(
                [
                    "",
                    "最近的意图历史（从旧到新）：",
                    "{intent_history}",
                ]
            )

        system_parts.extend(
            [
                "",
                "规则：",
                "- 如果用户消息意图明确，直接输出对应标签。",
                "- 如果用户消息意图模糊，结合意图历史判断。",
                "- 如果用户明确切换话题，输出新的意图标签。",
                "",
                "关键词参考：",
                "\n".join(rule_lines),
            ]
        )

        if example_lines:
            system_parts.extend(["", "示例：", "\n".join(example_lines)])

        messages = [("system", "\n".join(system_parts)), ("human", "{message}")]
        return ChatPromptTemplate.from_messages(messages)

    def _match_by_rules(self, message: str) -> tuple[str, float] | None:
        text = message.strip()
        if _SMALLTALK_RE.match(text):
            logger.info("Rule matched smalltalk intent=qa")
            return INTENT_QA, 0.99

        if looks_like_catalog_query(text):
            logger.info("Rule matched catalog-query intent=product_inquiry")
            return INTENT_PRODUCT_INQUIRY, 0.98

        if re.search(r"(选茶|送礼茶|口粮茶|推荐.*茶)", text, re.IGNORECASE):
            logger.info("Rule matched tea-selection intent=recommend")
            return INTENT_RECOMMEND, 0.98

        if re.search(r"(找|要|想买|需要).*(茶|茶叶|茶品)", text, re.IGNORECASE):
            logger.info("Rule matched tea-seeking intent=recommend")
            return INTENT_RECOMMEND, 0.95

        message_lower = text.lower()
        for intent, keywords in self._get_intent_rules().items():
            for keyword in keywords:
                if keyword and keyword.lower() in message_lower:
                    logger.info("Rule matched intent=%s keyword=%s", intent, keyword)
                    return intent, 0.95
        return None

    def _append_intent_history(
        self,
        state: ConversationState,
        intent_history: List[dict],
        intent: str,
        confidence: float,
    ) -> None:
        turn = (intent_history[-1]["turn"] + 1) if intent_history else 1
        updated_history = intent_history + [
            {
                "intent": intent,
                "confidence": confidence,
                "turn": turn,
                "timestamp": datetime.now().isoformat(),
            }
        ]
        state["intent_history"] = updated_history

    def _build_cache_key(self, state: ConversationState, user_message: str) -> str:
        attachment_signature = []
        for attachment in state.get("attachments") or []:
            attachment_signature.append(
                {
                    "file_id": attachment.get("file_id"),
                    "file_type": attachment.get("file_type"),
                    "image_intent": attachment.get("image_intent"),
                }
            )

        history_signature = []
        for entry in (state.get("intent_history") or [])[-settings.INTENT_HISTORY_SIZE:]:
            history_signature.append(
                {
                    "intent": entry.get("intent"),
                    "confidence": round(float(entry.get("confidence", 0.0)), 2),
                }
            )

        payload = {
            "business_id": state.get("business_id") or "default",
            "message": user_message.lower(),
            "attachments": attachment_signature,
            "history": history_signature,
            "valid_intents": self._get_valid_intents(),
        }
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    def execute(self, state: ConversationState) -> ConversationState:
        valid_intents = set(self._get_valid_intents())
        has_attachments = bool(state.get("attachments"))
        user_message = state["user_message"].strip()
        intent_history = state.get("intent_history") or []
        last_intent = state.get("last_intent")
        dialogue_act = state.get("dialogue_act")
        task_stack = list(state.get("task_stack") or [])
        rule_result = self._match_by_rules(user_message)
        preselected_intent = state.get("intent")

        if preselected_intent in valid_intents:
            confidence = float(state.get("confidence") or state.get("understanding_confidence") or 0.9)
            state["intent"] = preselected_intent
            state["confidence"] = confidence
            self._append_intent_history(state, intent_history, preselected_intent, confidence)
            return state

        if dialogue_act == DIALOGUE_ACT_RESUME_TASK and task_stack:
            resumed_intent = task_stack[-1].get("intent")
            if resumed_intent in valid_intents:
                confidence = 0.9
                state["intent"] = resumed_intent
                state["confidence"] = confidence
                self._append_intent_history(state, intent_history, resumed_intent, confidence)
                return state

        if (
            state.get("continue_previous_task")
            and last_intent in valid_intents
            and dialogue_act in CONTINUATION_DIALOGUE_ACTS
        ):
            if rule_result and rule_result[0] in valid_intents and rule_result[0] != last_intent:
                state["continue_previous_task"] = False
                state["dialogue_act"] = DIALOGUE_ACT_NEW_REQUEST
                state["intent"] = rule_result[0]
                state["confidence"] = rule_result[1]
                self._append_intent_history(state, intent_history, rule_result[0], rule_result[1])
                return state

            confidence = 0.92
            state["intent"] = last_intent
            state["confidence"] = confidence
            self._append_intent_history(state, intent_history, last_intent, confidence)
            return state

        image_intents = []
        if has_attachments:
            for attachment in state["attachments"]:
                image_intent = attachment.get("image_intent")
                if image_intent and image_intent in valid_intents:
                    image_intents.append(image_intent)

        if image_intents:
            intent = Counter(image_intents).most_common(1)[0][0]
            confidence = 0.95
            state["intent"] = intent
            state["confidence"] = confidence
            self._append_intent_history(state, intent_history, intent, confidence)
            return state

        if has_attachments and len(user_message) < 20:
            state["intent"] = INTENT_DOCUMENT_ANALYSIS
            state["confidence"] = 0.95
            self._append_intent_history(state, intent_history, INTENT_DOCUMENT_ANALYSIS, 0.95)
            return state

        if rule_result:
            state["intent"] = rule_result[0]
            state["confidence"] = rule_result[1]
            self._append_intent_history(state, intent_history, rule_result[0], rule_result[1])
            return state

        cache_key = self._build_cache_key(state, user_message)
        cached = self._intent_cache.get(cache_key)
        if cached:
            state["intent"] = cached["intent"]
            state["confidence"] = cached["confidence"]
            self._append_intent_history(
                state,
                intent_history,
                cached["intent"],
                cached["confidence"],
            )
            return state

        try:
            template = self._build_prompt_template(include_history=bool(intent_history))
            if intent_history:
                messages = template.format_messages(
                    intent_history=_format_intent_history(intent_history, settings.INTENT_HISTORY_SIZE),
                    message=user_message[:200],
                )
            else:
                messages = template.format_messages(message=user_message[:200])

            response = self.llm.invoke(messages)
            raw = response.content.strip().strip("\"'")

            intent = INTENT_QA
            for valid in self._get_valid_intents():
                if valid in raw:
                    intent = valid
                    break

            confidence = 0.9
            state["intent"] = intent
            state["confidence"] = confidence

            if confidence < settings.INTENT_FALLBACK_THRESHOLD and intent_history:
                fallback_intent = _find_fallback_intent(
                    intent_history,
                    settings.INTENT_FALLBACK_THRESHOLD,
                )
                if fallback_intent:
                    state["intent"] = fallback_intent
        except Exception as exc:
            logger.warning("Intent recognition failed, falling back to QA: %s", exc)
            state["intent"] = INTENT_QA
            state["confidence"] = 0.5

        self._append_intent_history(
            state,
            intent_history,
            state["intent"],
            state["confidence"],
        )

        if len(self._intent_cache) >= self._cache_max_size:
            keys_to_remove = list(self._intent_cache.keys())[: self._cache_max_size // 2]
            for key in keys_to_remove:
                del self._intent_cache[key]

        self._intent_cache[cache_key] = {
            "intent": state["intent"],
            "confidence": state["confidence"],
        }
        return state
