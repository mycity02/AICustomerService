"""
工单节点
"""
import json
from datetime import datetime
from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState
from langchain_core.prompts import ChatPromptTemplate


class TicketNode(BaseNode):
    """工单流程节点"""
    
    def execute(self, state: ConversationState) -> ConversationState:
        """执行工单创建"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个工单处理助手。从用户消息中提取工单信息。
返回JSON格式：
{{
    "title": "工单标题",
    "description": "问题描述",
    "priority": "low/medium/high/urgent",
    "category": "问题类别"
}}"""),
            ("human", """用户消息：{message}
历史对话：{history}

请提取工单信息：""")
        ])
        
        history_str = json.dumps(state["conversation_history"], ensure_ascii=False)
        
        response = self.llm.invoke(
            prompt.format_messages(
                message=state["user_message"],
                history=history_str
            )
        )
        
        try:
            ticket_info = json.loads(response.content)
            ticket_id = f"TK{datetime.now().strftime('%Y%m%d%H%M%S')}"
            state["ticket_id"] = ticket_id
            state["response"] = f"工单已创建成功！\n\n工单号：{ticket_id}\n标题：{ticket_info['title']}\n我们会尽快处理您的问题。"
        except json.JSONDecodeError:
            state["response"] = "抱歉，创建工单时出现问题。请提供更详细的问题描述。"
        
        return state
