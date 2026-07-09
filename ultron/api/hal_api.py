"""
ULTRON API Layer — HAL API interface.
"""

from typing import Dict
from ultron.hal.hal_manager import hal_manager

def get_device_status() -> Dict[str, bool]:
    if hal_manager:
        return hal_manager.check_devices()
    return {"microphone": False, "speaker": False, "camera": False}

def is_device_permitted(device: str) -> bool:
    if hal_manager:
        return hal_manager.is_allowed(device)
    return False
