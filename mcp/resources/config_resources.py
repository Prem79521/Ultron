"""
MCP Configuration Resources — Exposes sanitized config files as resources.
"""

import os
import pathlib
import json
import re
from typing import Dict, Any

WORKSPACE_ROOT = pathlib.Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))).resolve()

def _sanitize(data: dict) -> dict:
    """Sanitizes sensitive values in dicts recursively."""
    sanitized = {}
    sensitive = [r"key", r"token", r"secret", r"password", r"auth"]
    for k, v in data.items():
        if isinstance(v, dict):
            sanitized[k] = _sanitize(v)
        elif isinstance(v, list):
            sanitized[k] = [_sanitize(item) if isinstance(item, dict) else item for item in v]
        elif any(re.search(pat, k, re.IGNORECASE) for pat in sensitive):
            sanitized[k] = "[REDACTED]"
        else:
            sanitized[k] = v
    return sanitized

def register(mcp):

    @mcp.resource("config://voice.json")
    def voice_config() -> str:
        """Returns the voice settings configuration (sanitized)."""
        voice_path = WORKSPACE_ROOT / "config" / "voice.json"
        if voice_path.is_file():
            try:
                data = json.loads(voice_path.read_text(encoding="utf-8"))
                sanitized = _sanitize(data)
                return json.dumps(sanitized, indent=2)
            except Exception as exc:
                return json.dumps({"error": f"Error parsing voice config: {exc}"})
        return json.dumps({"error": "voice.json not found"})

    @mcp.resource("config://env")
    def env_config() -> str:
        """Returns the active environment variables (sanitized)."""
        env_path = WORKSPACE_ROOT / ".env"
        if not env_path.is_file():
            env_path = WORKSPACE_ROOT / ".env.example"
            
        if env_path.is_file():
            try:
                env_data = {}
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        sensitive = ["key", "token", "secret", "password", "auth"]
                        if any(pat in k.lower() for pat in sensitive) and v:
                            v = "[REDACTED]"
                        env_data[k] = v
                return json.dumps(env_data, indent=2)
            except Exception as exc:
                return json.dumps({"error": str(exc)})
        return json.dumps({"error": ".env file not found"})
