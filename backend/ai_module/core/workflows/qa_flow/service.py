"""QA workflow service helpers."""
from __future__ import annotations

import re
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate

from config import settings
from services.knowledge_retriever import knowledge_retriever

from ...memory_builder import MemoryContextBuilder
from ...out_of_scope_reply import compose_out_of_scope_reply

memory_builder = MemoryContextBuilder()
_file_service = None


def _get_file_service():
    global _file_service
    if _file_service is None:
        from services.file_service import FileService

        _file_service = FileService()
    return _file_service


_GREETING_RE = re.compile(
    r"^(你好|您好|hello|hi|哈喽|在吗|你是谁|你叫什么|早上好|晚上好)[!！。\s]*$",
    re.IGNORECASE,
)
_THANKS_RE = re.compile(
    r"^(谢谢|感谢|辛苦了|好的谢谢)[!！。\s]*$",
    re.IGNORECASE,
)
_BYE_RE = re.compile(r"^(再见|拜拜)[!！。\s]*$", re.IGNORECASE)
_LIGHT_CHAT_RE = re.compile(
    r"^(你好|您好|hello|hi|哈喽|在吗|你是谁|你叫什么|谢谢|感谢|好的|ok|再见|拜拜|早上好|晚上好)[!！。\s]*$",
    re.IGNORECASE,
)


SIMPLE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个友好的 AI 客服助手，请简洁回复用户。"),
        ("human", "{question}"),
    ]
)


class QAFlowService:
    """Operational logic behind the QA workflow."""

    def __init__(self, llm=None, runtime=None):
        self.llm = llm
        self.runtime = runtime

    def business_name(self, state) -> str:
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

    def business_scope_hint(self, state) -> str:
        business_id = state.get("business_id") or ""
        if business_id == "tea-retail":
            return "茶品推荐、产地风味、冲泡方法、购买流程、订单物流或售后问题"

        active_task = state.get("active_task") or {}
        active_intent = active_task.get("intent")
        if active_intent:
            return f"{self.business_name(state)}相关内容，或刚才那条{active_intent}任务相关问题"

        return f"{self.business_name(state)}相关问题、资料解读、商品或服务说明、购买流程、订单与售后问题"

    def scope_redirect_reply(self, state) -> str:
        business_name = self.business_name(state)
        scope_hint = self.business_scope_hint(state)
        return compose_out_of_scope_reply(
            state.get("user_message", ""),
            (
                f"如果您想继续聊{business_name}这边，"
                f"我可以帮您看{scope_hint}。"
            ),
            llm=self.llm,
            business_name=business_name,
            task_hint=(state.get("active_flow") or "业务咨询"),
            context_hint=(state.get("conversation_summary") or ""),
        )

    def quick_reply_for_chitchat(self, message: str) -> Optional[str]:
        text = message.strip()
        if not text:
            return None

        if _GREETING_RE.match(text):
            return "您好，我在。您可以直接告诉我您想咨询的业务问题，我来帮您处理。"
        if _THANKS_RE.match(text):
            return "不客气，您有需要继续处理的业务问题，直接告诉我就行。"
        if _BYE_RE.match(text):
            return "好的，有需要再来找我。"
        return None

    def is_light_chat(self, message: str, state) -> bool:
        if state.get("continue_previous_task"):
            return False
        return bool(_LIGHT_CHAT_RE.match(message.strip()))

    def business_profile(self) -> str:
        if self.runtime is None:
            return ""

        configured = self.runtime.get_prompt("system_prompt")
        return configured or ""

    def build_rag_prompt(self, state) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是 {business_name} 的 AI 客服助手。
你的首要职责是处理与当前业务、知识库资料和用户附件相关的问题。

