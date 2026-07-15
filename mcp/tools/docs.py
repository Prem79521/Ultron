"""
MCP Documentation, Config, and Log Tools.
"""

import os
import pathlib
import json
import re
from typing import List, Dict, Any

WORKSPACE_ROOT = pathlib.Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))).resolve()

def _sanitize_config_dict(data: dict) -> dict:
    """Sanitizes sensitive credentials (API keys, tokens, passwords) in configuration dictionaries."""
    sanitized = {}
    sensitive_patterns = [r"key", r"token", r"secret", r"password", r"auth"]
    for k, v in data.items():
        if isinstance(v, dict):
            sanitized[k] = _sanitize_config_dict(v)
        elif isinstance(v, list):
            sanitized[k] = [_sanitize_config_dict(item) if isinstance(item, dict) else item for item in v]
        elif any(re.search(pat, k, re.IGNORECASE) for pat in sensitive_patterns):
            sanitized[k] = "[REDACTED]"
        else:
            sanitized[k] = v
    return sanitized

def register(mcp):

    @mcp.tool()
    def list_documentation() -> List[Dict[str, Any]]:
        """List all markdown documentation files in the docs/ and documentation/ directories."""
        docs_list = []
        for dir_name in ["docs", "documentation"]:
            dir_path = WORKSPACE_ROOT / dir_name
            if dir_path.is_dir():
                for file_path in dir_path.glob("*.md"):
                    title = file_path.stem
                    try:
                        # Extract first header
                        content = file_path.read_text(encoding="utf-8")
                        for line in content.splitlines():
                            if line.startswith("# "):
                                title = line.replace("# ", "").strip()
                                break
                    except Exception:
                        pass
                    docs_list.append({
                        "name": file_path.name,
                        "title": title,
                        "directory": dir_name,
                        "relative_path": str(file_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
                    })
        return sorted(docs_list, key=lambda x: (x["directory"], x["name"]))

    @mcp.tool()
    def read_documentation(filename: str) -> str:
        """
        Read a documentation file.
        Filename should be the file name (e.g. '02_SYSTEM_ARCHITECTURE.md').
        """
        for dir_name in ["docs", "documentation"]:
            file_path = WORKSPACE_ROOT / dir_name / filename
            if file_path.is_file():
                # Verify security boundary
                if file_path.resolve().is_relative_to(WORKSPACE_ROOT):
                    try:
                        return file_path.read_text(encoding="utf-8")
                    except Exception as exc:
                        return f"Error reading document: {exc}"
        return f"Document '{filename}' not found in docs/ or documentation/."

    @mcp.tool()
    def read_logs(lines: int = 100) -> str:
        """Read the last N lines of the ULTRON log file (ultron.log)."""
        log_path = WORKSPACE_ROOT / "ultron.log"
        if not log_path.is_file():
            # Try checking the logs directory
            log_path = WORKSPACE_ROOT / "logs" / "ultron.log"
            if not log_path.is_file():
                return "ULTRON log file (ultron.log) not found."
                
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
            log_lines = content.splitlines()
            total = len(log_lines)
            start = max(0, total - lines)
            sliced = log_lines[start:total]
            return f"### Last {lines} log entries (Total lines: {total})\n" + "\n".join(sliced)
        except Exception as exc:
            return f"Error reading logs: {exc}"

    @mcp.tool()
    def get_project_config() -> Dict[str, Any]:
        """Get the project configurations (voice.json, environment file) with sensitive API keys redacted."""
        configs = {}
        
        # 1. voice.json
        voice_json_path = WORKSPACE_ROOT / "config" / "voice.json"
        if voice_json_path.is_file():
            try:
                data = json.loads(voice_json_path.read_text(encoding="utf-8"))
                configs["voice.json"] = _sanitize_config_dict(data)
            except Exception as exc:
                configs["voice.json"] = {"error": str(exc)}
                
        # 2. .env file
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
                        # Sanitize sensitive patterns
                        sensitive_patterns = ["key", "token", "secret", "password", "auth"]
                        if any(pat in k.lower() for pat in sensitive_patterns) and v:
                            v = "[REDACTED]"
                        env_data[k] = v
                configs[env_path.name] = env_data
            except Exception as exc:
                configs[env_path.name] = {"error": str(exc)}
                
        return configs
