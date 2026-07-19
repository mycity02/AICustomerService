"""工作流执行期间共享的会话状态。

这个类型字典是智能助手骨架各层之间的统一契约：
- 请求字段由接口层写入
- 上下文与对话状态在多轮之间持续维护
- 中间处理字段由理解、策略和路由节点产出
- 输出字段由最终命中的业务节点填写
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class ConversationState(TypedDict):
    # 请求输入
    user_message: str
    user_id: str
    session_id: str
    business_id: Optional[str]
    execution_context: Optional[Dict[str, Any]]
    attachments: Optional[List[Dict]]

    # 多轮上下文
    conversation_history: List[Dict[str, str]]
    user_profile: Dict[str, Any]
    last_intent: Optional[str]
    last_quick_actions: Optional[List[Dict[str, Any]]]
    active_task: Optional[Dict[str, Any]]
    task_stack: Optional[List[Dict[str, Any]]]
    pending_question: Optional[str]
    pending_action: Optional[str]

    # 中间处理态
    entry_classifier: Optional[str]
    semantic_source: Optional[str]
    guard_category: Optional[str]
    has_active_flow: bool
    active_flow: Optional[str]
    current_step: Optional[str]
    expected_user_acts: Optional[List[str]]
    expected_slot: Optional[str]
    expected_input_type: Optional[str]
    inflow_type: Optional[str]
    flow_relation: Optional[str]
    intent_hint: Optional[str]
    semantic_confidence: Optional[float]
    policy_action: Optional[str]
    skill_route: Optional[str]
    unsupported_capability: Optional[str]
    unsupported_capability_label: Optional[str]
    unsupported_capability_action: Optional[Dict[str, Any]]
    response_mode: Optional[str]
    resume_mode: Optional[str]
    dialogue_act: Optional[str]
    domain_intent: Optional[str]
    self_contained_request: bool
    continue_previous_task: bool
    need_clarification: bool
    understanding_confidence: Optional[float]
    slot_updates: Optional[Dict[str, Any]]
    reference_resolution: Optional[Dict[str, Any]]
    selected_quick_action: Optional[Dict[str, Any]]
    intent: Optional[str]
    confidence: Optional[float]
    retrieved_docs: Optional[List[Dict]]
    tool_result: Optional[Any]
    tool_used: Optional[str]

    # 最终输出
    response: str
    sources: Optional[List[Dict]]
    ticket_id: Optional[str]
    recommended_products: Optional[List[str]]
    quick_actions: Optional[List[Dict]]

    # 意图追踪
    intent_history: Optional[List[Dict[str, Any]]]
    conversation_summary: Optional[str]

    # 元数据
    timestamp: str
    processing_time: Optional[float]

    # 显式流程状态
    purchase_flow: Optional[Dict[str, Any]]
    aftersales_flow: Optional[Dict[str, Any]]

    # 智能体执行态
    topic_advisor_projects: Optional[List[Dict]]
    topic_advisor_tool_results: Optional[List[Dict]]
