import pytest
from ai_module.core.nodes.policy.dialogue_state_node import DialogueStateNode


def _make_state(**overrides):
    state = {
        "timestamp": "2026-03-17T10:00:00",
        "user_message": "需要",
        "intent": "推荐",
        "dialogue_act": "confirm",
        "continue_previous_task": True,
        "slot_updates": {},
        "selected_quick_action": None,
        "active_task": {
            "id": "task-1",
            "intent": "推荐",
            "status": "awaiting_user",
            "slots": {"language": "Java"},
        },
        "task_stack": [],
        "pending_question": "需要我继续帮你搜索吗？",
        "pending_action": "answer_follow_up",
    }
    state.update(overrides)
    return state


class TestDialogueStateNode:
    def test_continue_previous_task_merges_slots(self):
        node = DialogueStateNode()
        state = _make_state(slot_updates={"budget_max": 800})

        result = node.execute(state)

        assert result["active_task"]["intent"] == "推荐"
        assert result["active_task"]["slots"]["language"] == "Java"
        assert result["active_task"]["slots"]["budget_max"] == 800
        assert result["pending_question"] is None
        assert result["pending_action"] is None
    def test_new_request_suspends_previous_task(self):
        node = DialogueStateNode()
        state = _make_state(
            user_message="先帮我查订单",
            intent="订单查询",
            dialogue_act="switch_topic",
            continue_previous_task=False,
        )

        result = node.execute(state)

        assert result["active_task"]["intent"] == "订单查询"
        assert len(result["task_stack"]) == 1
        assert result["task_stack"][0]["intent"] == "推荐"
        assert result["task_stack"][0]["status"] == "suspended"
    def test_resume_task_restores_from_stack(self):
        node = DialogueStateNode()
        state = _make_state(
            user_message="继续刚才那个",
            intent="推荐",
            dialogue_act="resume_task",
            continue_previous_task=True,
            active_task={
                "id": "task-2",
                "intent": "订单查询",
                "status": "active",
                "slots": {"selected_order_no": "ORD001"},
            },
            task_stack=[
                {
                    "id": "task-1",
                    "intent": "推荐",
                    "status": "suspended",
                    "slots": {"language": "Java", "budget_max": 800},
                }
            ],
        )

        result = node.execute(state)

        assert result["active_task"]["intent"] == "推荐"
        assert result["active_task"]["slots"]["language"] == "Java"
        assert result["active_task"]["slots"]["budget_max"] == 800
        assert len(result["task_stack"]) == 1
        assert result["task_stack"][0]["intent"] == "订单查询"
    def test_selected_action_is_folded_into_task_slots(self):
        node = DialogueStateNode()
        state = _make_state(
            user_message="第一个",
            dialogue_act="select_item",
            selected_quick_action={
                "type": "product",
                "data": {
                    "product_id": 42,
                    "title": "Java 图书管理系统",
                },
            },
        )

        result = node.execute(state)

        assert result["active_task"]["slots"]["selected_product_id"] == 42
        assert result["active_task"]["slots"]["selected_product_title"] == "Java 图书管理系统"