规则:
1. 只有当用户问题与当前业务、知识库或附件明确相关时，才结合资料回答。
2. 如果用户问题明显超出当前业务范围，或者检索到的资料不足以支撑回答，不要强行把无关知识拼进回答。
3. 这类情况请直接礼貌拒绝，并自然引导用户回到当前业务，可参考引导方向：{scope_hint}。
4. 即使知识库里有内容，只要和用户当前问题不相关，也不要引用它们来硬答。
5. 如果问题属于业务范围，但资料不足，请明确说明当前没有足够信息，不要编造。
6. 回复保持简洁、自然、专业，优先控制在 2 到 4 句。
{conversation_summary_section}""",
                ),
                (
                    "human",
                    """当前业务说明：
{business_profile}

知识库内容：
{docs}

附件内容：
{attachments}

历史对话：
{short_term_memory}

用户问题：
{question}""",
                ),
            ]
        )

    def prepare_messages(self, state):
        user_message = state["user_message"]

        if self.is_light_chat(user_message, state):
            state["retrieved_docs"] = []
            state["sources"] = []
            state["_qa_messages"] = SIMPLE_PROMPT.format_messages(question=user_message)
            return state["_qa_messages"]

        attachment_texts = []
        file_service = _get_file_service()
        for attachment in state.get("attachments") or []:
            file_path = attachment.get("file_path", "")
            if not file_path:
                continue
            text = file_service.extract_text(file_path)
            if text:
                attachment_texts.append(f"《{attachment.get('file_name', '文件')}》\n{text[:5000]}")

        docs = knowledge_retriever.retrieve(
            query=user_message,
            collection_name="knowledge_base",
            top_k=settings.RETRIEVAL_TOP_K,
            use_hybrid=settings.RAG_USE_HYBRID_SEARCH,
            use_rerank=settings.RAG_USE_RERANK,
            use_query_rewrite=settings.RAG_USE_QUERY_REWRITE,
        )
        state["retrieved_docs"] = [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]
        state["sources"] = [doc.metadata for doc in docs]

        docs_text = "\n\n".join(f"文档{i + 1}：{doc.page_content}" for i, doc in enumerate(docs)) or "无"
        attachment_content = "\n\n".join(attachment_texts) if attachment_texts else "无"
        short_term_memory = memory_builder.build_short_term_memory_text(state)

        summary = state.get("conversation_summary", "")
        conversation_summary_section = f"\n对话历史摘要：\n{summary}" if summary else ""

        state["_qa_messages"] = self.build_rag_prompt(state).format_messages(
            business_name=self.business_name(state),
            scope_hint=self.business_scope_hint(state),
            business_profile=self.business_profile() or "当前未提供额外业务说明。",
            docs=docs_text,
            attachments=attachment_content,
            short_term_memory=short_term_memory or "无",
            question=user_message,
            conversation_summary_section=conversation_summary_section,
        )
        return state["_qa_messages"]

    def apply_quick_reply(self, state) -> None:
        quick_reply = self.quick_reply_for_chitchat(state["user_message"])
        state["_qa_quick_reply"] = quick_reply
        if quick_reply:
            state["retrieved_docs"] = []
            state["sources"] = []
            state["response"] = quick_reply

    def generate_response(self, state):
        quick_reply = state.get("_qa_quick_reply")
        if quick_reply:
            return state

        messages = state.get("_qa_messages")
        if messages is None:
            messages = self.prepare_messages(state)
        response = self.llm.invoke(messages)
        content = (response.content if hasattr(response, "content") else str(response)).strip()
        state["response"] = content or self.scope_redirect_reply(state)
        return state

    def generate_response_stream(self, state):
        quick_reply = self.quick_reply_for_chitchat(state["user_message"])
        if quick_reply:
            state["retrieved_docs"] = []
            state["sources"] = []
            state["response"] = quick_reply
            yield quick_reply
            return

        messages = state.get("_qa_messages")
        if messages is None:
            messages = self.prepare_messages(state)
        full_response = ""
        for chunk in self.llm.stream(messages):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        full_response = full_response.strip()
        if not full_response:
            full_response = self.scope_redirect_reply(state)
            yield full_response
        state["response"] = full_response
