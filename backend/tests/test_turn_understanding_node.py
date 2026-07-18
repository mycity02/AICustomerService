from unittest.mock import MagicMock

import pytest
from ai_module.core.nodes.understanding.turn_understanding_node import TurnUnderstandingNode


def _make_state(message: str, **overrides):
    state = {
        "user_message": message,
        "conversation_history": [],
        "last_intent": None,
        "last_quick_actions": [],
    }
    state.update(overrides)
    return state


class TestTurnUnderstandingNode:
    def _make_mock_llm(self, content: str):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = content
        mock_llm.invoke.return_value = mock_response
        return mock_llm
    def test_confirm_reply_continues_previous_task(self):
        node = TurnUnderstandingNode()
        state = _make_state(
            "需要",
            last_intent="推荐",
            conversation_history=[
                {"user": "帮我推荐 Java 项目", "assistant": "需要我帮你搜索 800 元左右的 Java 项目吗？"}
            ],
        )

        result = node.execute(state)

        assert result["dialogue_act"] == "confirm"
        assert result["self_contained_request"] is False
        assert result["continue_previous_task"] is True
        assert result["need_clarification"] is False
    def test_slot_filling_extracts_budget_language_and_difficulty(self):
        node = TurnUnderstandingNode()
        state = _make_state(
            "800 以内，Java 的，简单点",
            last_intent="推荐",
            conversation_history=[
                {"user": "帮我推荐项目", "assistant": "可以，再告诉我你的预算和技术方向。"}
            ],
        )

        result = node.execute(state)

        assert result["dialogue_act"] == "provide_slot"
        assert result["continue_previous_task"] is True
        assert result["slot_updates"]["budget_max"] == 800
        assert result["slot_updates"]["language"] == "Java"
        assert result["slot_updates"]["difficulty"] == "easy"
    def test_select_item_resolves_previous_quick_action(self):
        node = TurnUnderstandingNode()
        state = _make_state(
            "第一个",
            last_intent="推荐",
            last_quick_actions=[
                {
                    "type": "product",
                    "data": {
                        "title": "Java 图书管理系统",
                    },
                }
            ],
            conversation_history=[
                {"user": "推荐几个 Java 项目", "assistant": "我先给你 3 个方向，你可以说第一个或第二个。"}
            ],
        )

        result = node.execute(state)

        assert result["dialogue_act"] == "select_item"
        assert result["continue_previous_task"] is True
        assert result["selected_quick_action"]["type"] == "product"
        assert "Java 图书管理系统" in result["user_message"]
    def test_negative_feedback_on_recommendations_is_reject_continuation(self):
        node = TurnUnderstandingNode()
        state = _make_state(
            "我都不喜欢这个",
            last_intent="推荐",
            pending_action="select_recommended_item",
            pending_question="这些里你更喜欢哪一个？",
            active_task={"intent": "推荐", "status": "awaiting_user"},
            last_quick_actions=[
                {"type": "product", "data": {"title": "Java 图书管理系统"}},
                {"type": "product", "data": {"title": "在线商城系统"}},
            ],
            conversation_history=[
                {"user": "帮我推荐几个 Java 项目", "assistant": "我给你推荐 3 个方向，你更喜欢哪一个？"}
            ],
        )

        result = node.execute(state)

        assert result["dialogue_act"] == "reject"
        assert result["self_contained_request"] is False
        assert result["continue_previous_task"] is True
        assert result["need_clarification"] is False
    def test_without_context_it_stays_as_new_request(self):
        node = TurnUnderstandingNode()
        state = _make_state("帮我推荐几个 Spring Boot 项目")

        result = node.execute(state)

        assert result["dialogue_act"] == "new_request"
        assert result["domain_intent"] == "推荐"
        assert result["self_contained_request"] is True
        assert result["continue_previous_task"] is False
    def test_explicit_new_request_is_not_misclassified_as_slot_fill(self):
        node = TurnUnderstandingNode()
        state = _make_state(
            "帮我推荐几个 Java 项目",
            last_intent="问答",
            active_task={"intent": "问答", "status": "completed"},
            conversation_history=[
                {"user": "但学生能力限制整体性能", "assistant": "请重新描述一下您的问题。"}
            ],
        )

        result = node.execute(state)

        assert result["dialogue_act"] == "new_request"
        assert result["domain_intent"] == "推荐"
        assert result["self_contained_request"] is True
        assert result["continue_previous_task"] is False
        assert result["slot_updates"]["language"] == "Java"
    def test_llm_fallback_adds_domain_intent_for_natural_request(self):
        mock_llm = self._make_mock_llm(
            """{
  "dialogue_act": "new_request",
  "domain_intent": "推荐",
  "self_contained_request": true,
  "continue_previous_task": false,
  "need_clarification": false,
  "confidence": 0.87,
  "slot_updates": {
    "difficulty": "easy"
  }
}"""
        )
        node = TurnUnderstandingNode(llm=mock_llm)
        state = _make_state("想做个适合答辩展示、别太难的项目")

        result = node.execute(state)

        assert result["dialogue_act"] == "new_request"
        assert result["domain_intent"] == "推荐"
        assert result["self_contained_request"] is True
        assert result["continue_previous_task"] is False
        assert result["slot_updates"]["difficulty"] == "easy"
        assert result["understanding_confidence"] == 0.87
    def test_llm_fallback_can_continue_previous_task_for_contextual_phrase(self):
        mock_llm = self._make_mock_llm(
            """```json
{
  "dialogue_act": "provide_slot",
  "domain_intent": "推荐",
  "self_contained_request": false,
  "continue_previous_task": true,
  "need_clarification": false,
  "confidence": 0.91,
  "slot_updates": {
    "price_preference": "lower"
  }
}
```"""
        )
        node = TurnUnderstandingNode(llm=mock_llm)
        state = _make_state(
            "那个便宜一点的",
            last_intent="推荐",
            active_task={"intent": "推荐", "status": "awaiting_user"},
            conversation_history=[
                {"user": "帮我推荐几个 Java 项目", "assistant": "我给你三个方案，你想便宜一点还是功能更全一点？"}
            ],
        )

        result = node.execute(state)

        assert result["dialogue_act"] == "provide_slot"
        assert result["domain_intent"] == "推荐"
        assert result["self_contained_request"] is False
        assert result["continue_previous_task"] is True
        assert result["slot_updates"]["price_preference"] == "lower"
    def test_explicit_new_request_overrides_pending_follow_up_from_previous_task(self):
        node = TurnUnderstandingNode()
        state = _make_state(
            "帮我推荐几个 Java 项目",
            last_intent="问答",
            pending_action="answer_follow_up",
            pending_question="请告诉我您的具体需求",
            active_task={"intent": "问答", "status": "awaiting_user"},
            conversation_history=[
                {
                    "user": "但学生能力限制整体性能",
                    "assistant": "请告诉我您的具体需求，我会继续帮您分析。",
                }
            ],
        )

        result = node.execute(state)

        assert result["dialogue_act"] == "new_request"
        assert result["domain_intent"] == "推荐"
        assert result["self_contained_request"] is True
        assert result["continue_previous_task"] is False
        assert result["slot_updates"]["language"] == "Java"

