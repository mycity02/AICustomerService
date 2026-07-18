"""
Unit tests for ConversationSummarizer

Tests cover:
- should_summarize threshold logic
- summarize method (LLM call, history splitting, token enforcement)
- fallback_truncate method
- Token estimation helpers
"""
import sys
import os
import types
import importlib.util
from unittest.mock import MagicMock, patch

import pytest

# ── Bootstrap: set up the module hierarchy so summarizer's imports work ──

_backend_dir = os.path.join(os.path.dirname(__file__), "..")

for pkg in [
    "backend",
    "backend.services",
    "backend.ai_module.core",
]:
    if pkg not in sys.modules:
        sys.modules[pkg] = types.ModuleType(pkg)

# Load config.py
_config_path = os.path.join(_backend_dir, "config.py")
_config_spec = importlib.util.spec_from_file_location("backend.config", _config_path)
_config_mod = importlib.util.module_from_spec(_config_spec)
sys.modules["backend.config"] = _config_mod
_config_spec.loader.exec_module(_config_mod)

# Load summarizer.py
_summarizer_path = os.path.join(_backend_dir, "ai_module", "core", "summarizer.py")
_summarizer_spec = importlib.util.spec_from_file_location(
    "backend.ai_module.core.summarizer", _summarizer_path,
)
_summarizer_mod = importlib.util.module_from_spec(_summarizer_spec)
_summarizer_mod.__package__ = "backend.ai_module.core"
sys.modules["backend.ai_module.core.summarizer"] = _summarizer_mod
_summarizer_spec.loader.exec_module(_summarizer_mod)

ConversationSummarizer = _summarizer_mod.ConversationSummarizer
estimate_tokens = _summarizer_mod.estimate_tokens
estimate_history_tokens = _summarizer_mod.estimate_history_tokens
_format_history_for_summary = _summarizer_mod._format_history_for_summary


# ── Helpers ──────────────────────────────────────────────────────────

def _make_history(n: int) -> list:
    """Helper to create a conversation history with n messages."""
    return [
        {"user": f"用户消息{i}", "assistant": f"助手回复{i}", "timestamp": f"2024-01-01T00:00:{i:02d}"}
        for i in range(1, n + 1)
    ]


