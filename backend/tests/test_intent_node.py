"""
Unit tests for intent_node.py — verifying intent history prompt formatting,
fallback logic, and intent history append behavior.
"""
import sys
import os
import types
import importlib.util
from unittest.mock import MagicMock

import pytest

# ── Bootstrap: set up the module hierarchy so intent_node's relative imports work ──

_backend_dir = os.path.join(os.path.dirname(__file__), "..")

# Create package stubs so relative imports resolve
for pkg in [
    "backend",
    "backend.services",
    "backend.ai_module.core",
    "backend.ai_module.core.nodes",
]:
    if pkg not in sys.modules:
        sys.modules[pkg] = types.ModuleType(pkg)

# Load state.py
_state_path = os.path.join(_backend_dir, "ai_module", "core", "state.py")
_state_spec = importlib.util.spec_from_file_location("backend.ai_module.core.state", _state_path)
_state_mod = importlib.util.module_from_spec(_state_spec)
sys.modules["backend.ai_module.core.state"] = _state_mod
_state_spec.loader.exec_module(_state_mod)

# Load base.py
_base_path = os.path.join(_backend_dir, "ai_module", "core", "nodes", "common", "base.py")
_base_spec = importlib.util.spec_from_file_location("backend.ai_module.core.nodes.common.base", _base_path)
_base_mod = importlib.util.module_from_spec(_base_spec)
sys.modules["backend.ai_module.core.nodes.common.base"] = _base_mod
_base_spec.loader.exec_module(_base_mod)

# Load config.py
_config_path = os.path.join(_backend_dir, "config.py")
_config_spec = importlib.util.spec_from_file_location("backend.config", _config_path)
_config_mod = importlib.util.module_from_spec(_config_spec)
sys.modules["backend.config"] = _config_mod
sys.modules["config"] = _config_mod
_config_spec.loader.exec_module(_config_mod)

# Load constants.py
_constants_path = os.path.join(_backend_dir, "ai_module", "core", "constants.py")
_constants_spec = importlib.util.spec_from_file_location("backend.ai_module.core.constants", _constants_path)
_constants_mod = importlib.util.module_from_spec(_constants_spec)
_constants_mod.__package__ = "backend.ai_module.core"
sys.modules["backend.ai_module.core.constants"] = _constants_mod
_constants_spec.loader.exec_module(_constants_mod)

# Load intent_node.py
_intent_path = os.path.join(_backend_dir, "ai_module", "core", "nodes", "understanding", "intent_node.py")
_intent_spec = importlib.util.spec_from_file_location(
    "backend.ai_module.core.nodes.understanding.intent_node", _intent_path,
    submodule_search_locations=[],
)
_intent_mod = importlib.util.module_from_spec(_intent_spec)
_intent_mod.__package__ = "backend.ai_module.core.nodes"
sys.modules["backend.ai_module.core.nodes.understanding.intent_node"] = _intent_mod
_intent_spec.loader.exec_module(_intent_mod)

_format_intent_history = _intent_mod._format_intent_history
_find_fallback_intent = _intent_mod._find_fallback_intent
IntentRecognitionNode = _intent_mod.IntentRecognitionNode


# ── _format_intent_history tests ─────────────────────────────────────

class TestFormatIntentHistory:
    def test_empty_history_returns_placeholder(self):
        result = _format_intent_history([], max_entries=5)
        assert result == "（无历史记录）"

    def test_single_entry(self):
        history = [{"intent": "商品咨询", "confidence": 0.9, "turn": 1}]
        result = _format_intent_history(history, max_entries=5)
        assert "第 1 轮" in result
        assert "商品咨询" in result
        assert "0.9" in result

    def test_respects_max_entries_limit(self):
        history = [
            {"intent": "问答", "confidence": 0.8, "turn": i}
            for i in range(1, 11)
        ]
        result = _format_intent_history(history, max_entries=3)
        lines = result.strip().split("\n")
        assert len(lines) == 3
        # Should contain the last 3 entries (turns 8, 9, 10)
        assert "第 8 轮" in lines[0]
        assert "第 9 轮" in lines[1]
        assert "第 10 轮" in lines[2]

    def test_fewer_entries_than_max(self):
        history = [
            {"intent": "订单查询", "confidence": 0.85, "turn": 1},
            {"intent": "商品推荐", "confidence": 0.9, "turn": 2},
        ]
        result = _format_intent_history(history, max_entries=5)
        lines = result.strip().split("\n")
        assert len(lines) == 2

    def test_missing_fields_use_defaults(self):
        history = [{"intent": "问答"}]  # missing confidence and turn
        result = _format_intent_history(history, max_entries=5)
        assert "第 0 轮" in result
        assert "0.0" in result


