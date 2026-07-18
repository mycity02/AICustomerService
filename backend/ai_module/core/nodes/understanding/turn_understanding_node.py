"""多轮对话延续场景下的轮次理解节点。

它和传统业务意图识别不是一回事。
这个节点要回答的是：
“用户这一轮在做什么？这句话是否足够完整，可以单独开启一个新任务？”

例如：确认、拒绝、补充槽位、选择上一轮结果、恢复挂起任务，
或者明确发起一个全新的请求。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.memory_builder import MemoryContextBuilder
from ai_module.core.constants import (
    DEFAULT_INTENT_RULES,
    DIALOGUE_ACT_CONFIRM,
    DIALOGUE_ACT_CORRECT,
    DIALOGUE_ACT_NEW_REQUEST,
    DIALOGUE_ACT_PROVIDE_SLOT,
    DIALOGUE_ACT_REJECT,
    DIALOGUE_ACT_RESUME_TASK,
    DIALOGUE_ACT_SELECT_ITEM,
    DIALOGUE_ACT_SWITCH_TOPIC,
    DIALOGUE_ACT_UNCLEAR,
    INTENT_QA,
)
from ai_module.core.state import ConversationState

logger = logging.getLogger(__name__)

_CONFIRM_RE = re.compile(
    r"^(需要|好的?|行|可以|要|是的|嗯+|没问题|好啊|可以的|安排|继续吧)$",
    re.IGNORECASE,
)
_REJECT_RE = re.compile(
    r"^(不要了?|不用了?|算了|不需要|不是|不行|先不用|不要这个)$",
    re.IGNORECASE,
)
_NEGATIVE_FEEDBACK_RE = re.compile(
    r"(都不喜欢|不喜欢这些|不喜欢这几个|不满意这些|不满意这几个|都不满意|都不合适|没有喜欢的|没一个喜欢|一个都不喜欢|这些都不行|这几个都不行|都不太行|都一般|都不想要|这个不太行|这个不合适|这个我不喜欢)",
    re.IGNORECASE,
)
_CORRECT_RE = re.compile(r"(不是这个意思|不是这个|不对|我说的是|改成|不是.*是)")
_SWITCH_TOPIC_RE = re.compile(r"^(先|顺便|另外|对了|那先)")
_RESUME_TASK_RE = re.compile(r"^(继续刚才|回到刚才|继续上一个|回到上一个|继续刚刚|回到刚刚)")
_SELECT_ITEM_RE = re.compile(r"^第(?P<rank>[一二三四五六七八九十两\d]+)个(?:茶品|商品|订单)?$")
_REQUEST_FRAME_RE = re.compile(
    r"(帮我|帮忙|给我|找(?:一|几|下)?|查(?:一|下)?|看看|想要|我想|有没有|请推荐|介绍一下|怎么|如何|能不能|可不可以)",
    re.IGNORECASE,
)

_CHINESE_NUMERALS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


class TurnUnderstandingNode(BaseNode):
    """识别确认、补槽、选择等对话动作。

    在骨架设计中，它是对话层真正的语义入口，
    负责把原始用户输入转换成后续节点可以消费的结构化信号。
    """

    LANGUAGE_KEYWORDS = {
        "java": "Java",
        "spring boot": "Spring Boot",
        "springcloud": "Spring Cloud",
        "spring cloud": "Spring Cloud",
        "vue": "Vue",
        "python": "Python",
        "react": "React",
        "node": "Node.js",
        "php": "PHP",
        "c#": "C#",
        "微信小程序": "微信小程序",
    }
    _LLM_ELIGIBLE_ACTS = {
        DIALOGUE_ACT_NEW_REQUEST,
        DIALOGUE_ACT_PROVIDE_SLOT,
        DIALOGUE_ACT_SWITCH_TOPIC,
        DIALOGUE_ACT_UNCLEAR,
    }

    def __init__(self, llm=None, runtime=None):
        super().__init__(llm=llm, runtime=runtime)
        self.memory_builder = MemoryContextBuilder()

    def _assistant_requires_follow_up(self, assistant_message: str) -> bool:
        if not assistant_message:
            return False

        normalized = assistant_message.strip()
        if normalized.endswith(("?", "？")):
            return True

        return any(
            keyword in normalized
            for keyword in (
                "吗",
                "呢",
                "要不要",
                "是否",
                "请问",
                "需要我",
                "可以帮你",
                "要我",
                "继续吗",
                "告诉我",
                "再告诉我",
                "说一下",
                "补充一下",
            )
        )

    def _looks_like_result_rejection(self, message: str) -> bool:
        normalized = message.strip()
        if not normalized:
            return False
        return bool(_NEGATIVE_FEEDBACK_RE.search(normalized))

    def _extract_slot_updates(self, message: str) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        normalized = message.lower()

        budget_match = re.search(r"(预算\s*)?(?P<amount>\d{2,5})\s*(元|块|以内|以下|左右)", message)
        if budget_match:
            amount = int(budget_match.group("amount"))
            if any(token in message for token in ("以内", "以下", "不超过", "最多")):
                updates["budget_max"] = amount
            elif any(token in message for token in ("左右", "上下")):
                updates["budget_target"] = amount
            elif "预算" in message or "元" in message or "块" in message:
                updates["budget_target"] = amount

        for keyword, language in self.LANGUAGE_KEYWORDS.items():
            if keyword in normalized:
                updates["language"] = language
                break

        if any(token in message for token in ("简单点", "简单一些", "别太难", "容易一点", "基础")):
            updates["difficulty"] = "easy"
        elif any(token in message for token in ("中等", "适中")):
            updates["difficulty"] = "medium"
        elif any(token in message for token in ("难一点", "复杂", "高级")):
            updates["difficulty"] = "hard"

        if any(token in message for token in ("便宜点", "再便宜点", "便宜一点")):
            updates["price_preference"] = "lower"
        elif any(token in message for token in ("贵一点", "高端一点")):
            updates["price_preference"] = "higher"

        return updates

    def _get_intent_rules(self) -> Dict[str, List[str]]:
        if self.runtime is None:
            return {intent: list(keywords) for intent, keywords in DEFAULT_INTENT_RULES.items()}
        return self.runtime.get_intent_rules()

    def _match_explicit_intent_signal(self, message: str) -> Optional[str]:
        normalized = message.lower()
        scores: Dict[str, tuple[int, int, int]] = {}
        for intent, keywords in self._get_intent_rules().items():
            if intent == INTENT_QA:
                continue

            matched = [keyword for keyword in keywords if keyword and keyword.lower() in normalized]
            if not matched:
                continue

            scores[intent] = (
                len(matched),
                max(len(keyword) for keyword in matched),
                sum(len(keyword) for keyword in matched),
            )

        if not scores:
            return None

        return max(scores.items(), key=lambda item: item[1])[0]

    def _looks_like_explicit_request(self, message: str) -> bool:
        return bool(_REQUEST_FRAME_RE.search(message) or self._match_explicit_intent_signal(message))

    def _get_valid_intents(self) -> List[str]:
        if self.runtime is None:
            return list(DEFAULT_INTENT_RULES.keys())
        return self.runtime.get_intent_labels()

    def _build_prompt_template(self) -> ChatPromptTemplate:
        if self.runtime is not None:
            configured = self.runtime.get_prompt("turn_understanding_system_prompt")
            if configured:
                return ChatPromptTemplate.from_messages(
                    [("system", configured), ("human", "{input_payload}")]
                )

        system_prompt = """你是对话理解器，不直接回复用户。