def _make_mock_llm(summary_text: str = "这是一段测试摘要") -> MagicMock:
    """Create a mock LLM that returns a fixed summary."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = summary_text
    mock_llm.invoke = MagicMock(return_value=mock_response)
    return mock_llm


# ── estimate_tokens tests ────────────────────────────────────────────

class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_chinese_text(self):
        assert estimate_tokens("你好世界") == 2

    def test_longer_text(self):
        text = "这是一段较长的中文文本用于测试"  # 14 chars -> 7 tokens
        assert estimate_tokens(text) == 7

    def test_single_char(self):
        assert estimate_tokens("a") == 1

    def test_english_text(self):
        text = "hello world"  # 11 chars -> 5 tokens
        assert estimate_tokens(text) == 5


# ── estimate_history_tokens tests ────────────────────────────────────

class TestEstimateHistoryTokens:
    def test_empty_history(self):
        assert estimate_history_tokens([]) == 0

    def test_single_message(self):
        history = [{"user": "你好", "assistant": "你好！"}]
        expected = estimate_tokens("你好") + estimate_tokens("你好！")
        assert estimate_history_tokens(history) == expected

    def test_multiple_messages(self):
        history = _make_history(3)
        total = 0
        for msg in history:
            total += estimate_tokens(msg["user"]) + estimate_tokens(msg["assistant"])
        assert estimate_history_tokens(history) == total


# ── _format_history_for_summary tests ────────────────────────────────

class TestFormatHistoryForSummary:
    def test_empty_history(self):
        assert _format_history_for_summary([]) == ""

    def test_single_message(self):
        history = [{"user": "你好", "assistant": "你好！"}]
        result = _format_history_for_summary(history)
        assert "用户: 你好" in result
        assert "助手: 你好！" in result

    def test_missing_fields(self):
        history = [{"user": "只有用户消息"}]
        result = _format_history_for_summary(history)
        assert "用户: 只有用户消息" in result
        assert "助手" not in result


# ── should_summarize tests ───────────────────────────────────────────

class TestShouldSummarize:
    def test_below_threshold(self):
        summarizer = ConversationSummarizer(llm=None)
        assert summarizer.should_summarize(_make_history(5)) is False

    def test_at_threshold(self):
        summarizer = ConversationSummarizer(llm=None)
        assert summarizer.should_summarize(_make_history(10)) is False

    def test_above_threshold(self):
        summarizer = ConversationSummarizer(llm=None)
        assert summarizer.should_summarize(_make_history(11)) is True

    def test_empty_history(self):
        summarizer = ConversationSummarizer(llm=None)
        assert summarizer.should_summarize([]) is False


# ── summarize tests ──────────────────────────────────────────────────

class TestSummarize:
    def test_splits_history_correctly(self):
        mock_llm = _make_mock_llm("测试摘要内容")
        summarizer = ConversationSummarizer(llm=mock_llm)
        history = _make_history(15)

        result = summarizer.summarize(history)

        assert result["summary"] == "测试摘要内容"
        assert len(result["remaining_history"]) == 10
        assert result["remaining_history"] == history[-10:]
    def test_calls_llm(self):
        mock_llm = _make_mock_llm("摘要结果")
        summarizer = ConversationSummarizer(llm=mock_llm)
        history = _make_history(12)

        summarizer.summarize(history, existing_summary="旧摘要")

        mock_llm.invoke.assert_called_once()
    def test_with_existing_summary(self):
        mock_llm = _make_mock_llm("更新后的摘要")
        summarizer = ConversationSummarizer(llm=mock_llm)
        history = _make_history(12)

        result = summarizer.summarize(history, existing_summary="旧摘要")

        assert result["summary"] == "更新后的摘要"
    def test_no_messages_to_compress(self):
        mock_llm = _make_mock_llm()
        summarizer = ConversationSummarizer(llm=mock_llm)
        history = _make_history(10)

        result = summarizer.summarize(history)

        mock_llm.invoke.assert_not_called()
        assert result["summary"] == ""
        assert result["remaining_history"] == history
    def test_preserves_remaining_history_content(self):
        mock_llm = _make_mock_llm("摘要")
        summarizer = ConversationSummarizer(llm=mock_llm)
        history = _make_history(15)

        result = summarizer.summarize(history)

        for i, msg in enumerate(result["remaining_history"]):
            original = history[5 + i]
            assert msg["user"] == original["user"]
            assert msg["assistant"] == original["assistant"]


# ── Token enforcement tests ──────────────────────────────────────────

class TestTokenEnforcement:
    def test_truncates_when_over_limit(self):
        long_summary = "摘" * 5000  # ~2500 tokens
        mock_llm = _make_mock_llm(long_summary)

        summarizer = ConversationSummarizer(llm=mock_llm)
        summarizer.max_tokens = 3000
        history = _make_history(15)

        result = summarizer.summarize(history)

        total_tokens = estimate_tokens(result["summary"]) + estimate_history_tokens(result["remaining_history"])
        assert total_tokens <= 3000
    def test_no_truncation_when_within_limit(self):
        mock_llm = _make_mock_llm("短摘要")
        summarizer = ConversationSummarizer(llm=mock_llm)
        summarizer.max_tokens = 100000
        history = _make_history(15)

        result = summarizer.summarize(history)

        assert len(result["remaining_history"]) == 10


# ── fallback_truncate tests ──────────────────────────────────────────

class TestFallbackTruncate:
    def test_returns_last_n_messages(self):
        summarizer = ConversationSummarizer(llm=None)
        history = _make_history(20)

        result = summarizer.fallback_truncate(history)

        assert result["summary"] == ""
        assert len(result["remaining_history"]) == 10
        assert result["remaining_history"] == history[-10:]

    def test_short_history(self):
        summarizer = ConversationSummarizer(llm=None)
        history = _make_history(5)

        result = summarizer.fallback_truncate(history)

        assert result["summary"] == ""
        assert len(result["remaining_history"]) == 5
        assert result["remaining_history"] == history

    def test_empty_history(self):
        summarizer = ConversationSummarizer(llm=None)
        result = summarizer.fallback_truncate([])

        assert result["summary"] == ""
        assert result["remaining_history"] == []

    def test_exactly_at_threshold(self):
        summarizer = ConversationSummarizer(llm=None)
        history = _make_history(10)

        result = summarizer.fallback_truncate(history)

        assert result["summary"] == ""
        assert len(result["remaining_history"]) == 10
        assert result["remaining_history"] == history

