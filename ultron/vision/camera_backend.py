import logging
from typing import Optional
import cv2
import numpy as np
from ultron.vision.base import BaseCameraBackend

class OpenCVCameraBackend(BaseCameraBackend):
    """Camera backend implementation using OpenCV."""
    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.device_index = 0
        self.active = False
        self.logger = logging.getLogger("ultron-agent")

    def initialize(self, device_index: int = 0) -> bool:
        self.device_index = device_index
        return True

    def start(self) -> bool:
        try:
            # CAP_DSHOW on Windows provides fast, direct camera initialization
            self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                # Fallback to default API backend
                self.cap = cv2.VideoCapture(self.device_index)
            
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.active = True
                self.logger.info(f"OpenCVCameraBackend successfully opened camera device index: {self.device_index}")
                return True
            else:
                self.logger.error(f"OpenCVCameraBackend failed to open camera device index: {self.device_index}")
                return False
        except Exception as e:
            self.logger.error(f"Error starting OpenCVCameraBackend: {e}")
            return False

    def stop(self) -> bool:
        self.active = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.logger.info("OpenCVCameraBackend stopped.")
        return True

    def capture_frame(self) -> Optional[np.ndarray]:
        if not self.active or not self.cap:
            return None
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def is_active(self) -> bool:
        return self.active and self.cap is not None and self.cap.isOpened()