你只负责把当前用户输入解析为 JSON，不要输出解释，不要输出 markdown。

输出字段：
- dialogue_act: 必须是 new_request/confirm/reject/provide_slot/select_item/correct/switch_topic/resume_task/unclear 之一
- domain_intent: 必须是给定业务标签之一；如果无法确定就填 null
- self_contained_request: 布尔值，表示这句话本身是否足以作为一个新的独立请求
- continue_previous_task: 布尔值，表示这句话是否明显是在继续上一轮任务
- need_clarification: 布尔值，表示这句话是否过于模糊，系统应该先澄清
- confidence: 0 到 1 之间的小数
- slot_updates: 对象，可提取 budget_max、budget_target、language、difficulty、price_preference，提取不到就输出 {{}}

决策原则：
1. 如果当前句子本身已经表达完整需求，即使历史里有别的任务，也优先视为 self_contained_request=true。
2. 只有在当前句子明显依赖上一轮问题时，才把 continue_previous_task 设为 true。
3. 如果句子既像新请求又像补充条件，优先判断它是否能脱离上下文独立成立。
4. 不要编造 intent；不确定时 domain_intent 填 null。
5. 只输出一个 JSON 对象。"""
        return ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input_payload}")])

    def _format_recent_history(self, history: List[Dict[str, Any]], limit: int = 3) -> str:
        return self.memory_builder.build_recent_history_text(history, limit=max(limit, 6))

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

    def _normalize_llm_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        valid_dialogue_acts = {
            DIALOGUE_ACT_NEW_REQUEST,
            DIALOGUE_ACT_CONFIRM,
            DIALOGUE_ACT_REJECT,
            DIALOGUE_ACT_PROVIDE_SLOT,
            DIALOGUE_ACT_SELECT_ITEM,
            DIALOGUE_ACT_CORRECT,
            DIALOGUE_ACT_SWITCH_TOPIC,
            DIALOGUE_ACT_RESUME_TASK,
            DIALOGUE_ACT_UNCLEAR,
        }
        valid_intents = set(self._get_valid_intents())

        dialogue_act = payload.get("dialogue_act")
        if dialogue_act not in valid_dialogue_acts:
            dialogue_act = None

        domain_intent = payload.get("domain_intent")
        if domain_intent not in valid_intents:
            domain_intent = None

        slot_updates = payload.get("slot_updates")
        if not isinstance(slot_updates, dict):
            slot_updates = {}

        confidence = payload.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = None

        return {
            "dialogue_act": dialogue_act,
            "domain_intent": domain_intent,
            "self_contained_request": bool(payload.get("self_contained_request", False)),
            "continue_previous_task": bool(payload.get("continue_previous_task", False)),
            "need_clarification": bool(payload.get("need_clarification", False)),
            "confidence": confidence,
            "slot_updates": slot_updates,
        }

    def _should_use_llm(
        self,
        *,
        message: str,
        dialogue_act: str,
        domain_intent: Optional[str],
        self_contained_request: bool,
        continue_previous_task: bool,
        need_clarification: bool,
    ) -> bool:
        if self.llm is None:
            return False
        if len(message.strip()) < 3:
            return False
        if dialogue_act not in self._LLM_ELIGIBLE_ACTS:
            return False
        if domain_intent is None:
            return True
        if need_clarification:
            return True
        if dialogue_act == DIALOGUE_ACT_NEW_REQUEST and not self_contained_request:
            return True
        if dialogue_act == DIALOGUE_ACT_PROVIDE_SLOT and not continue_previous_task:
            return True
        return False

    def _infer_with_llm(
        self,
        state: ConversationState,
        *,
        message: str,
        dialogue_act: str,
        domain_intent: Optional[str],
        self_contained_request: bool,
        continue_previous_task: bool,
        need_clarification: bool,
        slot_updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        try:
            prompt = self._build_prompt_template()
            payload = {
                "message": message,
                "last_intent": state.get("last_intent"),
                "active_task_intent": (state.get("active_task") or {}).get("intent"),
                "pending_action": state.get("pending_action"),
                "pending_question": state.get("pending_question"),
                "last_quick_actions_count": len(state.get("last_quick_actions") or []),
                "recent_history": self._format_recent_history(state.get("conversation_history") or []),
                "task_snapshot": self.memory_builder.build_task_snapshot_text(state),
                "rule_guess": {
                    "dialogue_act": dialogue_act,
                    "domain_intent": domain_intent,
                    "self_contained_request": self_contained_request,
                    "continue_previous_task": continue_previous_task,
                    "need_clarification": need_clarification,
                    "slot_updates": slot_updates,
                },
                "valid_intents": self._get_valid_intents(),
            }
            response = self.llm.invoke(
                prompt.format_messages(
                    input_payload=json.dumps(payload, ensure_ascii=False, indent=2)
                )
            )
            raw = response.content if hasattr(response, "content") else str(response)
            json_block = self._extract_json_block(raw)
            if not json_block:
                return None
            parsed = json.loads(json_block)
            if not isinstance(parsed, dict):
                return None
            return self._normalize_llm_result(parsed)
        except Exception as exc:
            logger.warning("Turn understanding LLM fallback failed: %s", exc)
            return None

    def _parse_rank(self, token: str) -> Optional[int]:
        if token.isdigit():
            value = int(token)
            return value if value > 0 else None

        if token == "十":
            return 10
        if len(token) == 2 and token[0] == "十" and token[1] in _CHINESE_NUMERALS:
            return 10 + _CHINESE_NUMERALS[token[1]]
        return _CHINESE_NUMERALS.get(token)

    def _resolve_reference(
        self,
        message: str,
        quick_actions: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        message = message.strip()

        if message == "最后一个" and quick_actions:
            selected_action = quick_actions[-1]
            return {
                "selection_index": len(quick_actions),
                "selected_action": selected_action,
                "selected_action_type": selected_action.get("type"),
            }

        match = _SELECT_ITEM_RE.match(message)
        if not match:
            return None

        rank = self._parse_rank(match.group("rank"))
        if rank is None:
            return {"selection_index": None}

        resolution: Dict[str, Any] = {"selection_index": rank}
        if 0 < rank <= len(quick_actions):
            selected_action = quick_actions[rank - 1]
            resolution.update(
                {
                    "selected_action": selected_action,
                    "selected_action_type": selected_action.get("type"),
                }
            )
        return resolution

    def _enrich_message_with_selection(
        self,
        message: str,
        reference_resolution: Dict[str, Any],
    ) -> str:
        selected_action = reference_resolution.get("selected_action")
        if not selected_action:
            return message

        index = reference_resolution.get("selection_index")
        action_type = selected_action.get("type")
        data = selected_action.get("data", {})
        index_label = f"第{index}个" if index else "刚才选中的"

        if action_type == "product":
            title = data.get("title") or data.get("product_name")
            if title:
                return f"{message}（我指上次推荐里的{index_label}款茶：{title}）"

        if action_type in {"order_card", "order_card_simple"}:
            order_no = data.get("order_no")
            if order_no:
                return f"{message}（我指订单 {order_no}）"

        label = selected_action.get("label")
        if label:
            return f"{message}（我指上次展示的操作：{label}）"

        return message

    def execute(self, state: ConversationState) -> ConversationState:
        message = (state.get("user_message") or "").strip()
        last_intent = state.get("last_intent")
        quick_actions = list(state.get("last_quick_actions") or [])
        history = state.get("conversation_history") or []
        last_assistant_message = history[-1].get("assistant", "") if history else ""
        active_task = state.get("active_task") or {}
        task_stack = list(state.get("task_stack") or [])
        has_pending_follow_up = bool(state.get("pending_question") or state.get("pending_action"))

        state["dialogue_act"] = DIALOGUE_ACT_NEW_REQUEST
        state["domain_intent"] = None
        state["self_contained_request"] = False
        state["continue_previous_task"] = False
        state["need_clarification"] = False
        state["understanding_confidence"] = None
        state["slot_updates"] = {}
        state["reference_resolution"] = None
        state["selected_quick_action"] = None

        if not message:
            state["dialogue_act"] = DIALOGUE_ACT_UNCLEAR
            state["need_clarification"] = True
            state["understanding_confidence"] = 0.2
            return state

        # 在决定对话动作前，先从原始文本里提取结构化线索。
        slot_updates = self._extract_slot_updates(message)
        reference_resolution = self._resolve_reference(message, quick_actions)
        explicit_intent = self._match_explicit_intent_signal(message)
        active_task_open = active_task.get("status") in {"active", "awaiting_user"}
        explicit_request = bool(_REQUEST_FRAME_RE.search(message) or explicit_intent)
        awaiting_follow_up = (
            has_pending_follow_up
            or self._assistant_requires_follow_up(last_assistant_message)
            or bool(quick_actions)
            or active_task_open
        )
        slot_follow_up = (
            bool(slot_updates)
            and bool(last_intent)
            and awaiting_follow_up
            and not explicit_request
        )

        if _CORRECT_RE.search(message):
            dialogue_act = DIALOGUE_ACT_CORRECT
        elif _RESUME_TASK_RE.match(message) and task_stack:
            dialogue_act = DIALOGUE_ACT_RESUME_TASK
        elif reference_resolution is not None:
            dialogue_act = DIALOGUE_ACT_SELECT_ITEM
        elif slot_follow_up:
            dialogue_act = DIALOGUE_ACT_PROVIDE_SLOT
        elif self._looks_like_result_rejection(message):
            dialogue_act = DIALOGUE_ACT_REJECT
        elif _CONFIRM_RE.match(message):
            dialogue_act = DIALOGUE_ACT_CONFIRM
        elif _REJECT_RE.match(message):
            dialogue_act = DIALOGUE_ACT_REJECT
        elif _SWITCH_TOPIC_RE.match(message):
            dialogue_act = DIALOGUE_ACT_SWITCH_TOPIC
        elif len(message) <= 2 and last_intent:
            dialogue_act = DIALOGUE_ACT_UNCLEAR
        else:
            dialogue_act = DIALOGUE_ACT_NEW_REQUEST

        # 短回复只有在上一轮明显留下未完成动作时，才算真正的任务延续。
        continue_previous_task = False
        if last_intent:
            if dialogue_act == DIALOGUE_ACT_PROVIDE_SLOT and slot_follow_up:
                continue_previous_task = True
            elif dialogue_act == DIALOGUE_ACT_SELECT_ITEM and awaiting_follow_up:
                continue_previous_task = True
            elif dialogue_act == DIALOGUE_ACT_CORRECT and (history or active_task_open):
                continue_previous_task = True
            elif dialogue_act in {DIALOGUE_ACT_CONFIRM, DIALOGUE_ACT_REJECT} and awaiting_follow_up:
                continue_previous_task = True
            elif dialogue_act == DIALOGUE_ACT_RESUME_TASK:
                continue_previous_task = True

        self_contained_request = False
        if dialogue_act == DIALOGUE_ACT_NEW_REQUEST:
            if explicit_request or explicit_intent:
                self_contained_request = True
            elif not last_intent:
                self_contained_request = True
            elif not awaiting_follow_up and len(message) >= 4:
                self_contained_request = True

        need_clarification = False
        if dialogue_act == DIALOGUE_ACT_UNCLEAR:
            need_clarification = True
        elif not self_contained_request and not continue_previous_task and len(message) <= 4 and not explicit_intent:
            need_clarification = True

        if need_clarification:
            understanding_confidence = 0.25
        elif dialogue_act in {DIALOGUE_ACT_CONFIRM, DIALOGUE_ACT_REJECT, DIALOGUE_ACT_SELECT_ITEM, DIALOGUE_ACT_RESUME_TASK}:
            understanding_confidence = 0.95 if continue_previous_task else 0.75
        elif dialogue_act == DIALOGUE_ACT_PROVIDE_SLOT:
            understanding_confidence = 0.9 if continue_previous_task else 0.65
        elif self_contained_request and explicit_intent:
            understanding_confidence = 0.92
        elif self_contained_request:
            understanding_confidence = 0.8
        else:
            understanding_confidence = 0.6

        llm_result = None
        if self._should_use_llm(
            message=message,
            dialogue_act=dialogue_act,
            domain_intent=explicit_intent,
            self_contained_request=self_contained_request,
            continue_previous_task=continue_previous_task,
            need_clarification=need_clarification,
        ):
            llm_result = self._infer_with_llm(
                state,
                message=message,
                dialogue_act=dialogue_act,
                domain_intent=explicit_intent,
                self_contained_request=self_contained_request,
                continue_previous_task=continue_previous_task,
                need_clarification=need_clarification,
                slot_updates=slot_updates,
            )

        if llm_result:
            llm_dialogue_act = llm_result.get("dialogue_act")
            if llm_dialogue_act and dialogue_act in self._LLM_ELIGIBLE_ACTS:
                dialogue_act = llm_dialogue_act

            explicit_intent = explicit_intent or llm_result.get("domain_intent")

            merged_slot_updates = dict(llm_result.get("slot_updates") or {})
            merged_slot_updates.update(slot_updates)
            slot_updates = merged_slot_updates

            if dialogue_act == DIALOGUE_ACT_NEW_REQUEST:
                self_contained_request = bool(llm_result.get("self_contained_request"))
                continue_previous_task = False
            elif dialogue_act in {DIALOGUE_ACT_PROVIDE_SLOT, DIALOGUE_ACT_CORRECT, DIALOGUE_ACT_SELECT_ITEM}:
                continue_previous_task = bool(llm_result.get("continue_previous_task", continue_previous_task))
                self_contained_request = False
            elif dialogue_act in {DIALOGUE_ACT_CONFIRM, DIALOGUE_ACT_REJECT, DIALOGUE_ACT_RESUME_TASK}:
                continue_previous_task = True if dialogue_act == DIALOGUE_ACT_RESUME_TASK else continue_previous_task
                self_contained_request = False
            else:
                self_contained_request = bool(llm_result.get("self_contained_request", self_contained_request))
                continue_previous_task = bool(llm_result.get("continue_previous_task", continue_previous_task))

            need_clarification = bool(llm_result.get("need_clarification", need_clarification))
            llm_confidence = llm_result.get("confidence")
            if llm_confidence is not None:
                understanding_confidence = llm_confidence

        if self_contained_request:
            continue_previous_task = False
        if dialogue_act == DIALOGUE_ACT_UNCLEAR:
            need_clarification = True

        state["dialogue_act"] = dialogue_act
        state["domain_intent"] = explicit_intent
        state["self_contained_request"] = self_contained_request
        state["continue_previous_task"] = continue_previous_task
        state["need_clarification"] = need_clarification
        state["understanding_confidence"] = understanding_confidence
        state["slot_updates"] = slot_updates
        state["reference_resolution"] = reference_resolution

        if reference_resolution and reference_resolution.get("selected_action"):
            state["selected_quick_action"] = reference_resolution["selected_action"]
            state["user_message"] = self._enrich_message_with_selection(message, reference_resolution)

        return state
