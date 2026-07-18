"""
澄清意图节点
"""
from __future__ import annotations

from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.memory_builder import MemoryContextBuilder
from ai_module.core.state import ConversationState
from langchain_core.prompts import ChatPromptTemplate


class ClarifyNode(BaseNode):
    """澄清意图节点"""

    def __init__(self, llm=None):
        super().__init__(llm=llm)
        self.memory_builder = MemoryContextBuilder()
    
    def execute(self, state: ConversationState) -> ConversationState:
        """执行意图澄清"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个友好的AI客服助手。用户的消息意图不够明确，请自然地询问用户需要什么帮助。
要求：
1. 回复要自然、友好，像真人对话
2. 简要列出可能的服务选项（问答、工单、产品咨询）
3. 邀请用户详细说明需求
4. 不要机械地列1、2、3，而是融入对话中"""),
            ("human", """用户消息：{message}
短期记忆：{short_term_memory}

请自然地询问用户需要什么帮助：""")
        ])

        response = self.llm.invoke(
            prompt.format_messages(
                message=state["user_message"],
                short_term_memory=self.memory_builder.build_short_term_memory_text(
                    state,
                    include_task_snapshot=True,
                ),
            )
        )

        state["response"] = response.content
        return state

    def execute_stream(self, state: ConversationState):
        """以流式方式执行意图澄清，逐字输出结果。"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个友好的AI客服助手。用户的消息意图不够明确，请自然地询问用户需要什么帮助。
要求：
1. 回复要自然、友好，像真人对话
2. 简要列出可能的服务选项（问答、工单、产品咨询）
3. 邀请用户详细说明需求
4. 不要机械地列1、2、3，而是融入对话中"""),
            ("human", """用户消息：{message}
短期记忆：{short_term_memory}

请自然地询问用户需要什么帮助：""")
        ])

        messages = prompt.format_messages(
            message=state["user_message"],
            short_term_memory=self.memory_builder.build_short_term_memory_text(
                state,
                include_task_snapshot=True,
            ),
        )

        full_response = ""
        for chunk in self.llm.stream(messages):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        state["response"] = full_response
