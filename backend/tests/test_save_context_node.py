"""
Unit tests for SaveContextNode with ConversationSummarizer integration.

Tests cover:
- Basic context saving (message + intent_history persistence)
- Summarization trigger when history exceeds threshold
- Fallback truncation when summarization fails
- No summarization when summarizer is not provided (llm=None)
"""
import sys
import os
import types
import importlib.util
from unittest.mock import MagicMock, patch

import pytest

# ── Bootstrap: set up the module hierarchy so imports work ──

_backend_dir = os.path.join(os.path.dirname(__file__), "..")

for pkg in [
    "backend",
    "backend.services",
    "backend.ai_module.core",
    "backend.ai_module.core.nodes",
]:
    if pkg not in sys.modules:
        sys.modules[pkg] = types.ModuleType(pkg)

# Load config.py
_config_path = os.path.join(_backend_dir, "config.py")
_config_spec = importlib.util.spec_from_file_location("backend.config", _config_path)
_config_mod = importlib.util.module_from_spec(_config_spec)
sys.modules["backend.config"] = _config_mod
_config_spec.loader.exec_module(_config_mod)

# Stub services.redis_cache so save_context_node can import it
_redis_cache_stub = types.ModuleType("services.redis_cache")
_mock_redis_cache = MagicMock()
_redis_cache_stub.redis_cache = _mock_redis_cache
sys.modules["services.redis_cache"] = _redis_cache_stub

# Load base node
_base_path = os.path.join(_backend_dir, "ai_module", "core", "nodes", "common", "base.py")
_base_spec = importlib.util.spec_from_file_location(
    "backend.ai_module.core.nodes.common.base", _base_path,
)
_base_mod = importlib.util.module_from_spec(_base_spec)
_base_mod.__package__ = "backend.ai_module.core.nodes"

# We need state module for base
_state_path = os.path.join(_backend_dir, "ai_module", "core", "state.py")
_state_spec = importlib.util.spec_from_file_location(
    "backend.ai_module.core.state", _state_path,
)
_state_mod = importlib.util.module_from_spec(_state_spec)
_state_mod.__package__ = "backend.ai_module.core"
sys.modules["backend.ai_module.core.state"] = _state_mod
# Also register as relative import target
sys.modules["..state"] = _state_mod
_state_spec.loader.exec_module(_state_mod)

sys.modules["backend.ai_module.core.nodes.common.base"] = _base_mod
_base_spec.loader.exec_module(_base_mod)

# Load summarizer
_summarizer_path = os.path.join(_backend_dir, "ai_module", "core", "summarizer.py")
_summarizer_spec = importlib.util.spec_from_file_location(
    "backend.ai_module.core.summarizer", _summarizer_path,
)
_summarizer_mod = importlib.util.module_from_spec(_summarizer_spec)
_summarizer_mod.__package__ = "backend.ai_module.core"
sys.modules["backend.ai_module.core.summarizer"] = _summarizer_mod
_summarizer_spec.loader.exec_module(_summarizer_mod)

# Load save_context_node
_node_path = os.path.join(_backend_dir, "ai_module", "core", "nodes", "memory", "save_context_node.py")
_node_spec = importlib.util.spec_from_file_location(
    "backend.ai_module.core.nodes.memory.save_context_node", _node_path,
)
_node_mod = importlib.util.module_from_spec(_node_spec)
_node_mod.__package__ = "backend.ai_module.core.nodes"
sys.modules["backend.ai_module.core.nodes.memory.save_context_node"] = _node_mod
_node_spec.loader.exec_module(_node_mod)

SaveContextNode = _node_mod.SaveContextNode


# ── Helpers ──────────────────────────────────────────────────────────

def _make_state(**overrides):
    """Build a minimal ConversationState dict for testing."""
    base = {
        "session_id": "test-session",
        "user_message": "hello",
        "response": "hi there",
        "intent": "问答",
        "intent_history": [{"intent": "问答", "confidence": 0.9, "turn": 1}],
        "quick_actions": [],
        "active_task": None,
        "task_stack": [],
    }
    base.update(overrides)
    return base


