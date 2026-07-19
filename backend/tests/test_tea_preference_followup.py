from __future__ import annotations

from unittest.mock import MagicMock, patch

from ai_module.core.constants import INTENT_RECOMMEND
from ai_module.core.nodes.memory import save_context_node as save_context_module
from ai_module.core.nodes.memory.save_context_node import SaveContextNode
from ai_module.core.nodes.skills import product_inquiry_node as product_inquiry_module
from ai_module.core.nodes.skills.product_inquiry_node import ProductInquiryNode
from ai_module.core.nodes.understanding.message_entry_node import MessageEntryNode
from ai_module.core.nodes.understanding.turn_understanding_node import TurnUnderstandingNode
from ai_module.core.tea_preferences import extract_tea_preferences


def _conversation_state(message: str, **overrides):
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


def _open_recommendation_state(message: str, **overrides):
    state = _conversation_state(
        message,
        last_intent=INTENT_RECOMMEND,
        active_task={
            "id": "tea-task",
            "intent": INTENT_RECOMMEND,
            "status": "awaiting_user",
            "slots": {"brewing_constraint": "low_boiling_point", "location": "西藏"},
            "pending_action": "answer_follow_up",
            "pending_question": "您喜欢什么香型？",
        },
        pending_action="answer_follow_up",
        pending_question="您喜欢什么香型？",
        conversation_history=[
            {
                "user": "香型",
                "assistant": "您先说说喜欢的香型方向？😊",
            }
        ],
    )
    state.update(overrides)
    return state


def test_extracts_tea_domain_preferences():
    assert extract_tea_preferences("我在西藏，想要兰花香乌龙茶，买来送礼") == {
        "tea_category": "乌龙茶",
        "aroma": "兰花香",
        "usage": "送礼",
        "brewing_constraint": "low_boiling_point",
        "location": "西藏",
    }


def test_short_aroma_answer_continues_recommendation_and_becomes_slot():
    result = TurnUnderstandingNode().execute(_open_recommendation_state("兰花香"))

    assert result["dialogue_act"] == "provide_slot"
    assert result["continue_previous_task"] is True
    assert result["self_contained_request"] is False
    assert result["slot_updates"]["aroma"] == "兰花香"


def test_bare_tea_category_stays_in_open_recommendation_flow():
    result = MessageEntryNode().execute(_open_recommendation_state("乌龙茶"))

    assert result["intent"] == INTENT_RECOMMEND
    assert result["inflow_type"] == "valid_current_input"
    assert result["continue_previous_task"] is True
    assert result["slot_updates"]["tea_category"] == "乌龙茶"


def test_explicit_catalog_request_can_still_start_a_new_product_query():
    result = TurnUnderstandingNode().execute(_open_recommendation_state("帮我查一下乌龙茶"))

    assert result["dialogue_act"] == "new_request"
    assert result["self_contained_request"] is True
    assert result["continue_previous_task"] is False


def test_follow_up_question_with_trailing_emoji_keeps_task_open():
    state = {
        "session_id": "s1",
        "user_message": "香型",
        "response": "您先说说喜欢的香型方向？😊",
        "intent": INTENT_RECOMMEND,
        "intent_history": [],
        "quick_actions": [],
        "active_task": {
            "id": "tea-task",
            "intent": INTENT_RECOMMEND,
            "status": "active",
            "slots": {},
        },
        "task_stack": [],
    }
    cache = MagicMock()

    with patch.object(save_context_module, "redis_cache", cache):
        SaveContextNode().execute(state)

    assert state["pending_action"] == "answer_follow_up"
    assert state["pending_question"] == "您先说说喜欢的香型方向？😊"
    assert state["active_task"]["status"] == "awaiting_user"


class _FakeCatalogTool:
    name = "search_products"

    def __init__(self):
        self.calls = []

    def invoke(self, arguments):
        self.calls.append(arguments)
        return {
            "success": True,
            "products": [
                {
                    "id": "tea-oolong-1",
                    "title": "安溪铁观音清香型 250g",
                    "price": 168,
                    "rating": 4.78,
                    "sales_count": 287,
                    "tech_stack": ["福建安溪", "兰花香", "清鲜"],
                    "description": "兰花香清晰，茶汤清鲜。",
                }
            ],
        }


def test_standalone_aroma_query_searches_catalog_instead_of_returning_template(monkeypatch):
    tool = _FakeCatalogTool()
    monkeypatch.setattr(product_inquiry_module, "_get_search_products_tool", lambda: tool)

    result = ProductInquiryNode().execute({"user_message": "有兰花香的茶吗"})

    assert tool.calls == [{"keyword": "兰花香"}]
    assert "安溪铁观音清香型 250g" in result["response"]
    assert result["quick_actions"][0]["type"] == "product"


class _FakeAdvisorTool:
    name = "search_projects"

    def __init__(self):
        self.calls = []

    def invoke(self, arguments):
        self.calls.append(arguments)
        return {
            "success": True,
            "projects": [
                {
                    "id": "tea-oolong-1",
                    "title": "安溪铁观音清香型 250g",
                    "price": 168,
                    "rating": 4.78,
                    "sales_count": 287,
                    "tech_stack": ["福建安溪", "兰花香", "清鲜"],
                    "description": "兰花香清晰，茶汤清鲜。",
                }
            ],
        }


class _FakeRuntime:
    def __init__(self, tool):
        self.tool = tool

    def get_langchain_tools(self, group, execution_context=None):
        assert group == "topic_advisor"
        return [self.tool]


def test_recommendation_preference_update_uses_deterministic_inventory_search():
    # Older isolated-module tests replace services.function_tools globally.
    # Restore the one attribute required by the real service before importing it.
    import services.function_tools as function_tools

    if not hasattr(function_tools, "topic_advisor_tools"):
        function_tools.topic_advisor_tools = []
    from ai_module.core.workflows.topic_advisor.service import TopicAdvisorService

    tool = _FakeAdvisorTool()
    service = TopicAdvisorService(llm=None, runtime=_FakeRuntime(tool))
    state = _open_recommendation_state(
        "兰花香",
        intent=INTENT_RECOMMEND,
        continue_previous_task=True,
        slot_updates={"aroma": "兰花香"},
        execution_context=None,
    )

    result = service.run_agent(state)

    assert tool.calls == [{"keyword": "兰花香"}]
    assert "安溪铁观音清香型 250g" in result["response"]
    assert "高原" in result["response"]
    assert result["quick_actions"][0]["type"] == "product"
