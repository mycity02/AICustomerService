"""
Unit tests for QANode conversation_summary injection.

Tests verify that:
- Non-empty conversation_summary is injected into the RAG prompt
- Empty conversation_summary results in no summary section in the prompt
- The summary is clearly labeled in the prompt
"""
import sys
import os
import types
import importlib.util
from unittest.mock import MagicMock, patch

import pytest

# ── Bootstrap: set up module hierarchy so qa_node imports work ──

_backend_dir = os.path.join(os.path.dirname(__file__), "..")

for pkg in [
    "backend",
    "backend.services",
    "backend.ai_module.core",
    "backend.ai_module.core.nodes",
]:
    if pkg not in sys.modules:
        sys.modules[pkg] = types.ModuleType(pkg)

# Stub config
_config_path = os.path.join(_backend_dir, "config.py")
_config_spec = importlib.util.spec_from_file_location("backend.config", _config_path)
_config_mod = importlib.util.module_from_spec(_config_spec)
sys.modules["backend.config"] = _config_mod
sys.modules["config"] = _config_mod
_config_spec.loader.exec_module(_config_mod)

# Stub knowledge_retriever
_kr_mod = types.ModuleType("services.knowledge_retriever")
_mock_retriever = MagicMock()
_mock_retriever.retrieve = MagicMock(return_value=[])
_kr_mod.knowledge_retriever = _mock_retriever
sys.modules["services.knowledge_retriever"] = _kr_mod

# Stub file_service
_fs_mod = types.ModuleType("services.file_service")
_fs_mod.FileService = MagicMock
sys.modules["services.file_service"] = _fs_mod

# Stub base node
_base_mod = types.ModuleType("backend.ai_module.core.nodes.common.base")


class _FakeBaseNode:
    def __init__(self, llm=None, runtime=None):
        self.llm = llm
        self.runtime = runtime


_base_mod.BaseNode = _FakeBaseNode
sys.modules["backend.ai_module.core.nodes.common.base"] = _base_mod
sys.modules["ai_module.core.nodes.common.base"] = _base_mod

# Stub state
_state_path = os.path.join(_backend_dir, "ai_module", "core", "state.py")
if os.path.exists(_state_path):
    _state_spec = importlib.util.spec_from_file_location("backend.ai_module.core.state", _state_path)
    _state_mod = importlib.util.module_from_spec(_state_spec)
    sys.modules["backend.ai_module.core.state"] = _state_mod
    _state_spec.loader.exec_module(_state_mod)
else:
    _state_mod = types.ModuleType("backend.ai_module.core.state")
    _state_mod.ConversationState = dict
    sys.modules["backend.ai_module.core.state"] = _state_mod

_memory_builder_path = os.path.join(_backend_dir, "ai_module", "core", "memory_builder.py")
_memory_builder_spec = importlib.util.spec_from_file_location(
    "backend.ai_module.core.memory_builder",
    _memory_builder_path,
)
_memory_builder_mod = importlib.util.module_from_spec(_memory_builder_spec)
sys.modules["backend.ai_module.core.memory_builder"] = _memory_builder_mod
_memory_builder_spec.loader.exec_module(_memory_builder_mod)

# Now load qa_node
_qa_path = os.path.join(_backend_dir, "ai_module", "core", "nodes", "skills", "qa_node.py")
_qa_spec = importlib.util.spec_from_file_location("backend.ai_module.core.nodes.skills.qa_node", _qa_path)
_qa_mod = importlib.util.module_from_spec(_qa_spec)
_qa_mod.__package__ = "backend.ai_module.core.nodes"
sys.modules["backend.ai_module.core.nodes.skills.qa_node"] = _qa_mod
_qa_spec.loader.exec_module(_qa_mod)

QANode = _qa_mod.QANode


# ── Helpers ──────────────────────────────────────────────────────────

def _make_state(user_message="请问这个商品怎么样？", conversation_summary="", **overrides):
    state = {
        "user_message": user_message,
        "conversation_history": [],
        "conversation_summary": conversation_summary,
        "attachments": [],
        "retrieved_docs": [],
        "sources": [],
        "continue_previous_task": False,
    }
    state.update(overrides)
    return state


# ── Tests ────────────────────────────────────────────────────────────

class TestQANodeSummaryInjection:
    def test_summary_injected_when_present(self):
        """Non-empty conversation_summary should appear in the prompt."""
        summary_text = "用户之前咨询了订单ORD123的物流状态"
        state = _make_state(conversation_summary=summary_text)
        node = QANode(llm=MagicMock())

        messages = node._prepare_messages(state)

        system_content = messages[0].content
        assert "对话历史摘要" in system_content
        assert summary_text in system_content
    def test_no_summary_section_when_empty(self):
        """Empty conversation_summary should not add a summary section."""
        state = _make_state(conversation_summary="")
        node = QANode(llm=MagicMock())

        messages = node._prepare_messages(state)

        system_content = messages[0].content
        assert "对话历史摘要" not in system_content
    def test_no_summary_section_when_missing(self):
        """Missing conversation_summary key should not add a summary section."""
        state = _make_state()
        del state["conversation_summary"]
        node = QANode(llm=MagicMock())

        messages = node._prepare_messages(state)

        system_content = messages[0].content
        assert "对话历史摘要" not in system_content
    def test_chitchat_skips_rag_prompt(self):
        """Chitchat messages should use SIMPLE_PROMPT, not RAG_PROMPT with summary."""
        state = _make_state(user_message="你好", conversation_summary="一些摘要内容")
        node = QANode(llm=MagicMock())

        messages = node._prepare_messages(state)

        system_content = messages[0].content
        assert "对话历史摘要" not in system_content
    def test_short_reply_with_continuation_uses_rag_prompt(self):
        """Continuation replies should not be downgraded to chitchat by length."""
        _mock_retriever.retrieve.reset_mock()
        state = _make_state(
            user_message="需要",
            conversation_summary="用户上一轮在问推荐项目",
            continue_previous_task=True,
        )
        node = QANode(llm=MagicMock())

        messages = node._prepare_messages(state)

        system_content = messages[0].content
        assert "对话历史摘要" in system_content
        _mock_retriever.retrieve.assert_called()

