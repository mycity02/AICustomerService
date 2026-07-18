"""Workflow package base interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from ..state import ConversationState


class BaseWorkflow(ABC):
    """Base contract for pluggable business workflows."""

    name: str = "workflow"
    stream_enabled: bool = False

    @abstractmethod
    def execute(self, state: ConversationState) -> ConversationState:
        """Execute a full workflow turn and return updated conversation state."""

    def execute_stream(self, state: ConversationState) -> Iterator[str]:
        """Stream workflow output token-by-token when supported."""
        result = self.execute(state)
        for char in result.get("response", ""):
            yield char
