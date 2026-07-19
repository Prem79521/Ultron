"""
ULTRON Windows Skill — Controls Windows settings, known directories, and drives.
"""

import os
import subprocess
import time
from typing import Dict, Any
from ultron.skills.registry import CognitiveSkill

class WindowsSkill(CognitiveSkill):
    NAME = "WindowsSkill"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        action = params.get("action", "")
        
        if action == "open_settings":
            setting_name = params.get("setting", "").lower().strip()
            uri = params.get("path")
            display_name = params.get("name") or setting_name.title()
            
            if not uri:
                settings_map = {
                    "settings": ("ms-settings:", "Settings"),
                    "bluetooth": ("ms-settings:bluetooth", "Bluetooth Settings"),
                    "wifi": ("ms-settings:network-wifi", "WiFi Settings"),
                    "display": ("ms-settings:display", "Display Settings"),
                    "sound": ("ms-settings:sound", "Sound Settings"),
                    "network": ("ms-settings:network", "Network Settings")
                }
                if setting_name in settings_map:
                    uri, display_name = settings_map[setting_name]
                else:
                    uri = f"ms-settings:{setting_name}"
                    display_name = f"{setting_name.title()} Settings"
            
            self.core.logger.info("WindowsSkill", f"Opening settings URI: {uri}")
            try:
                os.startfile(uri)
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
                self.core.logger.error("WindowsSkill", f"Failed to open settings: {e}")
                return {
                    "success": False,
                    "spoken_response": f"Failed to open {display_name}.",
                    "visual_response": f"Error: {e}",
                    "execution_time": elapsed,
                    "errors": [str(e)]
                }
                
        elif action == "open_folder":
            folder_name = params.get("folder", "").lower().strip()
            path = params.get("path")
            display_name = params.get("name") or folder_name.title()
            
            if not path:
                user_profile = os.environ.get("USERPROFILE", "C:\\Users\\default")
                folders_map = {
                    "downloads": (os.path.join(user_profile, "Downloads"), "Downloads"),
                    "desktop": (os.path.join(user_profile, "Desktop"), "Desktop"),
                    "documents": (os.path.join(user_profile, "Documents"), "Documents"),
                    "pictures": (os.path.join(user_profile, "Pictures"), "Pictures"),
                    "videos": (os.path.join(user_profile, "Videos"), "Videos")
                }
                if folder_name in folders_map:
                    path, display_name = folders_map[folder_name]
                else:
                    path = os.path.join(user_profile, folder_name.capitalize())
            
            if not (path.startswith("shell:") or os.path.exists(path)):
                elapsed = (time.time() - start_time) * 1000
                err_msg = f"Folder {display_name} does not exist."
                self.core.logger.warning("WindowsSkill", err_msg)
                return {
                    "success": False,
                    "spoken_response": err_msg,
                    "visual_response": err_msg,
                    "execution_time": elapsed,
                    "errors": [err_msg]
                }
                
            self.core.logger.info("WindowsSkill", f"Opening directory in Explorer: {path}")
            try:
                if path.startswith("shell:"):
                    import subprocess
                    subprocess.Popen(["explorer.exe", path], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.startfile(path)
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
                self.core.logger.error("WindowsSkill", f"Failed to open folder: {e}")
                return {
                    "success": False,
                    "spoken_response": f"Failed to open {display_name}.",
                    "visual_response": f"Error: {e}",
                    "execution_time": elapsed,
                    "errors": [str(e)]
                }

                
        elif action == "open_drive":
            drive_letter = params.get("drive", "").upper().strip()
            if not drive_letter or len(drive_letter) != 1 or drive_letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                elapsed = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "spoken_response": f"Drive {drive_letter} is invalid.",
                    "visual_response": f"Invalid drive letter: {drive_letter}",
                    "execution_time": elapsed,
                    "errors": [f"Invalid drive letter: {drive_letter}"]
                }
            path = f"{drive_letter}:\\"
            if not os.path.exists(path):
                elapsed = (time.time() - start_time) * 1000
                err_msg = f"Drive {drive_letter} is not available."
                self.core.logger.warning("WindowsSkill", err_msg)
                return {
                    "success": False,
                    "spoken_response": err_msg,
                    "visual_response": err_msg,
                    "execution_time": elapsed,
                    "errors": [err_msg]
                }
                
            self.core.logger.info("WindowsSkill", f"Opening drive root in Explorer: {path}")
            try:
                os.startfile(path)
                elapsed = (time.time() - start_time) * 1000
                success_msg = f"Opening {drive_letter} Drive."
                return {
                    "success": True,
                    "spoken_response": success_msg,
                    "visual_response": success_msg,
                    "execution_time": elapsed,
                    "errors": []
                }
            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                self.core.logger.error("WindowsSkill", f"Failed to open drive: {e}")
                return {
                    "success": False,
                    "spoken_response": f"Failed to open {drive_letter} Drive.",
                    "visual_response": f"Error: {e}",
                    "execution_time": elapsed,
                    "errors": [str(e)]
                }
                
        elapsed = (time.time() - start_time) * 1000
        return {
            "success": False,
            "spoken_response": f"Action {action} is not supported.",
            "visual_response": f"Unsupported WindowsSkill action: {action}",
            "execution_time": elapsed,
            "errors": [f"Unsupported action: {action}"]
        }
