import os
import json
import time

PROFILE_PATH = "config/operator_profile.json"

def get_operator_profile_path() -> str:
    return PROFILE_PATH

def operator_profile_exists() -> bool:
    if not os.path.exists(PROFILE_PATH):
        return False
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            required = ["display_name", "voice_enabled", "workspace_directory"]
            return all(k in data for k in required) and len(data["display_name"].strip()) >= 2
    except Exception:
        return False

def load_operator_profile() -> dict:
    if not os.path.exists(PROFILE_PATH):
        return {}
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_operator_profile(display_name: str, voice_enabled: bool, workspace_directory: str):
    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    
    existing = load_operator_profile()
    existing.update({
        "display_name": display_name.strip(),
        "voice_enabled": voice_enabled,
        "workspace_directory": workspace_directory.strip().replace("\\", "/"),
        "last_login": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": existing.get("version", 1)
    })
    
    if "created_at" not in existing:
        existing["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4)
