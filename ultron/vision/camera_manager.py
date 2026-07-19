import logging
import threading
import time
from typing import Optional
import numpy as np
from ultron.core.service_manager import UltronService
from ultron.vision.base import BaseCameraBackend
from ultron.vision.camera_backend import OpenCVCameraBackend

class CameraService(UltronService):
    """Subsystem service managing camera devices and provider backends with a dedicated capture thread."""
    def __init__(self, backend: Optional[BaseCameraBackend] = None):
        super().__init__("CameraService")
        self.logger = logging.getLogger("ultron-agent")
        self.backend = backend or OpenCVCameraBackend()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        
        # Thread-safe frame and timing storage
        self._latest_frame: Optional[np.ndarray] = None
        self.capture_time_ms = 0.0
        self.camera_fps = 0.0
        self._fps_timestamps = []

    def start(self) -> bool:
        self.backend.initialize(0)
        success = self.backend.start()
        if success:
            self._running = True
            self.active = True
            self._thread = threading.Thread(target=self._capture_loop, name="CameraCaptureThread")
            self._thread.daemon = True
            self._thread.start()
            self.logger.info("CameraService started successfully. Active Provider: OpenCV (Threaded)")
        else:
            self.logger.error("CameraService failed to initialize/start backend provider.")
        return success

    def stop(self) -> bool:
        self._running = False
        self.active = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.backend.stop()
        self.logger.info("CameraService stopped.")
        return True

    def health(self) -> str:
        return "Running" if self.active and self.backend.is_active() else "Offline"

    def capture_frame(self):
        """Retrieves the latest cached camera frame thread-safely."""
        with self._lock:
            return self._latest_frame

    def _capture_loop(self):
        self.logger.info("CameraService: Threaded capture loop active.")
        while self._running:
            t0 = time.perf_counter()
            frame = self.backend.capture_frame()
            dur = (time.perf_counter() - t0) * 1000.0
            
            # FPS tracking
            now = time.time()
            self._fps_timestamps.append(now)
            while self._fps_timestamps and self._fps_timestamps[0] < now - 1.0:
                self._fps_timestamps.pop(0)
                
            with self._lock:
                self._latest_frame = frame
                self.capture_time_ms = dur
                self.camera_fps = len(self._fps_timestamps)
                
            # Yield to other threads and prevent spinning
            time.sleep(0.001)
