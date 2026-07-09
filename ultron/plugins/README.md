# ULTRON Plugins Module

## Purpose
The Plugins module provides an extensible framework to load, unload, configure, and execute third-party integrations (e.g., GitHub, Discord, Spotify, ROWDY, Home Assistant, browser automation plugins) without modifying the core system codebase.

## Responsibilities
*   **Plugin Registration**: Registers and mounts external services and APIs at runtime.
*   **Sandboxing**: Isolates plugin errors so that failures do not crash the core voice pipeline.
*   **Resource Mapping**: Exposes custom tools and resources to the MCP server from loaded plugins.

## Public Interfaces
*   `class PluginBase`: Parent interface class for plugins.
    *   `def initialize(core: Any) -> None`
    *   `def get_tools() -> List[Any]`
*   `class PluginRegistry`: Registry controller.
    *   `def load_plugin(plugin_name: str) -> None`
    *   `def unload_plugin(plugin_name: str) -> None`

## Dependencies
*   `ultron.core` for registration hooks.

## Future Expansion
*   Implement dynamic hot-loading from a local user plugins directory.
*   Support remote plugin repositories with signed validation manifests.

## Design Notes
*   **Open-Closed Principle**: Core ULTRON code must not import or depend on specific plugin classes. Plugins must inherit from `PluginBase` and register themselves.
