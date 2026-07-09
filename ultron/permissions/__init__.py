"""
ULTRON Permissions Module — Safety gates (Safe, Warning, Critical) for tool execution authorization.
"""

from typing import Dict, Any

class PermissionManager:
    def __init__(self, core_system):
        self.core = core_system
        self._policies = {
            "read_file": "safe",
            "search_web": "safe",
            "write_file": "warning",
            "run_command": "warning",
            "shutdown": "critical",
            "registry_edit": "critical"
        }

    async def check_permission(self, action_type: str, details: Dict[str, Any]) -> bool:
        policy = self._policies.get(action_type, "critical")
        if policy == "safe":
            return True
        elif policy == "warning":
            # In future: prompt user
            return False
        else:
            # Critical: block by default
            return False
