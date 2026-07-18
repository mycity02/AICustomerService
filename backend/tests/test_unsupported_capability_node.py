import pytest

from ai_module.core.nodes.skills.unsupported_capability_node import UnsupportedCapabilityNode


class _RuntimeStub:
    def __init__(self, *, features=None):
        self._features = features or {}

    def get_business_info(self):
        return {"features": dict(self._features)}
def test_active_flow_reply_keeps_quick_actions_empty():
    node = UnsupportedCapabilityNode(runtime=_RuntimeStub(features={"order_query": True}))
    state = {
        "unsupported_capability_label": "优惠券",
        "has_active_flow": True,
    }

    result = node.execute(state)

    assert "优惠券" in result["response"]
    assert "保留着" in result["response"]
    assert result["quick_actions"] is None
def test_non_active_flow_uses_fallback_action_when_available():
    node = UnsupportedCapabilityNode(runtime=_RuntimeStub(features={"order_query": True}))
    state = {
        "unsupported_capability_label": "购物车",
        "has_active_flow": False,
        "unsupported_capability_action": {
            "type": "button",
            "label": "查看购物车",
            "action": "navigate",
            "data": {"path": "/cart"},
        },
    }

    result = node.execute(state)

    assert "购物车" in result["response"]
    assert result["quick_actions"][0]["action"] == "navigate"
    assert result["quick_actions"][0]["data"]["path"] == "/cart"
