import pytest

from ai_module.core.nodes.skills.domain_scope_guard_node import DomainScopeGuardNode


class _RuntimeStub:
    class _BusinessPack:
        business_name = "云岫茶坊"

    business_pack = _BusinessPack()

    def __init__(self, *, features=None):
        self._features = features or {}

    def get_business_info(self):
        return {"features": dict(self._features)}
def test_active_flow_redirects_back_to_current_business():
    node = DomainScopeGuardNode(runtime=_RuntimeStub(features={"order_query": True}))
    state = {
        "active_flow": "订单查询",
        "execution_context": {"business_name": "云岫茶坊"},
        "user_message": "去新疆旅行",
    }

    result = node.execute(state)

    assert "出去走走挺不错" in result["response"]
    assert "顺着刚才的订单查询任务" in result["response"]
    assert "主要还是处理" not in result["response"]
    assert "订单查询任务" in result["response"]
    assert result["quick_actions"] is None
def test_no_active_flow_lists_supported_scope():
    node = DomainScopeGuardNode(runtime=_RuntimeStub(features={"order_query": True, "refund_service": True}))
    state = {
        "active_flow": None,
        "execution_context": {"business_name": "云岫茶坊"},
        "user_message": "今天天气怎么样",
    }

    result = node.execute(state)

    assert "天气变化确实挺快" in result["response"]
    assert "云岫茶坊" in result["response"]
    assert "如果您想继续聊云岫茶坊这边" in result["response"]
    assert "订单查询" in result["response"]
    assert "售后服务" in result["response"]
    assert result["quick_actions"] is None
