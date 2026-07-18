import importlib.util
import os
import sys
import types

import pytest

_backend_dir = os.path.join(os.path.dirname(__file__), "..")

for pkg in [
    "backend",
    "backend.services",
    "backend.ai_module.core",
    "backend.ai_module.core.nodes",
]:
    if pkg not in sys.modules:
        sys.modules[pkg] = types.ModuleType(pkg)

_state_path = os.path.join(_backend_dir, "ai_module", "core", "state.py")
_state_spec = importlib.util.spec_from_file_location("backend.ai_module.core.state", _state_path)
_state_mod = importlib.util.module_from_spec(_state_spec)
sys.modules["backend.ai_module.core.state"] = _state_mod
_state_spec.loader.exec_module(_state_mod)

_base_path = os.path.join(_backend_dir, "ai_module", "core", "nodes", "common", "base.py")
_base_spec = importlib.util.spec_from_file_location("backend.ai_module.core.nodes.common.base", _base_path)
_base_mod = importlib.util.module_from_spec(_base_spec)
sys.modules["backend.ai_module.core.nodes.common.base"] = _base_mod
_base_spec.loader.exec_module(_base_mod)

_constants_path = os.path.join(_backend_dir, "ai_module", "core", "constants.py")
_constants_spec = importlib.util.spec_from_file_location("backend.ai_module.core.constants", _constants_path)
_constants_mod = importlib.util.module_from_spec(_constants_spec)
_constants_mod.__package__ = "backend.ai_module.core"
sys.modules["backend.ai_module.core.constants"] = _constants_mod
_constants_spec.loader.exec_module(_constants_mod)

_services_pkg = types.ModuleType("services")
_function_tools_mod = types.ModuleType("services.function_tools")
_function_tools_mod.topic_advisor_tools = []
sys.modules["services"] = _services_pkg
sys.modules["services.function_tools"] = _function_tools_mod

_node_path = os.path.join(_backend_dir, "ai_module", "core", "nodes", "skills", "topic_advisor_node.py")
_node_spec = importlib.util.spec_from_file_location(
    "backend.ai_module.core.nodes.skills.topic_advisor_node",
    _node_path,
    submodule_search_locations=[],
)
_node_mod = importlib.util.module_from_spec(_node_spec)
_node_mod.__package__ = "backend.ai_module.core.nodes"
sys.modules["backend.ai_module.core.nodes.skills.topic_advisor_node"] = _node_mod
_node_spec.loader.exec_module(_node_mod)

TopicAdvisorNode = _node_mod.TopicAdvisorNode


def _make_state(**overrides):
    state = {
        "user_message": "我都不喜欢这个",
        "dialogue_act": "reject",
        "intent": "推荐",
        "last_intent": "推荐",
        "slot_updates": {},
        "active_task": {"intent": "推荐", "status": "awaiting_user", "slots": {}},
        "last_quick_actions": [
            {"type": "product", "data": {"product_id": 101, "title": "明前西湖龙井"}},
            {"type": "product", "data": {"product_id": 202, "title": "武夷山大红袍"}},
        ],
        "quick_actions": None,
        "response": "",
        "execution_context": None,
        "topic_advisor_projects": [],
        "topic_advisor_tool_results": [],
    }
    state.update(overrides)
    return state


class TestTopicAdvisorNode:
    def test_reject_without_new_constraints_triggers_refinement_prompt(self):
        node = TopicAdvisorNode()
        state = _make_state()

        result = node.execute(state)

        assert "不太合适" in result["response"]
        assert "香型" in result["response"]
        assert result["topic_advisor_tool_results"] == []
        assert [action["label"] for action in result["quick_actions"]] == [
            "换清淡一点",
            "换便宜一点",
            "换个香型",
            "换个茶类",
        ]
        assert result["active_task"]["slots"]["rejected_product_ids"] == [101, 202]
    def test_repeated_reject_after_refinement_prompt_still_stays_in_refinement_mode(self):
        node = TopicAdvisorNode()
        state = _make_state(
            last_quick_actions=[
                {
                    "type": "button",
                    "label": "换个香型",
                    "action": "send_question",
                    "data": {"question": "换个香型，我不太喜欢这一类香气"},
                }
            ],
            active_task={
                "intent": "推荐",
                "status": "awaiting_user",
                "slots": {"rejected_product_ids": [101, 202]},
            },
        )

        result = node.execute(state)

        assert "香型" in result["response"]
        assert result["topic_advisor_tool_results"] == []

