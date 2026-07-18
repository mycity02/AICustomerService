"""
Unit tests for FunctionCallingNode (refactored to use llm.bind_tools)
"""
import sys
import os
import types
import importlib.util
from unittest.mock import MagicMock

import pytest

# ── Bootstrap: set up the module hierarchy so function_calling_node's
#    relative imports work without pulling in the full services package ──

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

# Load constants.py
_constants_path = os.path.join(_backend_dir, "ai_module", "core", "constants.py")
_constants_spec = importlib.util.spec_from_file_location("backend.ai_module.core.constants", _constants_path)
_constants_mod = importlib.util.module_from_spec(_constants_spec)
_constants_mod.__package__ = "backend.ai_module.core"
sys.modules["backend.ai_module.core.constants"] = _constants_mod
_constants_spec.loader.exec_module(_constants_mod)

# Create mock tools that mimic LangChain @tool decorated functions
def _make_mock_tool(name):
    t = MagicMock()
    t.name = name
    t.invoke = MagicMock(return_value={"success": True})
    return t

_mock_tools = [
    _make_mock_tool("query_order"),
    _make_mock_tool("search_products"),
    _make_mock_tool("get_user_info"),
    _make_mock_tool("check_inventory"),
    _make_mock_tool("get_logistics"),
    _make_mock_tool("calculate_price"),
]

# Stub services.function_tools with mock all_tools
_ft_mod = types.ModuleType("services.function_tools")
_ft_mod.all_tools = _mock_tools
sys.modules["services.function_tools"] = _ft_mod
sys.modules["services"] = types.ModuleType("services")

# Load function_calling_node.py
_fc_path = os.path.join(_backend_dir, "ai_module", "core", "nodes", "policy", "function_calling_node.py")
_fc_spec = importlib.util.spec_from_file_location(
    "backend.ai_module.core.nodes.policy.function_calling_node", _fc_path,
    submodule_search_locations=[],
)
_fc_mod = importlib.util.module_from_spec(_fc_spec)
_fc_mod.__package__ = "backend.ai_module.core.nodes"
sys.modules["backend.ai_module.core.nodes.policy.function_calling_node"] = _fc_mod
_fc_spec.loader.exec_module(_fc_mod)

FunctionCallingNode = _fc_mod.FunctionCallingNode


# ── Helpers ──────────────────────────────────────────────────────────

def _make_state(**overrides):
    """Create a minimal ConversationState dict for testing."""
    state = {
        "user_message": "查询订单 ORD123",
        "user_id": "u1",
        "session_id": "s1",
        "attachments": None,
        "conversation_history": [],
        "user_profile": {},
        "intent": "订单查询",
        "confidence": 0.9,
        "retrieved_docs": None,
        "tool_result": None,
        "tool_used": None,
        "response": "",
        "sources": None,
        "ticket_id": None,
        "recommended_products": None,
        "quick_actions": None,
        "intent_history": [],
        "conversation_summary": "",
        "timestamp": "",
        "processing_time": None,
    }
    state.update(overrides)
    return state


# ── Tests ────────────────────────────────────────────────────────────