# ── _find_fallback_intent tests ──────────────────────────────────────

class TestFindFallbackIntent:
    def test_empty_history_returns_none(self):
        assert _find_fallback_intent([], threshold=0.6) is None

    def test_all_below_threshold_returns_none(self):
        history = [
            {"intent": "问答", "confidence": 0.3, "turn": 1},
            {"intent": "商品咨询", "confidence": 0.5, "turn": 2},
        ]
        assert _find_fallback_intent(history, threshold=0.6) is None

    def test_returns_most_recent_above_threshold(self):
        history = [
            {"intent": "商品咨询", "confidence": 0.9, "turn": 1},
            {"intent": "订单查询", "confidence": 0.8, "turn": 2},
            {"intent": "问答", "confidence": 0.3, "turn": 3},
        ]
        result = _find_fallback_intent(history, threshold=0.6)
        assert result == "订单查询"  # most recent with confidence >= 0.6

    def test_exact_threshold_is_included(self):
        history = [
            {"intent": "工单", "confidence": 0.6, "turn": 1},
        ]
        result = _find_fallback_intent(history, threshold=0.6)
        assert result == "工单"

    def test_single_high_confidence_entry(self):
        history = [
            {"intent": "购买指导", "confidence": 0.95, "turn": 1},
        ]
        result = _find_fallback_intent(history, threshold=0.6)
        assert result == "购买指导"


# ── _append_intent_history tests ─────────────────────────────────────

class TestAppendIntentHistory:
    def setup_method(self):
        self.node = IntentRecognitionNode(llm=None)

    def test_append_to_empty_history(self):
        state = {}
        self.node._append_intent_history(state, [], "商品咨询", 0.9)
        assert len(state["intent_history"]) == 1
        entry = state["intent_history"][0]
        assert entry["intent"] == "商品咨询"
        assert entry["confidence"] == 0.9
        assert entry["turn"] == 1
        assert "timestamp" in entry

    def test_append_increments_turn(self):
        existing = [
            {"intent": "问答", "confidence": 0.8, "turn": 3, "timestamp": "t"},
        ]
        state = {}
        self.node._append_intent_history(state, existing, "订单查询", 0.85)
        assert len(state["intent_history"]) == 2
        assert state["intent_history"][-1]["turn"] == 4

    def test_does_not_mutate_original_list(self):
        original = [
            {"intent": "问答", "confidence": 0.8, "turn": 1, "timestamp": "t"},
        ]
        original_len = len(original)
        state = {}
        self.node._append_intent_history(state, original, "工单", 0.7)
        assert len(original) == original_len  # original unchanged
        assert len(state["intent_history"]) == original_len + 1


# ── IntentRecognitionNode.execute integration tests ──────────────────

