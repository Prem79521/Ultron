"""
ULTRON Vision Manager — Provides hardware camera integrations and screen capture feeds.
"""

import logging

class UltronVisionManager:
    """Consolidated controller wrapping camera feed captures and future object detections."""
    def __init__(self, hal_manager):
        self.hal = hal_manager
        self.logger = logging.getLogger("ultron-agent")
        self.camera_active = False

    def start_camera(self) -> bool:
        if not self.hal.is_allowed("camera"):
            self.logger.warning("Vision: Camera access denied by permissions policy.")
            return False
            
        self.camera_active = True
        self.logger.info("Vision: Camera feed activated.")
        return True

    def stop_camera(self) -> bool:
        self.camera_active = False
        self.logger.info("Vision: Camera feed deactivated.")
        return True

    def capture_frame(self) -> str:
        if not self.camera_active:
            return "Camera is Offline."
        return "Frame captured (MOCKED)"

# Global instance initialized at boot
vision_manager = None

def init_vision(hal_manager) -> UltronVisionManager:
    global vision_manager
    vision_manager = UltronVisionManager(hal_manager)
    return vision_manager
