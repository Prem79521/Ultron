"""
ULTRON Browser Skill — Locates and launches Windows browser applications.
"""

import os
import subprocess
import time
from typing import Dict, Any
from ultron.skills.registry import CognitiveSkill

class BrowserSkill(CognitiveSkill):
    NAME = "BrowserSkill"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        browser_name = params.get("browser", "").lower().strip()
        path = params.get("path")
        
        if not path:
            from ultron.core.cognitive_os.resolver_chain import find_browser_executable_path
            path = find_browser_executable_path(browser_name)
            
        if not path or not os.path.exists(path):
            elapsed = (time.time() - start_time) * 1000
            err_msg = f"Browser {browser_name} is not supported or not installed."
            self.core.logger.warning("BrowserSkill", err_msg)
            return {
                "success": False,
                "spoken_response": f"Browser {browser_name} is not supported.",
                "visual_response": f"Unsupported browser: {browser_name}",
                "execution_time": elapsed,
                "errors": [err_msg]
            }
            
        exec_name = os.path.basename(path)
        display_name = exec_name.lower().replace(".exe", "").replace("_", " ").title()
        if display_name == "Msedge":
            display_name = "Microsoft Edge"
        
        self.core.logger.info("BrowserSkill", f"Launching {display_name} from: {path}")
        try:
            subprocess.Popen(
                [path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW | 0x00000008 # DETACHED_PROCESS
            )
            elapsed = (time.time() - start_time) * 1000
            success_msg = f"Opening {display_name}."
            return {
                "success": True,
                "spoken_response": success_msg,
                "visual_response": success_msg,
                "execution_time": elapsed,
                "errors": []
            }
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self.core.logger.error("BrowserSkill", f"Failed to launch browser: {e}")
            return {
                "success": False,
                "spoken_response": f"Failed to open {display_name}.",
                "visual_response": f"Error: {e}",
                "execution_time": elapsed,
                "errors": [str(e)]
            }

