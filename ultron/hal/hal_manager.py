"""
ULTRON Hardware Abstraction Layer (HAL) Manager — Coordinates hardware checks and device access policies.
"""

import logging
from typing import Dict, Any
from PySide6.QtMultimedia import QMediaDevices
from ultron.core.event_bus import event_bus

class UltronHALManager:
    """Consolidated controller querying physical hardware state and mapping permissions."""
    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.logger = logging.getLogger("ultron-agent")
        self.permissions: Dict[str, bool] = {"microphone": True, "speaker": True, "camera": True}
        self.load_permissions()

    def load_permissions(self):
        try:
            records = self.memory.list_records("preference")
            for r in records:
                if r["title"] == "permission_microphone":
                    self.permissions["microphone"] = (r["content"] == "true")
                elif r["title"] == "permission_speaker":
                    self.permissions["speaker"] = (r["content"] == "true")
                elif r["title"] == "permission_camera":
                    self.permissions["camera"] = (r["content"] == "true")
        except Exception as e:
            self.logger.error(f"Failed to load hardware permissions from database: {e}")

    def save_permission(self, device: str, allowed: bool):
        device_key = device.lower()
        if device_key in self.permissions:
            self.permissions[device_key] = allowed
            try:
                # Update UME Preference records
                pref_title = f"permission_{device_key}"
                records = self.memory.list_records("preference")
                existing = next((r for r in records if r["title"] == pref_title), None)
                val_str = "true" if allowed else "false"
                if existing:
                    self.memory.update_record("preference", existing["id"], {"content": val_str})
                else:
                    self.memory.create_record("preference", pref_title, val_str)
                    
                self.logger.info(f"Hardware permission saved: {device_key} = {allowed}")
                event_bus.publish("PERMISSION_CHANGED", {"device": device_key, "allowed": allowed})
            except Exception as e:
                self.logger.error(f"Failed to save permission '{device_key}' to database: {e}")

    def check_devices(self) -> Dict[str, bool]:
        """Queries physical system audio/video inputs using QMediaDevices."""
        inputs = len(QMediaDevices.audioInputs()) > 0
        outputs = len(QMediaDevices.audioOutputs()) > 0
        cameras = len(QMediaDevices.videoInputs()) > 0
        return {
            "microphone": inputs,
            "speaker": outputs,
            "camera": cameras
        }

    def is_allowed(self, device: str) -> bool:
        return self.permissions.get(device.lower(), False)

# Global manager instance initialized at startup
hal_manager = None

def init_hal(memory_manager) -> UltronHALManager:
    global hal_manager
    hal_manager = UltronHALManager(memory_manager)
    return hal_manager

def get_hal_manager() -> UltronHALManager:
    global hal_manager
    return hal_manager

