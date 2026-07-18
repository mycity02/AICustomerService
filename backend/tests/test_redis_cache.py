"""
Unit tests for redis_cache.py — verifying intent_history and conversation_summary
support in get_context and update_context methods.
"""
import sys
import os
import importlib.util

import pytest

# Import MemoryCache directly from the file to avoid the heavy services/__init__.py chain
_spec = importlib.util.spec_from_file_location(
    "redis_cache",
    os.path.join(os.path.dirname(__file__), "..", "services", "redis_cache.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
MemoryCache = _mod.MemoryCache


@pytest.fixture
def cache():
    """Provide a fresh MemoryCache instance for each test."""
    c = MemoryCache()
    c.connect()
    yield c
    c.disconnect()


# ── get_context defaults ──────────────────────────────────────────────
def test_get_context_returns_none_for_unknown_session(cache: MemoryCache):
    result = cache.get_context("nonexistent")
    assert result is None
def test_get_context_returns_default_new_fields(cache: MemoryCache):
    """Existing contexts without intent_history / conversation_summary
    should return [] and '' respectively (backward compatibility)."""
    # Manually seed a legacy context without the new fields
    cache._cache["session:legacy:context"] = {
        "history": [{"user": "hi", "assistant": "hello", "timestamp": "t"}],
        "user_profile": {"name": "Alice"},
        "last_intent": "问答",
        "updated_at": "2024-01-01T00:00:00",
    }

    ctx = cache.get_context("legacy")
    assert ctx is not None
    assert ctx["intent_history"] == []
    assert ctx["conversation_summary"] == ""
    assert ctx["last_quick_actions"] == []
    assert ctx["active_task"] is None
    assert ctx["task_stack"] == []
    assert ctx["pending_question"] is None
    assert ctx["pending_action"] is None
    # Original fields still present
    assert len(ctx["history"]) == 1
    assert ctx["last_intent"] == "问答"
def test_get_context_returns_stored_new_fields(cache: MemoryCache):
    """When intent_history and conversation_summary are stored, get_context returns them."""
    intent_history = [
        {"intent": "商品咨询", "confidence": 0.95, "turn": 1, "timestamp": "t1"},
    ]
    cache._cache["session:s1:context"] = {
        "history": [],
        "user_profile": {},
        "last_intent": "商品咨询",
        "intent_history": intent_history,
        "conversation_summary": "User asked about products.",
        "updated_at": "2024-01-01T00:00:00",
    }

    ctx = cache.get_context("s1")
    assert ctx["intent_history"] == intent_history
    assert ctx["conversation_summary"] == "User asked about products."
    assert ctx["last_quick_actions"] == []
    assert ctx["task_stack"] == []


# ── update_context with new fields ───────────────────────────────────
def test_update_context_persists_intent_history(cache: MemoryCache):
    intent_history = [
        {"intent": "订单查询", "confidence": 0.8, "turn": 1, "timestamp": "t1"},
        {"intent": "商品咨询", "confidence": 0.9, "turn": 2, "timestamp": "t2"},
    ]
    cache.update_context("s2", intent_history=intent_history)

    ctx = cache.get_context("s2")
    assert ctx["intent_history"] == intent_history
def test_update_context_persists_conversation_summary(cache: MemoryCache):
    summary = "The user inquired about order ORD123 and product availability."
    cache.update_context("s3", conversation_summary=summary)

    ctx = cache.get_context("s3")
    assert ctx["conversation_summary"] == summary
def test_update_context_persists_last_quick_actions(cache: MemoryCache):
    quick_actions = [{"type": "button", "label": "查看详情"}]
    cache.update_context("s3b", last_quick_actions=quick_actions)

    ctx = cache.get_context("s3b")
    assert ctx["last_quick_actions"] == quick_actions
def test_update_context_persists_dialogue_state_fields(cache: MemoryCache):
    active_task = {"id": "task-1", "intent": "推荐", "status": "awaiting_user"}
    task_stack = [{"id": "task-0", "intent": "订单查询", "status": "suspended"}]
    cache.update_context(
        "s3c",
        active_task=active_task,
        task_stack=task_stack,
        pending_question="要继续吗？",
        pending_action="answer_follow_up",
    )

    ctx = cache.get_context("s3c")
    assert ctx["active_task"] == active_task
    assert ctx["task_stack"] == task_stack
    assert ctx["pending_question"] == "要继续吗？"
    assert ctx["pending_action"] == "answer_follow_up"
def test_update_context_can_clear_pending_fields(cache: MemoryCache):
    cache.update_context("s3d", pending_question="继续吗？", pending_action="answer_follow_up")
    cache.update_context("s3d", pending_question=None, pending_action=None)

    ctx = cache.get_context("s3d")
    assert ctx["pending_question"] is None
    assert ctx["pending_action"] is None
def test_update_context_does_not_overwrite_unset_fields(cache: MemoryCache):
    """Calling update_context with only one new field should not erase the other."""
    cache.update_context(
        "s4",
        intent_history=[{"intent": "问答", "confidence": 0.7, "turn": 1, "timestamp": "t"}],
        conversation_summary="initial summary",
    )
    # Now update only the summary
    cache.update_context("s4", conversation_summary="updated summary")

    ctx = cache.get_context("s4")
    assert len(ctx["intent_history"]) == 1  # unchanged
    assert ctx["conversation_summary"] == "updated summary"
def test_update_context_preserves_original_fields(cache: MemoryCache):
    """Updating new fields should not affect existing original fields."""
    cache.update_context("s5", last_intent="问答", user_profile={"name": "Bob"})
    cache.update_context(
        "s5",
        intent_history=[{"intent": "问答", "confidence": 0.85, "turn": 1, "timestamp": "t"}],
    )

    ctx = cache.get_context("s5")
    assert ctx["last_intent"] == "问答"
    assert ctx["user_profile"] == {"name": "Bob"}
    assert len(ctx["intent_history"]) == 1
def test_update_context_all_fields_together(cache: MemoryCache):
    """All fields (old + new) can be set in a single call."""
    history = [{"user": "hi", "assistant": "hello", "timestamp": "t"}]
    intent_history = [{"intent": "商品推荐", "confidence": 0.92, "turn": 1, "timestamp": "t"}]
    summary = "Comprehensive summary."

    cache.update_context(
        "s6",
        history=history,
        user_profile={"vip": True},
        last_intent="商品推荐",
        intent_history=intent_history,
        conversation_summary=summary,
    )

    ctx = cache.get_context("s6")
    assert ctx["history"] == history
    assert ctx["user_profile"] == {"vip": True}
    assert ctx["last_intent"] == "商品推荐"
    assert ctx["intent_history"] == intent_history
    assert ctx["conversation_summary"] == summary
    assert ctx["updated_at"] is not None

