"""
AI 工作流节点基类。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....application.ports import RuntimePort

try:
    from ai_module.core.state import ConversationState
except Exception:  # pragma: no cover - compatibility path for isolated tests
    try:
        from backend.ai_module.core.state import ConversationState
    except Exception:  # pragma: no cover - package-relative fallback
        from ...state import ConversationState


class BaseNode(ABC):
    """工作流抽象节点。"""

    def __init__(self, llm=None, runtime: "RuntimePort | None" = None):
        self.llm = llm
        self.runtime = runtime

    @abstractmethod
    def execute(self, state: ConversationState) -> ConversationState:
        """执行当前节点逻辑。"""

    def validate_state(self, state: ConversationState) -> bool:
        return True

    def on_error(self, state: ConversationState, error: Exception) -> ConversationState:
        state["response"] = f"抱歉，处理您的请求时出现了问题: {error}"
        return state
