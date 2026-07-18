import pytest
from ai_module.core.nodes.policy.policy_node import PolicyNode


def _make_state(**overrides):
    state = {
        "dialogue_act": "new_request",
        "domain_intent": None,
        "self_contained_request": False,
        "continue_previous_task": False,
        "need_clarification": False,
        "understanding_confidence": 0.0,
        "intent": None,
        "confidence": None,
        "last_intent": None,
        "active_task": None,
        "task_stack": [],
    }
    state.update(overrides)
    return state


class TestPolicyNode:
    def test_self_contained_request_prefers_domain_intent(self):
        node = PolicyNode()
        state = _make_state(
            dialogue_act="new_request",
            domain_intent="推荐",
            self_contained_request=True,
            understanding_confidence=0.92,
            last_intent="问答",
            active_task={"intent": "问答", "status": "awaiting_user"},
        )

        result = node.execute(state)

        assert result["intent"] == "推荐"
        assert result["confidence"] == 0.92
        assert result["continue_previous_task"] is False
    def test_continuation_reuses_active_task_intent(self):
        node = PolicyNode()
        state = _make_state(
            dialogue_act="provide_slot",
            continue_previous_task=True,
            understanding_confidence=0.9,
            active_task={"intent": "推荐", "status": "awaiting_user"},
            last_intent="推荐",
        )

        result = node.execute(state)

        assert result["intent"] == "推荐"
        assert result["confidence"] == 0.9
    def test_conflicting_hint_breaks_continuation_bias(self):
        node = PolicyNode()
        state = _make_state(
            dialogue_act="provide_slot",
            domain_intent="订单查询",
            continue_previous_task=True,
            understanding_confidence=0.86,
            active_task={"intent": "问答", "status": "awaiting_user"},
            last_intent="问答",
        )

        result = node.execute(state)

        assert result["intent"] == "订单查询"
        assert result["dialogue_act"] == "new_request"
        assert result["continue_previous_task"] is False
        assert result["self_contained_request"] is True
    def test_unclear_turn_keeps_intent_empty_for_clarification(self):
        node = PolicyNode()
        state = _make_state(
            dialogue_act="unclear",
            need_clarification=True,
            understanding_confidence=0.25,
        )

        result = node.execute(state)

        assert result["intent"] is None
        assert result["confidence"] == 0.25

