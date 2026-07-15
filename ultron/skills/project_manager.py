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

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action", "get_status")
        project_name = params.get("project_name")

        if action == "create_project":
            if not project_name:
                return {"success": False, "error": "Project name is required"}
                
            import time
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
            # Check if project already exists
            records = self.memory.list_records("project", limit=100)
            if any(r["title"].upper() == project_name.upper() for r in records):
                return {"success": False, "error": f"Project \"{project_name}\" already exists in memory"}
                
            content_payload = {
                "directory": params.get("directory", "c:\\Users\\craft\\Desktop\\Ultron"),
                "status": "In Development",
                "last_milestone": "None",
                "priority_task": "None",
                "editor": "code",
                "dev_server": "npm run dev",
                "created": timestamp,
                "last_opened": timestamp,
                "summary": f"Project {project_name} initialization",
                "tags": [project_name.lower(), "active"]
            }
            
            try:
                self.memory.create_record(
                    memory_type="project",
                    title=project_name,
                    content=json.dumps(content_payload),
                    tags=[project_name.lower(), "active"],
                    importance_score=9
                )
                self.core.session.set_active_project(project_name)
                return {
                    "success": True,
                    "project_name": project_name,
                    "directory": content_payload["directory"],
                    "last_milestone": "None",
                    "priority_task": "None",
                    "editor": "code",
                    "dev_server": "npm run dev"
                }
            except Exception as e:
                return {"success": False, "error": f"Creating project failed: {e}"}

        elif action == "get_status":
            records = self.memory.list_records("project", limit=100)
            project_record = None
            
            if project_name:
                for r in records:
                    if r["title"].upper() == project_name.upper():
                        project_record = r
                        break
                if not project_record:
                    return {"success": False, "error": f"I don't have any project named \"{project_name}\" in memory."}
            else:
                if records:
                    project_record = records[0]
                    project_name = project_record["title"]
                else:
                    return {"success": False, "error": "I couldn't find an active project."}
            
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

        return {"success": False, "error": f"Unknown ProjectManager action: {action}"}
