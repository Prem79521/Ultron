"""
ULTRON Projects Module — Codebase tracking and active project metadata awareness.
"""

from typing import Dict, Any

class ProjectManager:
    def __init__(self, core_system):
        self.core = core_system
        self.active_project_path = None

    def set_active_project(self, path: str) -> None:
        self.active_project_path = path

    def get_project_status(self) -> Dict[str, Any]:
        return {
            "path": self.active_project_path,
            "status": "ready"
        }
