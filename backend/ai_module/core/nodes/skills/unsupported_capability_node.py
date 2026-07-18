"""Generic response node for unsupported business capabilities."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState

_SUPPORTED_SCOPE_LABELS = {
    "order_query": "订单查询",
    "product_search": "商品咨询",
    "refund_service": "售后服务",
    "coupon_system": "优惠券",
    "logistics_tracking": "物流查询",
    "cart_query": "购物车",
}


class UnsupportedCapabilityNode(BaseNode):
    """Respond safely when the user asks for a capability that is not enabled."""

    def _supported_scope_text(self) -> str:
        base_scope = ["问答", "茶品推荐", "购买指导"]
        if self.runtime is None or not hasattr(self.runtime, "get_business_info"):
            return "、".join(base_scope + ["商品咨询", "订单查询", "售后服务"])

        business_info = self.runtime.get_business_info()
        features = business_info.get("features") if isinstance(business_info, dict) else {}
        labels = list(base_scope)
        if isinstance(features, dict):
            for feature_key, label in _SUPPORTED_SCOPE_LABELS.items():
                if features.get(feature_key):
                    labels.append(label)

        deduped = []
        for label in labels:
            if label not in deduped:
                deduped.append(label)
        return "、".join(deduped)

    def execute(self, state: ConversationState) -> ConversationState:
        capability_label = state.get("unsupported_capability_label") or "这项业务"
        has_active_flow = bool(state.get("has_active_flow"))
        fallback_action = state.get("unsupported_capability_action")

        if has_active_flow:
            state["response"] = (
                f"您这句是在问“{capability_label}”相关业务。"
                "当前助手还不支持处理这类请求，我先把刚才的任务保留着；"
                "您如果想继续原来的流程，直接顺着上一条往下说就行。"
            )
            state["quick_actions"] = [fallback_action] if isinstance(fallback_action, dict) else None
            return state

        state["response"] = (
            f"当前助手还不支持处理“{capability_label}”相关业务。"
            f"您可以换成我已支持的问题，比如 {self._supported_scope_text()}。"
        )

        state["quick_actions"] = [fallback_action] if isinstance(fallback_action, dict) else None
        return state
