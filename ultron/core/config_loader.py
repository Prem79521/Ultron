"""
ULTRON Configuration Manager — Resolves settings from configuration files and environment variables.
"""

import os
import json
from typing import Dict, Any

class ConfigLoader:
    """Configuration Manager responsible for retrieving settings from files and environment overrides."""
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.settings: Dict[str, Any] = {}
        self.load_all()

    def load_all(self):
        config_files = ["general", "ui", "voice", "memory", "skills"]
        for name in config_files:
            path = os.path.join(self.config_dir, f"{name}.json")
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.settings[name] = json.load(f)
                except Exception:
                    self.settings[name] = {}
            else:
                self.settings[name] = {}

    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        # Check environment variables override first: ULTRON_{SECTION}_{KEY}
        if key:
            env_key = f"ULTRON_{section.upper()}_{key.upper()}"
            if env_key in os.environ:
                return os.environ[env_key]
                
        section_data = self.settings.get(section, {})
        if key is None:
            return section_data
            
        return section_data.get(key, default)

    def health(self) -> dict:
        loaded_sections = [k for k, v in self.settings.items() if v]
        is_healthy = len(loaded_sections) > 0
        return {
            "status": "healthy" if is_healthy else "degraded",
            "details": f"Loaded config sections: {', '.join(loaded_sections)}"
        }

# Global instance for backward compatibility
config_loader = ConfigLoader()
