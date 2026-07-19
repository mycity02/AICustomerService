"""Generic response node for out-of-domain requests."""
from __future__ import annotations

from ai_module.core.domain_scope import classify_guarded_request
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

_GUARDED_REPLY_TEMPLATES = {
    "prompt_security": (
        "为了保护系统和账号安全，我不能提供系统提示词、密钥、令牌、内部配置，"
        "也不能协助绕过安全规则。"
    ),
    "privacy": (
        "为了保护用户隐私，我只能查询和处理当前登录账户本人有权限访问的数据，"
        "不能提供其他用户的订单、地址、联系方式或账户信息。"
    ),
    "harmful": (
        "我不能提供可能造成伤害、违法或绕过安全措施的具体方法。"
    ),
    "medical": (
        "我不能替代医生进行诊断、治疗或用药建议，也不会把茶宣传为药物替代品。"
        "涉及孕期、慢性病或正在服药的情况，请先咨询医生。"
    ),
    "crisis": (
        "听起来您现在可能非常难受。若您有立即伤害自己的风险，请立刻联系当地急救或警方，"
        "并尽快联系身边可信任的人陪着您；本客服无法提供危机干预。"
    ),
}


class DomainScopeGuardNode(BaseNode):
    """Reject out-of-domain requests and redirect back to supported business scope."""

    def _guarded_reply(self, category: str, business_name: str) -> str:
        reply = _GUARDED_REPLY_TEMPLATES[category]
        if category == "crisis":
            return reply
        return (
            f"{reply}如果您需要，我仍可以继续协助处理{business_name}的茶品、订单、物流或售后问题。"
        )

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
        guard_category = state.get("guard_category") or classify_guarded_request(
            state.get("user_message", "")
        )
        if guard_category:
            state["guard_category"] = guard_category
            state["semantic_source"] = "safety_guard"
            state["response"] = self._guarded_reply(guard_category, business_name)
            state["quick_actions"] = None
            return state

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
