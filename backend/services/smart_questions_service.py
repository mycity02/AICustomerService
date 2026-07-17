"""Smart quick-question suggestions for the chat welcome card."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate

from config import init_chat_model

MAX_QUESTION_COUNT = 3

QUESTION_BANK: List[Dict[str, str]] = [
    {
        "topic": "logistics",
        "label": "查看物流",
        "question": "帮我查看物流信息",
        "icon": "package",
    },
    {
        "topic": "order_issue",
        "label": "订单有问题",
        "question": "我的订单有问题",
        "icon": "package",
    },
    {
        "topic": "refund",
        "label": "申请退款",
        "question": "如何申请退款？",
        "icon": "refund",
    },
    {
        "topic": "seller_contact",
        "label": "联系卖家",
        "question": "如何联系卖家？",
        "icon": "help",
    },
    {
        "topic": "usage_help",
        "label": "使用帮助",
        "question": "使用遇到问题怎么办？",
        "icon": "help",
    },
    {
        "topic": "purchase_help",
        "label": "购买咨询",
        "question": "如何购买作品？",
        "icon": "cart",
    },
]

TOPIC_INDEX = {item["topic"]: item for item in QUESTION_BANK}

SMART_QUESTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是电商客服欢迎卡片的文案助手。

你的任务不是决定 UI，也不是决定按钮动作。你只负责生成 3 条适合直接点击发送的中文问题文本候选。

硬性要求：
1. 只围绕当前系统已支持的客服场景：订单问题、物流、退款、联系卖家、使用帮助、购买咨询。
2. 不能生成域外话题，也不能生成未支持业务，例如购物车、优惠券、发票、积分、旅游、闲聊等。
3. 必须输出 JSON 对象，不要输出 markdown，不要解释。
4. questions 必须恰好 3 条。
5. 每条都使用这个结构：{"label":"...", "question":"...", "topic":"..."}。
6. topic 只能是：logistics、order_issue、refund、seller_contact、usage_help、purchase_help。
7. label 要短，适合按钮展示，2 到 8 个中文字符。
8. question 要像用户会直接发给客服的话，8 到 18 个中文字符。
9. 三条内容不能重复，优先推荐和用户上下文最相关的内容。

输出示例：
{"questions":[
  {"label":"查看物流","question":"帮我查看物流信息","topic":"logistics"},
  {"label":"申请退款","question":"如何申请退款？","topic":"refund"},
  {"label":"联系卖家","question":"如何联系卖家？","topic":"seller_contact"}
]}""",
        ),
        (
            "human",
            """用户上下文：
{context}

请返回 3 条候选问题。""",
        ),
    ]
)


