from typing import Dict, Any, List, Optional
import numpy as np
from ultron.core.service_manager import UltronService

class VisionProvider(UltronService):
    """Abstract interface for vision engines."""
    def __init__(self, name: str = "VisionService"):
        super().__init__(name)

    def initialize(self) -> bool:
        return True

    def process_frame(self, frame):
        """Processes a video/camera frame."""
        raise NotImplementedError

    def configure(self, config: dict):
        pass

    def emit(self, data):
        pass

    def start(self) -> bool:
        self.active = True
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def health(self) -> str:
        return "Running" if self.active else "Offline"

    def status(self) -> str:
        return "Running" if self.active else "Offline"


class HandLandmarksResult:
    """Standardized output structure for hand landmark detectors."""
    def __init__(self, landmarks: List[List[Dict[str, float]]], handedness: List[str], hand_ids: Optional[List[int]] = None, is_predicted: Optional[List[bool]] = None, scores: Optional[List[float]] = None, world_landmarks: Optional[List[List[Dict[str, float]]]] = None):
        # landmarks is a list of hands, each hand containing 21 points with keys 'x', 'y', 'z'
        self.landmarks = landmarks
        self.handedness = handedness
        self.hand_ids = hand_ids if hand_ids is not None else list(range(len(landmarks)))
        self.is_predicted = is_predicted if is_predicted is not None else [False] * len(landmarks)
        self.scores = scores if scores is not None else [1.0] * len(landmarks)
        self.world_landmarks = world_landmarks if world_landmarks is not None else landmarks

    def is_empty(self) -> bool:
        return len(self.landmarks) == 0


class DetectedGesture:
    """Represents a classified hand gesture."""
    def __init__(self, name: str, confidence: float, data: Optional[Dict[str, Any]] = None):
        self.name = name
        self.confidence = confidence
        self.data = data or {}


class BaseCameraBackend:
    """Abstract Camera Interface class for camera/video devices."""
    def initialize(self, device_index: int = 0) -> bool:
        raise NotImplementedError

    def start(self) -> bool:
        raise NotImplementedError

    def stop(self) -> bool:
        raise NotImplementedError

    def capture_frame(self) -> Optional[np.ndarray]:
        """Captures and returns the next raw BGR/RGB video frame."""
        raise NotImplementedError

    def is_active(self) -> bool:
        raise NotImplementedError


class BaseHandTracker:
    """Abstract Hand Landmark Tracker interface."""
    def initialize(self) -> bool:
        raise NotImplementedError

    def process_frame(self, frame: np.ndarray) -> HandLandmarksResult:
        """Processes a frame and returns extracted landmarks."""
        raise NotImplementedError

    def release(self) -> None:
        raise NotImplementedError


class BaseGestureClassifier:
    """Abstract Gesture Classifier interface."""
    def classify(self, tracker_result: HandLandmarksResult) -> List[DetectedGesture]:
        """Analyzes hand landmarks and outputs a list of classified gestures."""
        raise NotImplementedError
