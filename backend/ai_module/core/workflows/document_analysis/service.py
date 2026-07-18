"""Document analysis workflow service helpers."""
from __future__ import annotations

import time
import logging

from langchain_core.prompts import ChatPromptTemplate
from services.paddleocr_service import vision_llm_service

logger = logging.getLogger(__name__)
_file_service = None

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}


def _get_file_service():
    global _file_service
    if _file_service is None:
        from services.file_service import FileService

        _file_service = FileService()
    return _file_service


class DocumentAnalysisService:
    """Operational logic behind the document analysis workflow."""

    SYSTEM_PROMPT = """你是云岫茶坊的智能客服助手，服务于茶叶销售与智能导购平台。
用户上传了文件或图片，请结合平台业务场景来分析和回复。

平台业务：销售绿茶、红茶、乌龙茶、白茶、普洱茶和花茶，并提供选茶、冲泡、订单物流与售后服务。

回复策略：
- 如果是商品截图/商品页面：识别出商品信息，主动介绍该商品的特点，询问用户是否需要了解更多详情或购买
- 如果是订单截图/支付截图：识别订单信息，询问用户遇到了什么问题，主动提供帮助
- 如果是错误截图/bug截图：分析错误内容，提供可能的解决方案或建议提交工单
- 如果是茶叶包装、配料或冲泡说明：识别产地、规格、保质期和冲泡参数，并结合平台茶品解读
- 如果是其他类型文档：提取关键信息并给出专业解读

要求：
1. 回复要贴合客服场景，不要做纯粹的文档分析报告
2. 主动引导用户下一步操作（如查看商品、下单、提交工单等）
3. 语言亲切专业，像真人客服一样交流
4. 如果能识别出具体商品，主动关联平台商品信息"""

    def __init__(self, llm=None, runtime=None):
        self.llm = llm
        self.runtime = runtime

    def get_attachment_text(self, att: dict) -> tuple[str, str, dict]:
        """获取附件文本内容，返回“正文、展示名、附加信息”。
        """
        file_service = _get_file_service()
        file_path = att.get("file_path", "")
        file_name = att.get("file_name", "未知文件")
        file_id = att.get("file_id", "")
        ext = file_path.rsplit(".", 1)[1].lower() if "." in file_path else ""
        metadata = {}

        extracted_text = att.get("extracted_text")
        if extracted_text:
            logger.info("使用已提取的图片文字: %s", file_name)
            metadata = {
                "image_intent": att.get("image_intent"),
                "image_description": att.get("image_description"),
            }
            return extracted_text[:8000], f"{file_name} (图片文字已提取)", metadata

        if ext in IMAGE_EXTENSIONS:
            if file_id:
                for _ in range(4):
                    analysis = file_service.get_image_analysis(file_id)
                    if analysis and analysis.get("extracted_text"):
                        logger.info("从后台分析结果获取图片文字: %s", file_name)
                        metadata = {
                            "image_intent": analysis.get("image_intent"),
                            "image_description": analysis.get("image_description"),
                        }
                        return analysis["extracted_text"][:8000], f"{file_name} (图片文字已提取)", metadata
                    time.sleep(0.5)

            if file_path and vision_llm_service.is_available():
                logger.info("直接调用视觉LLM提取图片文字: %s", file_name)
                text = vision_llm_service.extract_text_from_image_file(file_path)
                if text:
                    return text[:8000], f"{file_name} (图片文字已提取)", metadata

            logger.warning("无法提取图片文字: %s", file_name)
            return "", "", metadata

        if file_path:
            text = file_service.extract_text(file_path)
            if text:
                return text[:8000], file_name, metadata

        return "", "", metadata

    def build_prompt(self, file_names, content, user_message, image_context):
        human_msg = f"用户上传的文件：{file_names}\n\n文件内容：\n{content}"
        if user_message:
            human_msg = f"用户消息：{user_message}\n\n{human_msg}"
        if image_context:
            human_msg += f"\n\n图片分析参考：{image_context}"
        human_msg += "\n\n请结合平台业务场景回复用户："

        prompt = ChatPromptTemplate.from_messages(
            [("system", self.SYSTEM_PROMPT), ("human", human_msg)]
        )
        return prompt.format_messages()

    def prepare_attachments(self, state):
        logger.info("文档分析节点: attachments=%s", len(state.get("attachments", [])))

        attachment_texts = []
        attachment_names = []
        image_context_parts = []

        for att in state.get("attachments") or []:
            text, name, metadata = self.get_attachment_text(att)
            if text:
                attachment_texts.append(text)
                attachment_names.append(name)
            if metadata.get("image_intent"):
                image_context_parts.append(
                    f"意图={metadata['image_intent']}, 描述={metadata.get('image_description', '')}"
                )

        state["_document_attachment_texts"] = attachment_texts
        state["_document_attachment_names"] = attachment_names
        state["_document_image_context"] = "; ".join(image_context_parts) if image_context_parts else ""
        return attachment_texts

    def generate_response(self, state):
        attachment_texts = state.get("_document_attachment_texts")
        attachment_names = state.get("_document_attachment_names")
        image_context = state.get("_document_image_context", "")
        if attachment_texts is None:
            self.prepare_attachments(state)
            attachment_texts = state.get("_document_attachment_texts")
            attachment_names = state.get("_document_attachment_names")
            image_context = state.get("_document_image_context", "")

        if not attachment_texts:
            state["response"] = "我注意到您上传了文件，但无法读取文件内容。请确保文件格式正确（支持 PDF、Word、TXT、图片等格式）。"
            return state

        all_content = "\n\n---\n\n".join(attachment_texts)
        user_message = state.get("user_message", "").strip()
        messages = self.build_prompt(", ".join(attachment_names), all_content, user_message, image_context)
        response = self.llm.invoke(messages)

        state["response"] = response.content
        state["sources"] = [{"type": "attachment", "files": attachment_names}]
        return state

    def generate_response_stream(self, state):
        attachment_texts = state.get("_document_attachment_texts")
        attachment_names = state.get("_document_attachment_names")
        image_context = state.get("_document_image_context", "")
        if attachment_texts is None:
            self.prepare_attachments(state)
            attachment_texts = state.get("_document_attachment_texts")
            attachment_names = state.get("_document_attachment_names")
            image_context = state.get("_document_image_context", "")

        if not attachment_texts:
            state["response"] = "我注意到您上传了文件，但无法读取文件内容。请确保文件格式正确（支持 PDF、Word、TXT、图片等格式）。"
            yield state["response"]
            return

        all_content = "\n\n---\n\n".join(attachment_texts)
        user_message = state.get("user_message", "").strip()
        messages = self.build_prompt(", ".join(attachment_names), all_content, user_message, image_context)

        full_response = ""
        for chunk in self.llm.stream(messages):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        state["response"] = full_response
        state["sources"] = [{"type": "attachment", "files": attachment_names}]
