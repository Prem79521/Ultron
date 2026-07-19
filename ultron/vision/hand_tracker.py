import os
import cv2
import numpy as np
import logging
import time
from typing import Dict, Any, List
from ultron.vision.base import BaseHandTracker, HandLandmarksResult

class MediaPipeHandTracker(BaseHandTracker):
    """Hand landmark tracker implementation using Google MediaPipe Tasks API."""
    def __init__(self):
        self.detector = None
        self.active = False
        self.logger = logging.getLogger("ultron-agent")
        self.last_timestamp_ms = 0

    def initialize(self) -> bool:
        try:
            import mediapipe.tasks as mp_tasks
            BaseOptions = mp_tasks.BaseOptions
            vision = mp_tasks.vision
            
            # Resolve local model path
            model_path = os.path.join("models", "hand_landmarker.task")
            if not os.path.exists(model_path):
                # Try absolute path from workspace
                model_path = os.path.abspath(model_path)
            
            options = vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=model_path),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=2,
                min_hand_detection_confidence=0.7,
                min_hand_presence_confidence=0.7,
                min_tracking_confidence=0.7
            )
            
            self.detector = vision.HandLandmarker.create_from_options(options)
            self.active = True
            self.logger.info("MediaPipeHandTracker successfully initialized with HandLandmarker in VIDEO mode.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize MediaPipeHandTracker: {e}")
            return False

    def process_frame(self, frame: np.ndarray, is_rgb: bool = False) -> HandLandmarksResult:
        if not self.active or self.detector is None:
            return HandLandmarksResult([], [])
        
        try:
            import mediapipe as mp
            # Convert BGR frame to RGB if needed
            rgb_frame = frame if is_rgb else cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert to MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Monotonically increasing timestamp in milliseconds
            timestamp_ms = int(time.perf_counter() * 1000)
            if timestamp_ms <= self.last_timestamp_ms:
                timestamp_ms = self.last_timestamp_ms + 1
            self.last_timestamp_ms = timestamp_ms
            
            # Run detection for video mode
            detection_result = self.detector.detect_for_video(mp_image, timestamp_ms)
            
            landmarks_list = []
            world_landmarks_list = []
            handedness_list = []
            scores_list = []
            
            if detection_result.hand_landmarks:
                for hand_idx, hand_landmarks in enumerate(detection_result.hand_landmarks):
                    points = []
                    for lm in hand_landmarks:
                        points.append({"x": lm.x, "y": lm.y, "z": lm.z})
                    landmarks_list.append(points)
                    
                    if detection_result.handedness:
                        label = detection_result.handedness[hand_idx][0].category_name
                        score = detection_result.handedness[hand_idx][0].score
                        handedness_list.append(label)
                        scores_list.append(score)
                    else:
                        handedness_list.append("Unknown")
                        scores_list.append(1.0)
                
                # Parse corresponding world landmarks in metric space
                if detection_result.hand_world_landmarks:
                    for hand_world_lms in detection_result.hand_world_landmarks:
                        w_points = []
                        for lm in hand_world_lms:
                            w_points.append({"x": lm.x, "y": lm.y, "z": lm.z})
                        world_landmarks_list.append(w_points)
                        
            return HandLandmarksResult(landmarks_list, handedness_list, scores=scores_list, world_landmarks=world_landmarks_list if world_landmarks_list else None)
        except Exception as e:
            self.logger.error(f"Error processing frame in MediaPipeHandTracker: {e}")
            return HandLandmarksResult([], [])

    def release(self) -> None:
        self.active = False
        if self.detector:
            try:
                self.detector.close()
            except Exception:
                pass
            self.detector = None
        self.logger.info("MediaPipeHandTracker released.")
