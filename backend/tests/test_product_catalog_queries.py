from __future__ import annotations

import pytest

from ai_module.core.constants import INTENT_PRODUCT_INQUIRY
from ai_module.core.domain_scope import has_business_signal, looks_out_of_business_scope
from ai_module.core.nodes.skills import product_inquiry_node as product_inquiry_module
from ai_module.core.nodes.skills.product_inquiry_node import ProductInquiryNode
from ai_module.core.nodes.understanding.intent_node import IntentRecognitionNode
from ai_module.core.nodes.understanding.message_entry_node import MessageEntryNode


CATALOG_MESSAGES = [
    "我想购买一些商品",
    "你都有什么商品",
    "商城里面有哪些商品",
    "你都卖什么茶",
    "系统有什么茶",
    "你们提供哪些茶叶",
    "茶品有哪些",
]


def _make_state(message: str, **overrides):
    state = {
        "user_message": message,
        "user_id": "u1",
        "session_id": "s1",
        "attachments": [],
        "conversation_history": [],
        "user_profile": {},
        "last_intent": None,
        "last_quick_actions": [],
        "active_task": None,
        "task_stack": [],
        "pending_question": None,
        "pending_action": None,
        "intent_history": [],
        "conversation_summary": "",
        "purchase_flow": None,
        "aftersales_flow": None,
    }
    state.update(overrides)
    return state


@pytest.mark.parametrize("message", CATALOG_MESSAGES)
def test_catalog_messages_are_in_scope_and_match_product_inquiry(message):
    assert has_business_signal(message)
    assert not looks_out_of_business_scope(message)
    intent, confidence = IntentRecognitionNode()._match_by_rules(message)
    assert intent == INTENT_PRODUCT_INQUIRY
    assert confidence >= 0.95


@pytest.mark.parametrize("message", CATALOG_MESSAGES)
def test_catalog_messages_route_to_product_inquiry_without_active_flow(message):
    result = MessageEntryNode().execute(_make_state(message))

    assert result["intent"] == INTENT_PRODUCT_INQUIRY
    assert result["domain_intent"] == INTENT_PRODUCT_INQUIRY
    assert result.get("skill_route") is None


def test_catalog_message_switches_from_stale_active_qa_flow():
    state = _make_state(
        "你都卖什么茶",
        last_intent="问答",
        active_task={"intent": "问答", "status": "awaiting_user"},
        pending_action="answer_follow_up",
        pending_question="还想了解什么？",
    )

    result = MessageEntryNode().execute(state)

    assert result["intent"] == INTENT_PRODUCT_INQUIRY
    assert result["domain_intent"] == INTENT_PRODUCT_INQUIRY
    assert result["inflow_type"] == "switch_flow"
    assert result["flow_relation"] == "switch"


def test_catalog_message_reuses_same_active_product_flow_without_llm():
    state = _make_state(
        "\u7cfb\u7edf\u6709\u4ec0\u4e48\u8336",
        last_intent=INTENT_PRODUCT_INQUIRY,
        active_task={"intent": INTENT_PRODUCT_INQUIRY, "status": "awaiting_user"},
        pending_action="answer_follow_up",
        pending_question="catalog follow up",
    )

    result = MessageEntryNode().execute(state)

    assert result["intent"] == INTENT_PRODUCT_INQUIRY
    assert result["domain_intent"] == INTENT_PRODUCT_INQUIRY
    assert result["inflow_type"] == "valid_current_input"
    assert result["flow_relation"] == "continue"


class _FakeSearchTool:
    def __init__(self):
        self.calls = []

    def invoke(self, arguments):
        self.calls.append(arguments)
        return {
            "success": True,
            "products": [
                {
                    "id": "tea-1",
                    "title": "西湖龙井·明前特级",
                    "price": 298,
                    "rating": 4.9,
                    "sales_count": 128,
                    "tech_stack": ["绿茶", "鲜爽", "杭州"],
                    "description": "豆香清雅，适合日常自饮。",
                },
                {
                    "id": "tea-2",
                    "title": "安溪铁观音·兰花香",
                    "price": 188,
                    "rating": 4.8,
                    "sales_count": 96,
                    "tech_stack": ["乌龙茶", "兰花香"],
                    "description": "兰花香明显，回甘持久。",
                },
            ],
        }


def test_product_inquiry_queries_real_catalog_and_builds_product_cards(monkeypatch):
    fake_search = _FakeSearchTool()
    monkeypatch.setattr(product_inquiry_module, "_get_search_products_tool", lambda: fake_search)
    state = {"user_message": "商城里面有哪些商品", "tool_result": None}

    result = ProductInquiryNode().execute(state)

    assert fake_search.calls == [{"keyword": ""}]
    assert "西湖龙井·明前特级" in result["response"]
    assert "安溪铁观音·兰花香" in result["response"]
    assert "这个确实得看具体情况" not in result["response"]
    product_actions = [action for action in result["quick_actions"] if action["type"] == "product"]
    assert [action["data"]["product_id"] for action in product_actions] == ["tea-1", "tea-2"]
    assert result["recommended_products"] == ["tea-1", "tea-2"]
