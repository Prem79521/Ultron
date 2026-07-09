"""
ULTRON File System Skill — Local directory checks, file reads, file writes, and searches.
"""

import os
import shutil
from typing import Dict, Any, List
from ultron.skills.registry import CognitiveSkill

class FileSystemSkill(CognitiveSkill):
    NAME = "FileSystem"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action")
        path = params.get("path")
        
        if not action or not path:
            return {"success": False, "error": "Parameters 'action' and 'path' are required"}

        try:
            if action == "exists":
                exists = os.path.exists(path)
                is_dir = os.path.isdir(path) if exists else False
                return {"success": True, "exists": exists, "is_directory": is_dir}

            elif action == "create_directory":
                os.makedirs(path, exist_ok=True)
                self.core.logger.info("FILES", f"Created directory path: {path}")
                return {"success": True, "message": f"Created directory: {path}"}

            elif action == "read_file":
                if not os.path.isfile(path):
                    return {"success": False, "error": f"File does not exist: {path}"}
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read(4000)  # Safe bounds read
                return {"success": True, "content": content}

            elif action == "write_file":
                content = params.get("content", "")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.core.logger.info("FILES", f"Wrote content to file: {path}")
                return {"success": True, "message": f"Wrote file: {path}"}

            elif action == "delete":
                if not os.path.exists(path):
                    return {"success": False, "error": f"Path not found: {path}"}
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.core.logger.info("FILES", f"Deleted path: {path}")
                return {"success": True, "message": f"Deleted: {path}"}

            return {"success": False, "error": f"Unknown FileSystem action: {action}"}
        except Exception as e:
            self.core.logger.error("FILES", f"FileSystem action '{action}' failed on path '{path}': {e}")
            return {"success": False, "error": str(e)}
