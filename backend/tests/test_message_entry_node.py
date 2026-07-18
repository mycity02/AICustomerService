import pytest

from ai_module.core.constants import DEFAULT_INTENT_RULES
from ai_module.core.nodes.understanding.message_entry_node import MessageEntryNode


class _RuntimeStub:
    class _BusinessPack:
        config = {}

    business_pack = _BusinessPack()

    def __init__(self, *, features=None):
        self._features = features or {}

    def get_business_info(self):
        return {"features": dict(self._features)}

    def get_intent_rules(self):
        return {intent: list(keywords) for intent, keywords in DEFAULT_INTENT_RULES.items()}


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


class TestMessageEntryNode:
    def test_without_active_flow_uses_global_intent_classifier(self):
        node = MessageEntryNode()
        state = _make_state("帮我推荐几个 Java 项目")

        result = node.execute(state)

        assert result["entry_classifier"] == "global_intent"
        assert result["has_active_flow"] is False
        assert result["intent"] == "推荐"
        assert result["domain_intent"] == "推荐"
        assert result["dialogue_act"] == "new_request"
        assert result["self_contained_request"] is True
    def test_with_active_flow_uses_inflow_classifier_for_continuation(self):
        node = MessageEntryNode()
        state = _make_state(
            "800以内，Java的，简单点",
            last_intent="推荐",
            active_task={"intent": "推荐", "status": "awaiting_user"},
            pending_action="select_recommended_item",
            pending_question="这些里你更喜欢哪一个？",
            conversation_history=[
                {"user": "帮我推荐几个 Java 项目", "assistant": "告诉我你的预算和技术偏好。"}
            ],
        )

        result = node.execute(state)

        assert result["entry_classifier"] == "inflow"
        assert result["has_active_flow"] is True
        assert result["active_flow"] == "推荐"
        assert result["inflow_type"] == "valid_current_input"
        assert result["intent"] == "推荐"
        assert result["continue_previous_task"] is True
        assert result["slot_updates"]["budget_max"] == 800
        assert result["slot_updates"]["language"] == "Java"
    def test_with_active_flow_switches_to_new_global_intent_when_user_changes_task(self):
        node = MessageEntryNode()
        state = _make_state(
            "查一下我的订单",
            last_intent="推荐",
            active_task={"intent": "推荐", "status": "awaiting_user"},
            pending_action="select_recommended_item",
            pending_question="这些里你更喜欢哪一个？",
            conversation_history=[
                {"user": "帮我推荐几个 Java 项目", "assistant": "我给你推荐了 3 个方向。"}
            ],
        )

        result = node.execute(state)

        assert result["entry_classifier"] == "inflow"
        assert result["has_active_flow"] is True
        assert result["inflow_type"] == "switch_flow"
        assert result["flow_relation"] == "switch"
        assert result["intent"] == "订单查询"
        assert result["domain_intent"] == "订单查询"
        assert result["continue_previous_task"] is False
    def test_cart_question_switches_out_of_order_flow_instead_of_reusing_order_query(self):
        node = MessageEntryNode()
        state = _make_state(
            "购物车有东西吗",
            last_intent="订单查询",
            active_task={"intent": "订单查询", "status": "awaiting_user"},
            pending_action="select_order",
            pending_question="请选择您要咨询的订单",
            conversation_history=[
                {"user": "查看我的订单", "assistant": "您有 7 个订单，请选择要咨询的订单。"}
            ],
        )

        result = node.execute(state)

        assert result["entry_classifier"] == "inflow"
        assert result["inflow_type"] == "switch_flow"
        assert result["flow_relation"] == "switch"
        assert result["intent"] == "购物车查询"
        assert result["domain_intent"] == "购物车查询"
        assert result["continue_previous_task"] is False
    def test_disabled_capability_in_active_flow_short_circuits_to_unsupported_route(self):
        node = MessageEntryNode(runtime=_RuntimeStub(features={"coupon_system": False}))
        state = _make_state(
            "优惠券可以用吗",
            last_intent="订单查询",
            active_task={"intent": "订单查询", "status": "awaiting_user"},
            pending_action="select_order",
            pending_question="请选择您要咨询的订单",
        )

        result = node.execute(state)

        assert result["entry_classifier"] == "inflow"
        assert result["skill_route"] == "unsupported_capability"
        assert result["unsupported_capability"] == "coupon_query"
        assert result["unsupported_capability_label"] == "优惠券"
        assert result["response_mode"] == "answer_then_resume"
        assert result["resume_mode"] == "resume_exact"
        assert result["intent"] is None
        assert result["continue_previous_task"] is False
    def test_out_of_domain_message_short_circuits_to_domain_scope_guard(self):
        node = MessageEntryNode()
        state = _make_state(
            "去新疆旅行",
            last_intent="订单查询",
            active_task={"intent": "订单查询", "status": "awaiting_user"},
            pending_action="select_order",
            pending_question="请选择您要咨询的订单",
        )

        result = node.execute(state)

        assert result["entry_classifier"] == "inflow"
        assert result["skill_route"] == "domain_scope_guard"
        assert result["semantic_source"] == "domain_scope_guard"
        assert result["inflow_type"] == "irrelevant"
        assert result["intent"] is None
        assert result["flow_relation"] == "interrupt"
        assert result["response_mode"] == "answer_then_resume"
        assert result["continue_previous_task"] is False
    def test_out_of_domain_message_without_active_flow_short_circuits_before_intent(self):
        node = MessageEntryNode()
        state = _make_state("去新疆旅行")

        result = node.execute(state)

        assert result["entry_classifier"] == "global_intent"
        assert result["skill_route"] == "domain_scope_guard"
        assert result["semantic_source"] == "domain_scope_guard"
        assert result["intent"] is None
        assert result["flow_relation"] == "no_flow"
    def test_same_domain_self_contained_request_defers_to_inflow_llm(self):
        node = MessageEntryNode()
        state = _make_state(
            "我想去旅行",
            last_intent="推荐",
            active_task={"intent": "推荐", "status": "awaiting_user"},
            pending_action="select_recommended_item",
            pending_question="这些里你更喜欢哪一个？",
            conversation_history=[
                {"user": "帮我推荐几个 Java 项目", "assistant": "我先给你 3 个方向。"}
            ],
        )

        def fake_understanding(_state):
            _state["dialogue_act"] = "new_request"
            _state["domain_intent"] = "推荐"
            _state["self_contained_request"] = True
            _state["continue_previous_task"] = False
            _state["slot_updates"] = {}
            _state["understanding_confidence"] = 0.72
            return _state

        def fake_inflow_llm(*_args, **_kwargs):
            return {
                "inflow_type": "irrelevant",
                "domain_intent": None,
                "continue_previous_task": False,
                "need_clarification": False,
                "confidence": 0.84,
            }

        node.inflow_understanding.execute = fake_understanding
        node._infer_inflow_with_llm = fake_inflow_llm

        result = node.execute(state)

        assert result["inflow_type"] == "irrelevant"
        assert result["flow_relation"] == "interrupt"
        assert result["continue_previous_task"] is False
    def test_irrelevant_message_does_not_soft_switch_to_global_qa(self):
        node = MessageEntryNode()
        state = _make_state(
            "中东地区怎么打仗了",
            last_intent="推荐",
            active_task={"intent": "推荐", "status": "awaiting_user"},
            pending_action="select_recommended_item",
            pending_question="这些里你更喜欢哪一个？",
        )

        def fake_understanding(_state):
            _state["dialogue_act"] = "unclear"
            _state["domain_intent"] = None
            _state["self_contained_request"] = False
            _state["continue_previous_task"] = False
            _state["slot_updates"] = {}
            _state["understanding_confidence"] = 0.35
            return _state

        def fake_intent(_state):
            _state["intent"] = "问答"
            _state["confidence"] = 0.92
            return _state

        def fake_inflow_llm(*_args, **_kwargs):
            return None

        node.inflow_understanding.execute = fake_understanding
        node.global_intent_classifier.execute = fake_intent
        node._infer_inflow_with_llm = fake_inflow_llm

        result = node.execute(state)

        assert result["skill_route"] == "domain_scope_guard"
        assert result["semantic_source"] == "domain_scope_guard"
        assert result["intent"] is None
        assert result["flow_relation"] == "interrupt"
        assert result["continue_previous_task"] is False
    def test_out_of_domain_question_short_circuits_before_related_question_fallback(self):
        node = MessageEntryNode()
        state = _make_state(
            "中东地区怎么打仗了",
            last_intent="推荐",
            active_task={"intent": "推荐", "status": "awaiting_user"},
            pending_action="select_recommended_item",
            pending_question="这些里你更喜欢哪一个？",
        )

        def fake_understanding(_state):
            _state["dialogue_act"] = "unclear"
            _state["domain_intent"] = None
            _state["self_contained_request"] = False
            _state["continue_previous_task"] = False
            _state["slot_updates"] = {}
            _state["understanding_confidence"] = 0.41
            return _state

        def fake_inflow_llm(*_args, **_kwargs):
            return {
                "inflow_type": "related_question",
                "domain_intent": None,
                "continue_previous_task": False,
                "need_clarification": False,
                "confidence": 0.86,
            }

        def fake_intent(_state):
            _state["intent"] = "问答"
            _state["confidence"] = 0.93
            return _state

        node.inflow_understanding.execute = fake_understanding
        node._infer_inflow_with_llm = fake_inflow_llm
        node.global_intent_classifier.execute = fake_intent

        result = node.execute(state)

        assert result["skill_route"] == "domain_scope_guard"
        assert result["semantic_source"] == "domain_scope_guard"
        assert result["inflow_type"] == "irrelevant"
        assert result["intent"] is None
        assert result["response_mode"] == "answer_then_resume"
        assert result["continue_previous_task"] is False
