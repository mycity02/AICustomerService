import types

import pytest
from ai_module.core.nodes.policy.conversation_control_node import ConversationControlNode
from ai_module.core.nodes.policy.response_planner_node import ResponsePlannerNode


def _make_state(**overrides):
    state = {
        "has_active_flow": True,
        "active_flow": "推荐",
        "current_step": "select_recommended_item",
        "pending_question": "这些里你更喜欢哪一个？",
        "pending_action": "select_recommended_item",
        "inflow_type": None,
        "response_mode": None,
        "resume_mode": None,
        "continue_previous_task": False,
        "need_clarification": False,
        "self_contained_request": False,
        "intent": None,
        "domain_intent": None,
        "user_message": "我想去旅行",
        "conversation_history": [],
    }
    state.update(overrides)
    return state


class _FakeLLM:
    def __init__(self, content: str):
        self.content = content

    def invoke(self, _messages):
        return types.SimpleNamespace(content=self.content)


class _CapturingLLM:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return types.SimpleNamespace(content=self.content)


class TestResponsePlannerNode:
    def test_irrelevant_input_goes_to_answer_then_resume(self):
        node = ResponsePlannerNode()
        state = _make_state(inflow_type="irrelevant")

        result = node.execute(state)

        assert result["response_mode"] == "answer_then_resume"
        assert result["resume_mode"] == "resume_exact"
        assert result["continue_previous_task"] is False
    def test_related_blocker_uses_safe_step_resume(self):
        node = ResponsePlannerNode()
        state = _make_state(
            inflow_type="related_blocker",
            user_message="我不会操作这一步",
        )

        result = node.execute(state)

        assert result["response_mode"] == "help_current_task"
        assert result["resume_mode"] == "resume_from_safe_step"
    def test_unknown_self_contained_message_prefers_answer_then_resume(self):
        node = ResponsePlannerNode()
        state = _make_state(
            inflow_type="unknown",
            self_contained_request=True,
            user_message="今天天气真好",
        )

        result = node.execute(state)

        assert result["response_mode"] == "answer_then_resume"
        assert result["resume_mode"] == "resume_exact"
    def test_unknown_ambiguous_reference_still_clarifies(self):
        node = ResponsePlannerNode()
        state = _make_state(
            inflow_type="unknown",
            user_message="那个呢",
        )

        result = node.execute(state)

        assert result["response_mode"] == "clarify_before_resume"
        assert result["resume_mode"] == "resume_from_safe_step"
    def test_conversation_control_generates_resume_prompt(self):
        node = ConversationControlNode()
        state = _make_state(
            response_mode="clarify_before_resume",
            resume_mode="resume_exact",
            user_message="那个呢",
        )

        result = node.execute(state)

        assert "那个呢" in result["response"]
        assert "第一个" in result["response"]
        assert "切换" not in result["response"]
    def test_conversation_control_answers_side_topic_naturally(self):
        node = ConversationControlNode(llm=_FakeLLM("这句我先接住，刚才那个推荐我也还记着。"))
        state = _make_state(
            response_mode="answer_then_resume",
            user_message="谢谢",
        )

        result = node.execute(state)

        assert "刚才那个推荐" in result["response"]
    def test_conversation_control_includes_short_term_memory_in_prompt(self):
        llm = _CapturingLLM("我先接住这个话题。")
        node = ConversationControlNode(llm=llm)
        state = _make_state(
            response_mode="answer_then_resume",
            user_message="谢谢",
            conversation_history=[
                {"user": "天气真冷啊", "assistant": "是啊，这两天降温挺明显的。"},
                {"user": "我要去新疆旅行", "assistant": "新疆昼夜温差会比较大。"},
            ],
            active_task={
                "intent": "推荐",
                "status": "awaiting_user",
                "slots": {"language": "Python"},
                "pending_question": "这些里你更喜欢哪一个？",
                "pending_action": "select_recommended_item",
            },
        )

        node.execute(state)

        prompt_text = "\n".join(getattr(message, "content", "") for message in llm.messages)
        assert "短期记忆：" in prompt_text
        assert "我要去新疆旅行" in prompt_text
        assert "当前主任务：推荐" in prompt_text
    def test_conversation_control_redirects_out_of_scope_topic_back_to_business(self):
        node = ConversationControlNode(
            llm=_FakeLLM("新疆确实值得去看看。顺着刚才的订单问题，您可以继续往下说，我接着帮您处理。")
        )
        state = _make_state(
            active_flow="订单查询",
            response_mode="answer_then_resume",
            user_message="去新疆旅行",
        )

        result = node.execute(state)

        assert "新疆确实值得去看看" in result["response"]
        assert "订单问题" in result["response"]
        assert "主要还是处理" not in result["response"]
        assert "先放一放" not in result["response"]
        assert "简短接一下" not in result["response"]
        assert "订单查询任务" not in result["response"]
    def test_conversation_control_redirects_out_of_scope_topic_naturally_in_recommend_flow(self):
        node = ConversationControlNode(
            llm=_FakeLLM("新加坡节奏挺快的。说回刚才选茶这件事，您更在意茶类、香型、预算还是口感浓淡？")
        )
        state = _make_state(
            response_mode="answer_then_resume",
            user_message="新加坡怎么样",
            active_task={
                "intent": "推荐",
                "status": "awaiting_user",
                "slots": {"language": "Python"},
                "pending_question": "这些里你更喜欢哪一个？",
                "pending_action": "select_recommended_item",
            },
        )

        result = node.execute(state)

        assert "新加坡节奏挺快的" in result["response"]
        assert "说回刚才选茶这件事" in result["response"]
        assert "您更在意茶类、香型、预算还是口感浓淡" in result["response"]
        assert "刚才我们在看 Python 茶品" not in result["response"]
        assert "主要还是帮您做" not in result["response"]
    def test_conversation_control_out_of_scope_prompt_emphasizes_natural_transition(self):
        llm = _CapturingLLM("新加坡节奏挺快的。说回刚才选茶这件事，您更在意茶类、香型、预算还是口感浓淡？")
        node = ConversationControlNode(llm=llm)
        state = _make_state(
            response_mode="answer_then_resume",
            user_message="新加坡怎么样",
            active_task={
                "intent": "推荐",
                "status": "awaiting_user",
                "slots": {"language": "Python"},
                "pending_question": "这些里你更喜欢哪一个？",
                "pending_action": "select_recommended_item",
            },
        )

        node.execute(state)

        prompt_text = "\n".join(getattr(message, "content", "") for message in llm.messages)
        assert "不自然示例" in prompt_text
        assert "更自然示例" in prompt_text
        assert "不要直接写“我们先说回刚才的茶品选择”" in prompt_text

