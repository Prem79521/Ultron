"""
ULTRON Project Manager Skill — Manages active project sessions and recovers workspace states from UME.
"""

import json
from typing import Dict, Any
from ultron.skills.registry import CognitiveSkill

class ProjectManagerSkill(CognitiveSkill):
    NAME = "ProjectManager"

    def __init__(self, core_system, memory_manager):
        super().__init__(core_system, memory_manager)
        self._seed_rowdy_if_missing()

    def _seed_rowdy_if_missing(self):
        """Seeds project metadata into SQLite Project Memory for the demo session."""
        try:
            # Query if 'ROWDY' project is already in Project Memory
            records = self.memory.list_records("project", limit=100)
            rowdy_exists = any(r["title"] == "ROWDY" for r in records)
            
            if not rowdy_exists:
                content_payload = {
                    "directory": "c:\\Users\\craft\\Desktop\\Ultron",
                    "status": "In Development",
                    "last_milestone": "Seller Dashboard",
                    "priority_task": "Payment Integration",
                    "editor": "code",
                    "dev_server": "npm run dev"
                }
                self.memory.create_record(
                    memory_type="project",
                    title="ROWDY",
                    content=json.dumps(content_payload),
                    tags=["rowdy", "development", "active"],
                    importance_score=9
                )
                self.core.logger.info("PROJECTS", "Seeded mock ROWDY project data into Project Memory.")
        except Exception as e:
            self.core.logger.error("PROJECTS", f"Seeding ROWDY project failed: {e}")

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action", "get_status")
        project_name = params.get("project_name", "ROWDY")

        if action == "get_status":
            records = self.memory.list_records("project", limit=100)
            project_record = None
            for r in records:
                if r["title"].upper() == project_name.upper():
                    project_record = r
                    break
            
            if project_record:
                try:
                    data = json.loads(project_record["content"])
                except Exception:
                    data = {"directory": "c:\\Users\\craft\\Desktop\\Ultron"}
                
                self.core.session.set_active_project(project_name)
                return {
                    "success": True,
                    "project_name": project_name,
                    "directory": data.get("directory"),
                    "last_milestone": data.get("last_milestone", "None"),
                    "priority_task": data.get("priority_task", "None"),
                    "editor": data.get("editor", "code"),
                    "dev_server": data.get("dev_server"),
                    "raw_record": project_record
                }
            
            return {"success": False, "error": f"Project {project_name} not found in memory"}

        return {"success": False, "error": f"Unknown ProjectManager action: {action}"}
