"""
Plugin base abstractions.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AIPlugin(ABC):
    """Base contract that every infrastructure plugin must implement."""

    def __init__(self, adapter: Optional[Any] = None):
        self.adapter = adapter

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the plugin."""

    def get_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.get_schema(),
        }