# ── Tests ────────────────────────────────────────────────────────────
def test_saves_message_and_intent_history():
    """Basic save: adds message to context and persists intent_history."""
    node = SaveContextNode(llm=None)
    state = _make_state()

    mock_cache = MagicMock()
    mock_cache.add_message_to_context = MagicMock()
    mock_cache.update_context = MagicMock()

    with patch.object(_node_mod, "redis_cache", mock_cache):
        result = node.execute(state)

    mock_cache.add_message_to_context.assert_called_once_with(
        session_id="test-session",
        user_message="hello",
        assistant_message="hi there",
    )
    mock_cache.update_context.assert_called_once_with(
        session_id="test-session",
        last_intent="问答",
        intent_history=[{"intent": "问答", "confidence": 0.9, "turn": 1}],
        last_quick_actions=[],
        active_task=None,
        task_stack=[],
        pending_question=None,
        pending_action=None,
    )
    assert result is state
def test_save_context_updates_active_task_pending_state():
    node = SaveContextNode(llm=None)
    state = _make_state(
        response="请从下面选择一个项目：",
        quick_actions=[{"type": "product", "data": {"title": "Java 图书管理系统"}}],
        active_task={"id": "task-1", "intent": "推荐", "status": "active", "slots": {}},
    )

    mock_cache = MagicMock()
    mock_cache.add_message_to_context = MagicMock()
    mock_cache.update_context = MagicMock()

    with patch.object(_node_mod, "redis_cache", mock_cache):
        node.execute(state)

    assert state["active_task"]["status"] == "awaiting_user"
    assert state["pending_action"] == "select_recommended_item"
    assert state["pending_question"] == "请从下面选择一个项目："
def test_no_summarization_without_llm():
    """When llm is None, summarizer is None and summarization is skipped."""
    node = SaveContextNode(llm=None)
    assert node.summarizer is None

    state = _make_state()
    mock_cache = MagicMock()
    mock_cache.add_message_to_context = MagicMock()
    mock_cache.update_context = MagicMock()
    mock_cache.get_context = MagicMock()

    with patch.object(_node_mod, "redis_cache", mock_cache):
        node.execute(state)

    # get_context should NOT be called when summarizer is None
    mock_cache.get_context.assert_not_called()
def test_summarization_triggered_when_threshold_exceeded():
    """When history exceeds threshold, summarizer.summarize is called and cache updated."""
    mock_llm = MagicMock()
    node = SaveContextNode(llm=mock_llm)

    long_history = [{"user": f"msg{i}", "assistant": f"reply{i}"} for i in range(15)]
    state = _make_state()

    mock_cache = MagicMock()
    mock_cache.add_message_to_context = MagicMock()
    mock_cache.update_context = MagicMock()
    mock_cache.get_context = MagicMock(return_value={
        "history": long_history,
        "conversation_summary": "old summary",
    })

    # Mock the summarizer methods
    node.summarizer.should_summarize = MagicMock(return_value=True)
    node.summarizer.summarize = MagicMock(return_value={
        "summary": "new summary",
        "remaining_history": long_history[-10:],
    })

    with patch.object(_node_mod, "redis_cache", mock_cache):
        node.execute(state)

    node.summarizer.summarize.assert_called_once_with(long_history, "old summary")

    # Second update_context call should have the summary result
    calls = mock_cache.update_context.call_args_list
    assert len(calls) == 2
    _, kwargs = calls[1]
    assert kwargs["session_id"] == "test-session"
    assert kwargs["history"] == long_history[-10:]
    assert kwargs["conversation_summary"] == "new summary"
def test_fallback_truncation_on_summarization_failure():
    """When summarize() raises, fallback_truncate is used instead."""
    mock_llm = MagicMock()
    node = SaveContextNode(llm=mock_llm)

    long_history = [{"user": f"msg{i}", "assistant": f"reply{i}"} for i in range(15)]
    state = _make_state()

    mock_cache = MagicMock()
    mock_cache.add_message_to_context = MagicMock()
    mock_cache.update_context = MagicMock()
    mock_cache.get_context = MagicMock(return_value={
        "history": long_history,
        "conversation_summary": "",
    })

    node.summarizer.should_summarize = MagicMock(return_value=True)
    node.summarizer.summarize = MagicMock(side_effect=RuntimeError("LLM failed"))
    node.summarizer.fallback_truncate = MagicMock(return_value={
        "summary": "",
        "remaining_history": long_history[-10:],
    })

    with patch.object(_node_mod, "redis_cache", mock_cache):
        node.execute(state)

    node.summarizer.fallback_truncate.assert_called_once_with(long_history)

    calls = mock_cache.update_context.call_args_list
    assert len(calls) == 2
    _, kwargs = calls[1]
    assert kwargs["history"] == long_history[-10:]
