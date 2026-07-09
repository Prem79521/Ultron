"""
ULTRON Plugin Loader — Dynamically discovers and loads modular extensions.
"""

import os
import json
import importlib.util
import logging
from typing import Dict, Any, List
from ultron.core.event_bus import event_bus

class UltronPluginLoader:
    """Discovers and imports third-party extension packages during startup."""
    def __init__(self, plugins_dir: str = "plugins", skill_registry = None):
        self.plugins_dir = plugins_dir
        self.registry = skill_registry
        self.loaded_plugins: Dict[str, dict] = {}
        self._loaded_modules: Dict[str, Any] = {}
        self._loaded_folders: Dict[str, str] = {}
        self.logger = logging.getLogger("ultron-agent")

    def load_all_plugins(self):
        if not os.path.exists(self.plugins_dir):
            try:
                os.makedirs(self.plugins_dir)
            except Exception:
                return
                
        self.logger.info(f"Scanning for plugins in: {os.path.abspath(self.plugins_dir)}")
        
        # 1. Scan top-level folders for backward compatibility
        try:
            for item in os.listdir(self.plugins_dir):
                item_path = os.path.join(self.plugins_dir, item)
                if os.path.isdir(item_path) and item not in ["skills", "voice", "vision", "llm", "automation", "tts", "themes", "widgets", "integrations", "providers"]:
                    self._load_plugin_folder(item_path, item)
        except Exception as e:
            self.logger.error(f"Top-level plugin scanning exception: {e}")

        # 2. Scan categorized plugin directories
        categories = ["skills", "voice", "vision", "llm", "automation", "tts", "themes", "widgets", "integrations", "providers"]
        for cat in categories:
            cat_dir = os.path.join(self.plugins_dir, cat)
            if os.path.exists(cat_dir) and os.path.isdir(cat_dir):
                try:
                    for item in os.listdir(cat_dir):
                        item_path = os.path.join(cat_dir, item)
                        if os.path.isdir(item_path):
                            self._load_plugin_folder(item_path, f"{cat}/{item}")
                except Exception as e:
                    self.logger.error(f"Category '{cat}' plugin scanning exception: {e}")

    def _load_plugin_folder(self, folder_path: str, plugin_name: str):
        manifest_path = os.path.join(folder_path, "manifest.json")
        if not os.path.exists(manifest_path):
            return
            
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                
            name_key = manifest.get("name", plugin_name)
            if name_key in self.loaded_plugins:
                self.logger.info(f"Plugin '{name_key}' is already loaded.")
                return
            
            # 1. Version Compatibility Validation
            min_version = manifest.get("minimum_ultron_version", "1.0.0")
            if min_version > "1.0.0":
                self.logger.warning(f"Plugin '{name_key}' requires ULTRON v{min_version}. Current: 1.0.0. Skipping.")
                event_bus.publish("PLUGIN_FAILED", {"plugin": name_key, "reason": "Version incompatibility"})
                return

            # 2. Dependency Validation
            dependencies = manifest.get("dependencies", [])
            for dep in dependencies:
                if dep not in self.loaded_plugins:
                    self.logger.warning(f"Plugin '{name_key}' missing dependency '{dep}'. Skipping.")
                    event_bus.publish("PLUGIN_FAILED", {"plugin": name_key, "reason": f"Missing dependency: {dep}"})
                    return

            # 3. Permission Validation
            permissions = manifest.get("permissions", [])
            from ultron.hal.hal_manager import get_hal_manager
            hal = get_hal_manager()
            for perm in permissions:
                if hal and not hal.is_allowed(perm):
                    self.logger.warning(f"Plugin '{name_key}' requests permission '{perm}' which is disabled.")
                    event_bus.publish("WARNING_OCCURRED", {"message": f"Plugin '{name_key}' requests disabled permission '{perm}'"})

            entry_file = manifest.get("entry_point", "plugin.py")
            entry_path = os.path.join(folder_path, entry_file)
            
            if os.path.exists(entry_path):
                # Dynamically load the module
                spec = importlib.util.spec_from_file_location(f"plugin_{plugin_name.replace('/', '_')}", entry_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Lifecycle hook: on_load
                    if hasattr(module, "on_load"):
                        try:
                            module.on_load()
                        except Exception as e:
                            self.logger.error(f"Plugin '{name_key}' on_load() failed: {e}")
                    
                    # Invoke legacy plugin registration callback
                    if hasattr(module, "register_plugin"):
                        module.register_plugin(self.registry)
                        
                    # Lifecycle hook: on_enable
                    if hasattr(module, "on_enable"):
                        try:
                            module.on_enable()
                        except Exception as e:
                            self.logger.error(f"Plugin '{name_key}' on_enable() failed: {e}")
                        
                    # Track metadata
                    self.loaded_plugins[name_key] = {
                        "version": manifest.get("version", "1.0.0"),
                        "author": manifest.get("author", "Unknown"),
                        "description": manifest.get("description", ""),
                        "permissions": permissions,
                        "dependencies": dependencies,
                        "configuration": manifest.get("configuration", {}),
                        "health": "Healthy",
                        "status": "Enabled"
                    }
                    self._loaded_modules[name_key] = module
                    self._loaded_folders[name_key] = folder_path
                    
                    self.logger.info(f"Successfully loaded plugin: {name_key} (v{manifest.get('version', '1.0.0')})")
                    event_bus.publish("PLUGIN_LOADED", {"plugin": name_key})
        except Exception as e:
            self.logger.error(f"Failed to load plugin '{plugin_name}': {e}")
            event_bus.publish("ERROR_OCCURRED", {"message": f"Plugin loading failed: {plugin_name}", "error": str(e)})

    def unload_plugin(self, plugin_name: str) -> bool:
        """Dynamically unloads a loaded plugin, invoking unregistration callbacks."""
        if plugin_name in self.loaded_plugins:
            try:
                module = self._loaded_modules.get(plugin_name)
                
                # Lifecycle hook: on_disable
                if module and hasattr(module, "on_disable"):
                    try:
                        module.on_disable()
                    except Exception as e:
                        self.logger.error(f"Plugin '{plugin_name}' on_disable() failed: {e}")
                
                if module and hasattr(module, "unregister_plugin"):
                    module.unregister_plugin(self.registry)
                    
                # Lifecycle hook: on_unload
                if module and hasattr(module, "on_unload"):
                    try:
                        module.on_unload()
                    except Exception as e:
                        self.logger.error(f"Plugin '{plugin_name}' on_unload() failed: {e}")
                        
                del self.loaded_plugins[plugin_name]
                del self._loaded_modules[plugin_name]
                del self._loaded_folders[plugin_name]
                
                self.logger.info(f"Successfully unloaded plugin: {plugin_name}")
                event_bus.publish("PLUGIN_UNLOADED", {"plugin": plugin_name})
                return True
            except Exception as e:
                self.logger.error(f"Failed to unload plugin '{plugin_name}': {e}")
                event_bus.publish("ERROR_OCCURRED", {"message": f"Plugin unloading failed: {plugin_name}", "error": str(e)})
        return False

    def hot_reload(self, plugin_name: str) -> bool:
        """Performs a hot-reload sequence on a plugin."""
        folder = self._loaded_folders.get(plugin_name)
        if folder:
            self.logger.info(f"Hot-reloading plugin: {plugin_name}")
            self.unload_plugin(plugin_name)
            self._load_plugin_folder(folder, plugin_name)
            return True
        return False

    def available(self) -> bool:
        return os.path.exists(self.plugins_dir)

    def ready(self) -> bool:
        return len(self.loaded_plugins) > 0

    def load_all(self):
        self.load_all_plugins()

    def shutdown(self):
        for name in list(self.loaded_plugins.keys()):
            self.unload_plugin(name)

# Global loader instance initialized at boot (never None!)
plugin_loader = UltronPluginLoader()

def init_plugin_loader(plugins_dir: str, skill_registry) -> UltronPluginLoader:
    global plugin_loader
    plugin_loader.plugins_dir = plugins_dir
    plugin_loader.registry = skill_registry
    return plugin_loader

def get_plugin_loader() -> UltronPluginLoader:
    global plugin_loader
    return plugin_loader
