"""
ULTRON Skills Package — Registers and exposes native execution skills.
"""

from ultron.skills.registry import CognitiveSkill, SkillRegistry
from ultron.skills.project_manager import ProjectManagerSkill
from ultron.skills.file_system import FileSystemSkill
from ultron.skills.terminal import TerminalSkill
from ultron.skills.browser import BrowserSkill
from ultron.skills.command_dispatcher import CommandDispatcher

def register_all_skills(registry: SkillRegistry):
    """Registers the native production skills onto the registry."""
    registry.register_skill("ProjectManager", ProjectManagerSkill)
    registry.register_skill("FileSystem", FileSystemSkill)
    registry.register_skill("Terminal", TerminalSkill)
    registry.register_skill("Browser", BrowserSkill)
    registry.register_skill("CommandDispatcher", CommandDispatcher)