def test_no_summarization_when_below_threshold():
    """When history is below threshold, no summarization occurs."""
    mock_llm = MagicMock()
    node = SaveContextNode(llm=mock_llm)

    short_history = [{"user": f"msg{i}", "assistant": f"reply{i}"} for i in range(5)]
    state = _make_state()

    mock_cache = MagicMock()
    mock_cache.add_message_to_context = MagicMock()
    mock_cache.update_context = MagicMock()
    mock_cache.get_context = MagicMock(return_value={
        "history": short_history,
        "conversation_summary": "",
    })

    node.summarizer.should_summarize = MagicMock(return_value=False)
    node.summarizer.summarize = MagicMock()

    with patch.object(_node_mod, "redis_cache", mock_cache):
        node.execute(state)

    node.summarizer.summarize.assert_not_called()
    # update_context should only be called once (for intent_history)
    mock_cache.update_context.assert_called_once()
def test_control_response_preserves_resume_position():
    node = SaveContextNode(llm=None)
    state = _make_state(
        response="我先确认一下，您是想继续刚才的推荐任务，还是切换到新的问题？",
        response_mode="clarify_before_resume",
        resume_mode="resume_exact",
        pending_question="这些里你更喜欢哪一个？",
        pending_action="select_recommended_item",
        active_task={
            "id": "task-1",
            "intent": "推荐",
            "status": "awaiting_user",
            "slots": {"language": "Java"},
            "pending_question": "这些里你更喜欢哪一个？",
            "pending_action": "select_recommended_item",
        },
    )

    mock_cache = MagicMock()
    mock_cache.add_message_to_context = MagicMock()
    mock_cache.update_context = MagicMock()

    with patch.object(_node_mod, "redis_cache", mock_cache):
        node.execute(state)

    assert state["pending_action"] == "select_recommended_item"
    assert state["pending_question"] == "这些里你更喜欢哪一个？"
    assert state["active_task"]["resume_mode"] == "resume_exact"
    assert state["active_task"]["resume_pending_action"] == "select_recommended_item"
def test_cancel_control_response_clears_active_task():
    node = SaveContextNode(llm=None)
    state = _make_state(
        response="好的，我先把刚才的推荐任务停在这里。",
        response_mode="cancel_current_task",
        active_task={"id": "task-1", "intent": "推荐", "status": "awaiting_user", "slots": {}},
        pending_question="这些里你更喜欢哪一个？",
        pending_action="select_recommended_item",
    )

    mock_cache = MagicMock()
    mock_cache.add_message_to_context = MagicMock()
    mock_cache.update_context = MagicMock()

    with patch.object(_node_mod, "redis_cache", mock_cache):
        node.execute(state)

    assert state["active_task"] is None
    assert state["pending_question"] is None
    assert state["pending_action"] is None
def test_answer_then_resume_preserves_original_resume_position():
    node = SaveContextNode(llm=None)
    state = _make_state(
        response="这句我先接住，刚才那个推荐我还记着。",
        response_mode="answer_then_resume",
        resume_mode="resume_exact",
        pending_question="这些里你更喜欢哪一个？",
        pending_action="select_recommended_item",
        active_task={
            "id": "task-1",
            "intent": "推荐",
            "status": "awaiting_user",
            "slots": {"language": "Java"},
            "pending_question": "这些里你更喜欢哪一个？",
            "pending_action": "select_recommended_item",
        },
    )

    mock_cache = MagicMock()
    mock_cache.add_message_to_context = MagicMock()
    mock_cache.update_context = MagicMock()

    with patch.object(_node_mod, "redis_cache", mock_cache):
        node.execute(state)

    assert state["pending_action"] == "select_recommended_item"
    assert state["pending_question"] == "这些里你更喜欢哪一个？"
    assert state["active_task"]["resume_mode"] == "resume_exact"
    assert state["active_task"]["resume_pending_action"] == "select_recommended_item"
    assert state["active_task"]["awaiting_resume_decision"] is False

