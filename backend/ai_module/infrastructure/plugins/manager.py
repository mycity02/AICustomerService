"""
Plugin manager.

This manager is intentionally lightweight: it owns plugin registration and
runtime discovery, while the AI runtime decides how plugins are exposed to
workflow nodes and agents.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

from .base import AIPlugin

logger = logging.getLogger(__name__)


class PluginManager:
    """Runtime registry for plugins."""

    def __init__(self):
        self.plugins: Dict[str, AIPlugin] = {}
        self._adapter = None

    def set_adapter(self, adapter: Any):
        self._adapter = adapter
        for plugin in self.plugins.values():
            plugin.adapter = adapter

    def register(self, plugin: AIPlugin):
        if plugin.name in self.plugins:
            logger.warning("Plugin %s already exists and will be replaced", plugin.name)

        if self._adapter is not None:
            plugin.adapter = self._adapter

        self.plugins[plugin.name] = plugin
        logger.info("Registered plugin: %s", plugin.name)

    def unregister(self, plugin_name: str):
        if plugin_name in self.plugins:
            del self.plugins[plugin_name]
            logger.info("Unregistered plugin: %s", plugin_name)

    def execute(self, plugin_name: str, **kwargs) -> Any:
        plugin = self.resolve_plugin(plugin_name)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_name} does not exist")

        logger.info("Executing plugin: %s", plugin.name)
        return plugin.execute(**kwargs)

    def get_plugin(self, plugin_name: str) -> Optional[AIPlugin]:
        return self.plugins.get(plugin_name)

    def resolve_plugin(self, plugin_name: str) -> Optional[AIPlugin]:
        plugin = self.plugins.get(plugin_name)
        if plugin is not None:
            return plugin

        for candidate in self.plugins.values():
            matches = getattr(candidate, "matches", None)
            if callable(matches) and matches(plugin_name):
                return candidate
        return None

    def get_plugins(
        self,
        names: Optional[Iterable[str]] = None,
        group: Optional[str] = None,
    ) -> List[AIPlugin]:
        results: List[AIPlugin] = []
        seen: set[str] = set()

        def _supports(plugin: AIPlugin) -> bool:
            if not group:
                return True
            supports_group = getattr(plugin, "supports_group", None)
            if callable(supports_group):
                return supports_group(group)
            return True

        if names is not None:
            for name in names:
                plugin = self.resolve_plugin(name)
                if plugin is None or plugin.name in seen or not _supports(plugin):
                    continue
                seen.add(plugin.name)
                results.append(plugin)
            return results

        for plugin in self.plugins.values():
            if _supports(plugin):
                results.append(plugin)
        return results

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [plugin.get_metadata() for plugin in self.plugins.values()]

    def get_plugin_schemas(self) -> Dict[str, Dict]:
        return {plugin.name: plugin.get_schema() for plugin in self.plugins.values()}

    def has_plugin(self, plugin_name: str) -> bool:
        return self.resolve_plugin(plugin_name) is not None


plugin_manager = PluginManager()