class SmartQuestionsService:
    """Build smart quick questions for the welcome card."""

    def __init__(self):
        self.llm = init_chat_model(temperature=0.4, max_tokens=300)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 3600

    def _get_cache_key(self, user_id: str, context: str) -> str:
        context_hash = hashlib.md5(context.encode("utf-8")).hexdigest()[:8]
        return f"smart_questions:{user_id}:{context_hash}"

    def _get_cached_questions(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        cached = self._cache.get(cache_key)
        if not cached:
            return None
        if datetime.now() >= cached["expires_at"]:
            self._cache.pop(cache_key, None)
            return None
        return cached["questions"]

    def _set_cached_questions(self, cache_key: str, questions: List[Dict[str, Any]]) -> None:
        self._cache[cache_key] = {
            "questions": questions,
            "expires_at": datetime.now() + timedelta(seconds=self._cache_ttl),
        }

    async def generate_smart_questions(
        self,
        user_id: str,
        user_profile: Dict[str, Any],
        recent_orders: List[Dict[str, Any]] | None = None,
        browsing_history: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        context = self._build_user_context(user_profile, recent_orders, browsing_history)
        cache_key = self._get_cache_key(user_id, context)
        cached_questions = self._get_cached_questions(cache_key)
        if cached_questions:
            return cached_questions

        try:
            response = await self.llm.ainvoke(SMART_QUESTION_PROMPT.format_messages(context=context))
            raw_questions = self._extract_questions(response.content)
            questions = self._normalize_questions(raw_questions, recent_orders)
        except Exception:
            questions = self.get_rule_based_questions(recent_orders)

        self._set_cached_questions(cache_key, questions)
        return questions

    def _extract_questions(self, content: Any) -> List[Dict[str, Any]]:
        text = getattr(content, "content", content)
        if not isinstance(text, str):
            raise ValueError("smart questions response must be a string")

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        if not cleaned.startswith("{"):
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if match:
                cleaned = match.group(0)

        payload = json.loads(cleaned)
        questions = payload.get("questions")
        if not isinstance(questions, list):
            raise ValueError("smart questions payload must contain a questions list")
        return questions

    def _normalize_questions(
        self,
        raw_questions: List[Dict[str, Any]],
        recent_orders: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        seen_questions: set[str] = set()

        for item in raw_questions:
            if not isinstance(item, dict):
                continue

            topic = str(item.get("topic", "")).strip()
            template = TOPIC_INDEX.get(topic)
            if template is None:
                continue

            label = self._clean_text(item.get("label")) or template["label"]
            question = self._clean_text(item.get("question")) or template["question"]
            if not question:
                continue

            normalized_key = re.sub(r"\s+", "", question)
            if normalized_key in seen_questions:
                continue
            seen_questions.add(normalized_key)

            normalized.append(
                {
                    "type": "button",
                    "label": label[:8],
                    "action": "send_question",
                    "data": {"question": question[:18]},
                    "icon": template["icon"],
                }
            )
            if len(normalized) >= MAX_QUESTION_COUNT:
                break

        if len(normalized) < MAX_QUESTION_COUNT:
            for item in self.get_rule_based_questions(recent_orders):
                key = re.sub(r"\s+", "", item["data"]["question"])
                if key in seen_questions:
                    continue
                seen_questions.add(key)
                normalized.append(item)
                if len(normalized) >= MAX_QUESTION_COUNT:
                    break

        return normalized[:MAX_QUESTION_COUNT]

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        text = re.sub(r"\s+", " ", text)
        text = text.replace('"', "").replace("'", "")
        return text

    def _build_user_context(
        self,
        user_profile: Dict[str, Any],
        recent_orders: List[Dict[str, Any]] | None = None,
        browsing_history: List[Dict[str, Any]] | None = None,
    ) -> str:
        context_parts: List[str] = []

        if user_profile:
            interests = user_profile.get("interests", [])
            if interests:
                context_parts.append(f"用户兴趣: {', '.join(map(str, interests))}")

            preferences = user_profile.get("preferences", {})
            if preferences:
                context_parts.append(f"用户偏好: {json.dumps(preferences, ensure_ascii=False)}")

        if recent_orders:
            order_info: List[str] = []
            for order in recent_orders[:3]:
                status = str(order.get("status", "")).strip()
                product_name = str(order.get("product_name", "")).strip()
                if status == "shipped" and product_name:
                    order_info.append(f"待收货订单: {product_name}")
                elif status == "completed" and product_name:
                    order_info.append(f"已完成订单: {product_name}")
                elif status == "pending_payment" and product_name:
                    order_info.append(f"待支付订单: {product_name}")
            if order_info:
                context_parts.append("订单信息:\n" + "\n".join(order_info))

        if browsing_history:
            viewed_products: List[str] = []
            for item in browsing_history[:5]:
                product_name = str(item.get("product_name", "")).strip()
                tech_stack = item.get("tech_stack", []) or []
                if product_name:
                    tech_text = ", ".join(map(str, tech_stack[:4]))
                    viewed_products.append(f"{product_name} ({tech_text})" if tech_text else product_name)
            if viewed_products:
                context_parts.append("浏览记录:\n" + "\n".join(viewed_products))

        if not context_parts:
            context_parts.append("新用户，没有历史订单和浏览记录。")

        return "\n\n".join(context_parts)

    def get_rule_based_questions(
        self,
        recent_orders: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        questions: List[Dict[str, Any]] = []
        used_topics: set[str] = set()

        if recent_orders:
            for order in recent_orders[:3]:
                if order.get("status") == "shipped":
                    logistics = TOPIC_INDEX["logistics"]
                    questions.append(
                        {
                            "type": "button",
                            "label": logistics["label"],
                            "action": "send_question",
                            "data": {"question": logistics["question"]},
                            "icon": logistics["icon"],
                        }
                    )
                    used_topics.add("logistics")
                    break

        for item in QUESTION_BANK:
            if item["topic"] in used_topics:
                continue
            questions.append(
                {
                    "type": "button",
                    "label": item["label"],
                    "action": "send_question",
                    "data": {"question": item["question"]},
                    "icon": item["icon"],
                }
            )
            if len(questions) >= MAX_QUESTION_COUNT:
                break

        return questions[:MAX_QUESTION_COUNT]

    def _get_rule_based_questions(
        self,
        recent_orders: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        return self.get_rule_based_questions(recent_orders)

    def get_default_questions(self) -> List[Dict[str, Any]]:
        return self.get_rule_based_questions()

    def _get_default_questions(self) -> List[Dict[str, Any]]:
        return self.get_default_questions()


smart_questions_service = SmartQuestionsService()
