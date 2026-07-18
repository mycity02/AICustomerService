"""
上下文加载节点
"""
from datetime import datetime
from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState
from services.redis_cache import redis_cache


class ContextNode(BaseNode):
    """上下文加载节点"""
    
    def execute(self, state: ConversationState) -> ConversationState:
        """加载会话上下文"""
        context = redis_cache.get_context(state["session_id"])
        
        if context:
            state["conversation_history"] = context.get("history", [])
            state["user_profile"] = context.get("user_profile", {})
            state["last_intent"] = context.get("last_intent")
            state["intent_history"] = context.get("intent_history", [])
            state["conversation_summary"] = context.get("conversation_summary", "")
            state["last_quick_actions"] = context.get("last_quick_actions", [])
            state["active_task"] = context.get("active_task")
            state["task_stack"] = context.get("task_stack", [])
            state["pending_question"] = context.get("pending_question")
            state["pending_action"] = context.get("pending_action")
        else:
            state["conversation_history"] = []
            state["user_profile"] = {}
            state["last_intent"] = None
            state["intent_history"] = []
            state["conversation_summary"] = ""
            state["last_quick_actions"] = []
            state["active_task"] = None
            state["task_stack"] = []
            state["pending_question"] = None
            state["pending_action"] = None

        state["timestamp"] = datetime.now().isoformat()
        return state
