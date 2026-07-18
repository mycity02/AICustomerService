"""Generic response node for out-of-domain requests."""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.out_of_scope_reply import compose_out_of_scope_reply
from ai_module.core.state import ConversationState

_SUPPORTED_SCOPE_LABELS = {
    "order_query": "订单查询",
    "product_search": "商品咨询",
    "refund_service": "售后服务",
    "coupon_system": "优惠券",
    "logistics_tracking": "物流查询",
    "cart_query": "购物车",
}


class DomainScopeGuardNode(BaseNode):
    """Reject out-of-domain requests and redirect back to supported business scope."""

    def _business_name(self, state: ConversationState) -> str:
        execution_context = state.get("execution_context") or {}
        if isinstance(execution_context, dict):
            business_name = execution_context.get("business_name")
            if business_name:
                return business_name

        if self.runtime is not None:
            business_pack = getattr(self.runtime, "business_pack", None)
            if business_pack is not None:
                return getattr(business_pack, "business_name", "") or "当前业务"

        return "当前业务"

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

    def _redirect_text(self, state: ConversationState, business_name: str) -> str:
        active_flow = state.get("active_flow")
        if active_flow:
            return (
                f"顺着刚才的{active_flow}任务，您可以继续往下说，我接着帮您处理。"
            )
        return (
            f"如果您想继续聊{business_name}这边，"
            f"我可以帮您看{self._supported_scope_text()}。"
        )

    def _build_context_hint(self, state: ConversationState) -> str:
        parts = []
        pending_question = (state.get("pending_question") or "").strip()
        if pending_question:
            parts.append(f"上一步在问用户：{pending_question}")
        current_step = state.get("current_step")
        if current_step:
            parts.append(f"当前停留步骤：{current_step}")
        history = state.get("conversation_history") or []
        if history:
            last = history[-1]
            last_assistant = (last.get("assistant") or "").strip()
            if last_assistant:
                parts.append(f"上一轮助手说：{last_assistant[:80]}")
        return "；".join(parts) if parts else "用户刚进入业务咨询"

    def execute(self, state: ConversationState) -> ConversationState:
        business_name = self._business_name(state)
        state["response"] = compose_out_of_scope_reply(
            state.get("user_message", ""),
            self._redirect_text(state, business_name),
            llm=self.llm,
            business_name=business_name,
            task_hint=(state.get("active_flow") or "业务咨询"),
            context_hint=self._build_context_hint(state),
        )
        state["quick_actions"] = None
        return state