class TestFunctionCallingNodeInit:
    """Test __init__ sets up bind_tools and tool_map correctly."""

    def test_init_binds_tools(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = MagicMock()

        node = FunctionCallingNode(mock_llm)

        mock_llm.bind_tools.assert_called_once()
        assert node.llm_with_tools is not None
        # tool_map should contain all 6 tools
        expected_names = {
            "query_order", "search_products", "get_user_info",
            "check_inventory", "get_logistics", "calculate_price",
        }
        assert set(node.tool_map.keys()) == expected_names

    def test_init_with_none_llm(self):
        node = FunctionCallingNode(None)
        assert node.llm_with_tools is None
        # tool_map should still be populated from all_tools
        assert len(node.tool_map) == 6


class TestSkipIntents:
    """Test that skip intents bypass tool calling entirely."""
    def test_skip_qa_intent(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = MagicMock()
        node = FunctionCallingNode(mock_llm)

        state = _make_state(intent="问答")
        result = node.execute(state)

        assert result["tool_result"] is None
        assert result["tool_used"] is None
    def test_skip_document_analysis_intent(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = MagicMock()
        node = FunctionCallingNode(mock_llm)

        state = _make_state(intent="文档分析")
        result = node.execute(state)

        assert result["tool_result"] is None
        assert result["tool_used"] is None
    def test_skip_ticket_intent(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = MagicMock()
        node = FunctionCallingNode(mock_llm)

        state = _make_state(intent="工单")
        result = node.execute(state)

        assert result["tool_result"] is None
        assert result["tool_used"] is None
    def test_non_skip_intent_calls_llm(self):
        mock_llm = MagicMock()
        mock_llm_with_tools = MagicMock()
        mock_response = MagicMock()
        mock_response.tool_calls = []
        mock_llm_with_tools.invoke.return_value = mock_response
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        node = FunctionCallingNode(mock_llm)

        state = _make_state(intent="订单查询")
        node.execute(state)

        mock_llm_with_tools.invoke.assert_called_once()


class TestToolCallParsing:
    """Test that tool_calls from LLM response are parsed and executed."""
    def test_single_tool_call(self):
        mock_llm = MagicMock()
        mock_llm_with_tools = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        mock_response = MagicMock()
        mock_response.tool_calls = [
            {"name": "query_order", "args": {"order_no": "ORD123"}}
        ]
        mock_llm_with_tools.invoke.return_value = mock_response

        node = FunctionCallingNode(mock_llm)

        # Replace the tool in tool_map with a fresh mock
        mock_tool = MagicMock()
        mock_tool.invoke = MagicMock(return_value={"success": True, "order_no": "ORD123"})
        mock_tool.name = "query_order"
        node.tool_map["query_order"] = mock_tool
        node._refresh_tools = MagicMock()

        state = _make_state(intent="订单查询")
        result = node.execute(state)

        assert result["tool_used"] == "query_order"
        assert len(result["tool_result"]) == 1
        assert result["tool_result"][0]["tool"] == "query_order"
        assert result["tool_result"][0]["result"] == {"success": True, "order_no": "ORD123"}
    def test_multiple_tool_calls(self):
        mock_llm = MagicMock()
        mock_llm_with_tools = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        mock_response = MagicMock()
        mock_response.tool_calls = [
            {"name": "query_order", "args": {"order_no": "ORD123"}},
            {"name": "get_logistics", "args": {"order_no": "ORD123"}},
        ]
        mock_llm_with_tools.invoke.return_value = mock_response

        node = FunctionCallingNode(mock_llm)

        # Mock both tools
        for name in ["query_order", "get_logistics"]:
            mock_tool = MagicMock()
            mock_tool.invoke = MagicMock(return_value={"success": True})
            mock_tool.name = name
            node.tool_map[name] = mock_tool

        state = _make_state(intent="订单查询")
        result = node.execute(state)

        assert result["tool_used"] == "query_order, get_logistics"
        assert len(result["tool_result"]) == 2


class TestNoToolCalls:
    """Test behavior when LLM returns no tool_calls."""
    def test_no_tool_calls_sets_none(self):
        mock_llm = MagicMock()
        mock_llm_with_tools = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        mock_response = MagicMock()
        mock_response.tool_calls = []
        mock_llm_with_tools.invoke.return_value = mock_response

        node = FunctionCallingNode(mock_llm)

        state = _make_state(intent="商品咨询")
        result = node.execute(state)

        assert result["tool_result"] is None
        assert result["tool_used"] is None


class TestErrorHandling:
    """Test that exceptions during tool execution are caught and recorded."""
    def test_tool_execution_error_recorded(self):
        mock_llm = MagicMock()
        mock_llm_with_tools = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        mock_response = MagicMock()
        mock_response.tool_calls = [
            {"name": "query_order", "args": {"order_no": "BAD"}}
        ]
        mock_llm_with_tools.invoke.return_value = mock_response

        node = FunctionCallingNode(mock_llm)

        # Mock tool that raises an exception
        mock_tool = MagicMock()
        mock_tool.invoke = MagicMock(side_effect=Exception("DB connection failed"))
        mock_tool.name = "query_order"
        node.tool_map["query_order"] = mock_tool
        node._refresh_tools = MagicMock()

        state = _make_state(intent="订单查询")
        result = node.execute(state)

        # Should NOT crash; error should be recorded
        assert result["tool_result"] is not None
        assert len(result["tool_result"]) == 1
        assert "error" in result["tool_result"][0]
        assert "DB connection failed" in result["tool_result"][0]["error"]
        assert result["tool_used"] == "query_order"
    def test_unknown_tool_name_recorded(self):
        mock_llm = MagicMock()
        mock_llm_with_tools = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        mock_response = MagicMock()
        mock_response.tool_calls = [
            {"name": "nonexistent_tool", "args": {}}
        ]
        mock_llm_with_tools.invoke.return_value = mock_response

        node = FunctionCallingNode(mock_llm)

        state = _make_state(intent="订单查询")
        result = node.execute(state)

        assert result["tool_result"] is not None
        assert len(result["tool_result"]) == 1
        assert "error" in result["tool_result"][0]
        assert "工具不存在" in result["tool_result"][0]["error"]
    def test_llm_invocation_error_does_not_crash(self):
        mock_llm = MagicMock()
        mock_llm_with_tools = MagicMock()
        mock_llm_with_tools.invoke.side_effect = Exception("LLM timeout")
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        node = FunctionCallingNode(mock_llm)

        state = _make_state(intent="订单查询")
        result = node.execute(state)

        # Should gracefully handle the error
        assert result["tool_result"] is None
        assert result["tool_used"] is None


class TestBuildMessages:
    """Test the _build_messages helper method."""

    def test_build_messages_basic(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = MagicMock()
        node = FunctionCallingNode(mock_llm)

        state = _make_state(
            intent="订单查询",
            user_message="我的订单在哪里？",
            conversation_history=[],
        )
        messages = node._build_messages(state)

        # Should have system + human message
        assert len(messages) == 2
        assert messages[0][0] == "system"
        assert messages[-1][0] == "human"
        assert "订单查询" in messages[-1][1]
        assert "我的订单在哪里？" in messages[-1][1]

    def test_build_messages_with_history(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = MagicMock()
        node = FunctionCallingNode(mock_llm)

        state = _make_state(
            intent="订单查询",
            user_message="查一下",
            conversation_history=[
                {"user": "你好", "assistant": "你好！有什么可以帮您？"},
                {"user": "我要查订单", "assistant": "请提供订单号"},
            ],
        )
        messages = node._build_messages(state)

        # system(1) + 2 history turns × 2 msgs(4) + current human(1) = 6
        assert len(messages) == 6
        assert messages[0][0] == "system"
        assert messages[1][0] == "human"
        assert messages[1][1] == "你好"
        assert messages[2][0] == "assistant"
        assert messages[-1][0] == "human"

    def test_build_messages_limits_history_to_3(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = MagicMock()
        node = FunctionCallingNode(mock_llm)

        state = _make_state(
            intent="订单查询",
            user_message="查一下",
            conversation_history=[
                {"user": f"msg{i}", "assistant": f"reply{i}"}
                for i in range(10)
            ],
        )
        messages = node._build_messages(state)

        # system(1) + 3 history turns × 2 msgs(6) + current human(1) = 8
        # Only last 3 turns from history
        assert len(messages) == 8