class TestIntentRecognitionNodeExecute:
    def setup_method(self):
        # Clear the class-level cache before each test
        IntentRecognitionNode._intent_cache.clear()

    def _make_state(self, message="你好", intent_history=None, attachments=None, **overrides):
        state = {
            "user_message": message,
            "user_id": "test_user",
            "session_id": "test_session",
            "attachments": attachments,
            "conversation_history": [],
            "user_profile": {},
            "last_intent": None,
            "dialogue_act": None,
            "continue_previous_task": False,
            "task_stack": [],
            "intent": None,
            "confidence": None,
            "intent_history": intent_history,
        }
        state.update(overrides)
        return state

    def _make_mock_llm(self, response_text="问答"):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = response_text
        mock_llm.invoke.return_value = mock_response
        return mock_llm
    def test_execute_appends_to_empty_intent_history(self):
        mock_llm = self._make_mock_llm("商品推荐")
        node = IntentRecognitionNode(llm=mock_llm)
        state = self._make_state(message="推荐几个项目", intent_history=[])

        result = node.execute(state)

        assert result["intent"] == "推荐"
        assert len(result["intent_history"]) == 1
        assert result["intent_history"][0]["intent"] == "推荐"
        assert result["intent_history"][0]["turn"] == 1
    def test_execute_appends_to_existing_intent_history(self):
        mock_llm = self._make_mock_llm("订单查询")
        node = IntentRecognitionNode(llm=mock_llm)
        existing_history = [
            {"intent": "商品咨询", "confidence": 0.9, "turn": 1, "timestamp": "t1"},
        ]
        state = self._make_state(
            message="我的订单到哪了",
            intent_history=existing_history,
        )

        result = node.execute(state)

        assert result["intent"] == "订单查询"
        assert len(result["intent_history"]) == 2
        assert result["intent_history"][-1]["intent"] == "订单查询"
        assert result["intent_history"][-1]["turn"] == 2
    def test_execute_uses_history_prompt_when_history_exists(self):
        mock_llm = self._make_mock_llm("商品咨询")
        node = IntentRecognitionNode(llm=mock_llm)
        existing_history = [
            {"intent": "商品推荐", "confidence": 0.9, "turn": 1, "timestamp": "t1"},
        ]
        state = self._make_state(
            message="我想继续刚才的话题",
            intent_history=existing_history,
        )

        node.execute(state)

        # Verify LLM was called with messages that include intent history
        call_args = mock_llm.invoke.call_args[0][0]
        system_msg = call_args[0].content
        assert "意图历史" in system_msg
        assert "商品推荐" in system_msg
    def test_execute_uses_basic_prompt_when_no_history(self):
        mock_llm = self._make_mock_llm("问答")
        node = IntentRecognitionNode(llm=mock_llm)
        state = self._make_state(message="我想补充一点信息", intent_history=[])

        node.execute(state)

        call_args = mock_llm.invoke.call_args[0][0]
        system_msg = call_args[0].content
        assert "最近的意图历史" not in system_msg
    def test_attachment_shortcut_appends_to_history(self):
        node = IntentRecognitionNode(llm=None)
        state = self._make_state(
            message="分析一下",
            intent_history=[],
            attachments=[{"name": "file.pdf"}],
        )

        result = node.execute(state)

        assert result["intent"] == "文档分析"
        assert len(result["intent_history"]) == 1
        assert result["intent_history"][0]["intent"] == "文档分析"
    def test_continue_previous_task_reuses_last_intent(self):
        mock_llm = self._make_mock_llm("问答")
        node = IntentRecognitionNode(llm=mock_llm)
        state = self._make_state(
            message="需要",
            intent_history=[],
            last_intent="推荐",
            dialogue_act="confirm",
            continue_previous_task=True,
        )

        result = node.execute(state)

        assert result["intent"] == "推荐"
        assert result["confidence"] == 0.92
        mock_llm.invoke.assert_not_called()
    def test_resume_task_uses_stacked_intent(self):
        mock_llm = self._make_mock_llm("问答")
        node = IntentRecognitionNode(llm=mock_llm)
        state = self._make_state(
            message="继续刚才那个",
            dialogue_act="resume_task",
            task_stack=[{"intent": "订单查询"}],
        )

        result = node.execute(state)

        assert result["intent"] == "订单查询"
        assert result["confidence"] == 0.9
        mock_llm.invoke.assert_not_called()
    def test_preselected_intent_from_policy_short_circuits(self):
        mock_llm = self._make_mock_llm("问答")
        node = IntentRecognitionNode(llm=mock_llm)
        state = self._make_state(
            message="帮我推荐几个 Java 项目",
            intent_history=[],
            intent="推荐",
            confidence=0.91,
        )

        result = node.execute(state)

        assert result["intent"] == "推荐"
        assert result["confidence"] == 0.91
        mock_llm.invoke.assert_not_called()
    def test_explicit_new_intent_overrides_continuation_bias(self):
        mock_llm = self._make_mock_llm("问答")
        node = IntentRecognitionNode(llm=mock_llm)
        state = self._make_state(
            message="帮我推荐几个 Java 项目",
            intent_history=[],
            last_intent="问答",
            dialogue_act="provide_slot",
            continue_previous_task=True,
        )

        result = node.execute(state)

        assert result["intent"] == "推荐"
        assert result["confidence"] == 0.95
        assert result["continue_previous_task"] is False
        assert result["dialogue_act"] == "new_request"
        mock_llm.invoke.assert_not_called()
    def test_cart_query_matches_rule_before_order_history_bias(self):
        mock_llm = self._make_mock_llm("订单查询")
        node = IntentRecognitionNode(llm=mock_llm)
        state = self._make_state(
            message="购物车有东西吗",
            intent_history=[
                {"intent": "订单查询", "confidence": 0.95, "turn": 1, "timestamp": "t1"},
            ],
        )

        result = node.execute(state)

        assert result["intent"] == "购物车查询"
        assert result["confidence"] == 0.95
        mock_llm.invoke.assert_not_called()
    def test_exception_fallback_appends_to_history(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM error")
        node = IntentRecognitionNode(llm=mock_llm)
        state = self._make_state(message="测试异常", intent_history=[])

        result = node.execute(state)

        assert result["intent"] == "问答"
        assert result["confidence"] == 0.5
        assert len(result["intent_history"]) == 1
        assert result["intent_history"][0]["intent"] == "问答"

