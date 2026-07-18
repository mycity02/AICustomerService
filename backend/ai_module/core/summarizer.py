"""
对话摘要压缩器。

负责将较早的对话历史压缩为摘要文本，同时保留关键上下文信息。

需求：
- 3.1：当对话历史超过阈值时自动触发摘要
- 3.2：将阈值之前的历史消息压缩为结构化摘要
- 3.3：保留阈值之后的最近原始对话
- 3.5：摘要后总令牌数不能超过配置上限
- 3.6：摘要失败时退回到截断策略
"""

import logging

from langchain_core.prompts import ChatPromptTemplate

from config import settings

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """请将以下对话历史压缩为一段简洁的摘要。
保留以下关键信息：
- 用户的主要意图和需求
- 提及的具体商品名称、订单号
- 已解决的问题和结论
- 用户的偏好信息

已有摘要：
{existing_summary}

请输出更新后的摘要，不超过 500 字。"""),
    ("human", "对话历史：\n{history_text}")
])


def estimate_tokens(text: str) -> int:
    """估算一段文本的令牌数量。

    这里采用简单启发式：中文大约每 2 个字符记作 1 个令牌，
    对中英文混合内容也能给出相对保守的估算值。
    """
    if not text:
        return 0
    return max(1, len(text) // 2)


def estimate_history_tokens(history: list) -> int:
    """估算一组历史消息的总令牌数量。

    每条历史消息默认包含“用户内容”和“助手内容”两个字段。
    """
    total = 0
    for msg in history:
        user_text = msg.get("user", "")
        assistant_text = msg.get("assistant", "")
        total += estimate_tokens(user_text) + estimate_tokens(assistant_text)
    return total


def _format_history_for_summary(history: list) -> str:
    """将历史消息整理成适合摘要提示词使用的可读文本块。"""
    lines = []
    for msg in history:
        user_text = msg.get("user", "")
        assistant_text = msg.get("assistant", "")
        if user_text:
            lines.append(f"用户: {user_text}")
        if assistant_text:
            lines.append(f"助手: {assistant_text}")
    return "\n".join(lines)


class ConversationSummarizer:
    """对话摘要压缩器。

    该组件会把较早的对话历史压缩为摘要，同时保留最近消息原文。
    优先使用大模型生成智能摘要，失败时再退回到简单截断。
    """

    def __init__(self, llm):
        self.llm = llm
        self.trigger_threshold = settings.SUMMARY_TRIGGER_THRESHOLD  # 默认 10
        self.max_tokens = settings.CONTEXT_MAX_TOKENS  # 默认 3000

    def should_summarize(self, history: list) -> bool:
        """判断是否需要触发摘要。

        当历史消息数量超过配置阈值时返回真值。

        需求 3.1：当历史长度超过摘要触发阈值时执行摘要。
        """
        return len(history) > self.trigger_threshold

    def summarize(self, history: list, existing_summary: str = "") -> dict:
        """生成较早历史对话的摘要。

        会按照触发阈值拆分历史：
        - 阈值之前的消息压缩成摘要
        - 阈值之后的消息保留为最近历史

        摘要生成后，还会校验“摘要 + 保留历史”的总令牌数，
        如果超过上下文上限，就继续裁剪最近历史。

        参数：
            第一项是完整的对话历史，
            第二项是已有摘要文本，会在新摘要中合并考虑。

        返回值：
            一个字典，其中包含：
            - 生成后的摘要文本
            - 保留的最近历史消息

        需求 3.2：阈值之前的消息压缩为摘要
        需求 3.3：阈值之后的消息保留为最近历史
        需求 3.5：总令牌数不超过上下文上限
        """
        # 先拆分出需要压缩的历史和需要保留的最近消息。
        messages_to_summarize = history[:-self.trigger_threshold] if len(history) > self.trigger_threshold else []
        remaining_history = history[-self.trigger_threshold:]

        if not messages_to_summarize:
            # 没有可压缩的历史时，直接返回原结果。
            return {
                "summary": existing_summary,
                "remaining_history": remaining_history,
            }

        # 将待压缩历史整理成供大模型使用的文本块。
        history_text = _format_history_for_summary(messages_to_summarize)

        # 调用大模型生成摘要。
        messages = SUMMARY_PROMPT.format_messages(
            existing_summary=existing_summary or "（无）",
            history_text=history_text,
        )
        response = self.llm.invoke(messages)
        summary = response.content.strip()

        logger.info(
            f"📝 摘要生成完成: 压缩了 {len(messages_to_summarize)} 条消息, "
            f"保留 {len(remaining_history)} 条最近消息"
        )

        # 摘要生成后再次检查令牌上限，必要时继续裁剪最近历史。
        remaining_history = self._enforce_token_limit(summary, remaining_history)

        return {
            "summary": summary,
            "remaining_history": remaining_history,
        }

    def _enforce_token_limit(self, summary: str, remaining_history: list) -> list:
        """确保“摘要 + 保留历史”的总令牌数不超过上限。

        如果超限，就持续移除保留历史中最早的消息，
        直到满足约束。

        需求 3.5：总令牌数不得超过上下文上限。
        """
        summary_tokens = estimate_tokens(summary)

        while remaining_history:
            history_tokens = estimate_history_tokens(remaining_history)
            total_tokens = summary_tokens + history_tokens

            if total_tokens <= self.max_tokens:
                break

            # 超限时优先移除保留历史中最早的一条消息。
            remaining_history = remaining_history[1:]
            logger.debug(
                f"令牌超限，截断最早消息。当前: {len(remaining_history)} 条, "
                f"估算令牌数: {summary_tokens + estimate_history_tokens(remaining_history)}"
            )

        return remaining_history

    def fallback_truncate(self, history: list) -> dict:
        """摘要失败时的兜底截断策略。

        该策略仅保留最近的若干条消息，不再生成摘要文本。

        需求 3.6：摘要失败时退回到截断策略。
        """
        return {
            "summary": "",
            "remaining_history": history[-self.trigger_threshold:],
        }
