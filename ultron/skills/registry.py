"""
ULTRON Skills Registry & Plugin Loader — Dynamically discovers and registers execution skills.
"""

import os
import importlib.util
from typing import Dict, Any, List, Type, Optional
from ultron.core import ultron_logger

class CognitiveSkill:
    """Base interface class for all ULTRON execution skills."""
    def __init__(self, core_system, memory_manager):
        self.core = core_system
        self.memory = memory_manager

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def health(self) -> dict:
        return {"status": "healthy", "details": f"Skill {self.__class__.__name__} online."}

class SkillRegistry:
    """Registry that hosts built-in capabilities and loads future plugins dynamically."""
    def __init__(self, core_system, memory_manager):
        self.core = core_system
        self.memory = memory_manager
        self._skills: Dict[str, CognitiveSkill] = {}

    def register_skill(self, name: str, skill_class: Type[CognitiveSkill]):
        skill_instance = skill_class(self.core, self.memory)
        self._skills[name.lower()] = skill_instance
        self.core.logger.info("SKILLS", f"Registered skill: {name}")

    def get_skill(self, name: str) -> Optional[CognitiveSkill]:
        return self._skills.get(name.lower())

    def load_plugins(self, plugin_directories: List[str]):
        """
        Placeholder Plugin Discovery Loader.
        Scans directories for future plugins inheriting from CognitiveSkill.
        """
        self.core.logger.info("SKILLS", f"Scanning directories for plugins: {plugin_directories}")
        for directory in plugin_directories:
            if not os.path.isdir(directory):
                continue
            for filename in os.listdir(directory):
                if filename.endswith(".py") and not filename.startswith("__"):
                    path = os.path.join(directory, filename)
                    try:
                        # Establish module import spec
                        module_name = f"ultron.plugins.{filename[:-3]}"
                        spec = importlib.util.spec_from_file_location(module_name, path)
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            
                            # Inspect module classes
                            for attr_name in dir(mod):
                                attr = getattr(mod, attr_name)
                                if isinstance(attr, type) and issubclass(attr, CognitiveSkill) and attr is not CognitiveSkill:
                                    skill_name = getattr(attr, "NAME", attr_name)
                                    self.register_skill(skill_name, attr)
                    except Exception as e:
                        self.core.logger.error("SKILLS", f"Failed to load plugin {filename}: {e}")

    def health(self) -> dict:
        loaded_skills = list(self._skills.keys())
        is_healthy = len(loaded_skills) >= 5  # Expect 5 native skills
        return {
            "status": "healthy" if is_healthy else "degraded",
            "details": f"Registered skills ({len(loaded_skills)}): {', '.join(loaded_skills)}"
        }

def register_all_skills(registry: SkillRegistry):
    """Registers the native production skills onto the registry."""
    from ultron.skills.project_manager import ProjectManagerSkill
    from ultron.skills.file_system import FileSystemSkill
    from ultron.skills.terminal import TerminalSkill
    from ultron.skills.browser import BrowserSkill
    from ultron.skills.command_dispatcher import CommandDispatcher

    registry.register_skill("ProjectManager", ProjectManagerSkill)
    registry.register_skill("FileSystem", FileSystemSkill)
    registry.register_skill("Terminal", TerminalSkill)
    registry.register_skill("Browser", BrowserSkill)
    registry.register_skill("CommandDispatcher", CommandDispatcher)
