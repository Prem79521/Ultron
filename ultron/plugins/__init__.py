"""
ULTRON Plugins Module — Decoupled interface for third-party integrations (GitHub, Discord, Spotify).
"""

from typing import List, Any

class PluginBase:
    def __init__(self, core_system):
        self.core = core_system

    def initialize(self) -> None:
        pass

    def get_tools(self) -> List[Any]:
        return []

class PluginRegistry:
    def __init__(self, core_system):
        self.core = core_system
        self._loaded_plugins = {}

    def load_plugin(self, name: str, plugin_class) -> None:
        instance = plugin_class(self.core)
        instance.initialize()
        self._loaded_plugins[name] = instance
