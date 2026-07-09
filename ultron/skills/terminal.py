"""
ULTRON Terminal Skill — Spawns PowerShell windows on Windows and runs shell executions.
"""

import subprocess
import os
from typing import Dict, Any
from ultron.skills.registry import CognitiveSkill

class TerminalSkill(CognitiveSkill):
    NAME = "Terminal"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action", "execute_command")
        
        if action == "open_terminal":
            directory = params.get("directory", os.getcwd())
            self.core.logger.info("TERMINAL", f"Opening native PowerShell window targeting directory: {directory}")
            try:
                # On Windows, spawn an independent PowerShell window
                cmd_str = f'start powershell.exe -NoExit -Command "cd \'{directory}\'"'
                subprocess.Popen(cmd_str, shell=True)
                return {"success": True, "message": f"PowerShell spawned at: {directory}"}
            except Exception as e:
                self.core.logger.error("TERMINAL", f"Failed to spawn terminal: {e}")
                return {"success": False, "error": str(e)}

        elif action == "execute_command":
            command = params.get("command")
            if not command:
                return {"success": False, "error": "Parameter 'command' is required"}
                
            self.core.logger.info("TERMINAL", f"Executing shell command: {command}")
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                return {
                    "success": result.returncode == 0,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            except subprocess.TimeoutExpired:
                self.core.logger.warning("TERMINAL", f"Command timed out: {command}")
                return {"success": False, "error": "Command execution timeout expired"}
            except Exception as e:
                self.core.logger.error("TERMINAL", f"Command failed: {e}")
                return {"success": False, "error": str(e)}

        return {"success": False, "error": f"Unknown Terminal action: {action}"}
