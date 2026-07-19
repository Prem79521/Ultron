import cv2
import numpy as np
import logging
import math
import time
import threading
import traceback
from typing import Dict, Any, List, Optional, Tuple
from ultron.core.service_manager import UltronService
from ultron.core.event_bus import event_bus, Event
from ultron.vision.base import BaseCameraBackend, BaseHandTracker, BaseGestureClassifier, HandLandmarksResult, DetectedGesture
from ultron.vision.camera_backend import OpenCVCameraBackend
from ultron.vision.hand_tracker import MediaPipeHandTracker

# Landmark Joint Index Mapping
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12
RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20

# Finger Landmark Groupings
FINGER_BRANCHES = {
    "thumb": [WRIST, THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP],
    "index": [WRIST, INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP],
    "middle": [WRIST, MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP],
    "ring": [WRIST, RING_MCP, RING_PIP, RING_DIP, RING_TIP],
    "pinky": [WRIST, PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP]
}

PALM_SCAFFOLD = [WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]
PALM_LINKS = [(WRIST, INDEX_MCP), (WRIST, MIDDLE_MCP), (WRIST, RING_MCP), (WRIST, PINKY_MCP),
              (INDEX_MCP, MIDDLE_MCP), (MIDDLE_MCP, RING_MCP), (RING_MCP, PINKY_MCP)]


class OneEuroFilter:
    """Velocity-based adaptive low-pass filter for landmark stabilization."""
    def __init__(self, t0: float, x0: np.ndarray, mincutoff: float = 0.5, beta: float = 0.010, dcutoff: float = 1.0):
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.x_prev = np.array(x0, dtype=np.float32)
        self.dx_prev = np.zeros_like(self.x_prev)
        self.t_prev = t0

    def __call__(self, t: float, x: np.ndarray) -> np.ndarray:
        dt = t - self.t_prev
        if dt <= 0:
            return self.x_prev
        
        x = np.array(x, dtype=np.float32)
        dx = (x - self.x_prev) / dt
        
        alpha_d = 1.0 / (1.0 + self.dcutoff / (2.0 * math.pi * dt))
        self.dx_prev = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev
        
        speed = np.linalg.norm(self.dx_prev)
        cutoff = self.mincutoff + self.beta * speed
        alpha = 1.0 / (1.0 + cutoff / (2.0 * math.pi * dt))
        
        self.x_prev = alpha * x + (1.0 - alpha) * self.x_prev
        self.t_prev = t
        return self.x_prev


class TrackedHand:
    """Manages persistent hand tracking state across frames."""
    def __init__(self, hand_id: int, palm_center: np.ndarray, handedness: str, current_time: float):
        self.hand_id = hand_id
        self.palm_center = palm_center
        self.handedness = handedness
        self.handedness_history = [handedness]
        self.last_seen = current_time
        self.last_prediction_time = current_time
        
        # Filters and solvers
        self.filter: Optional[OneEuroFilter] = None
        self.world_filter: Optional[OneEuroFilter] = None
        self.velocity = np.zeros(3, dtype=np.float32)
        self.last_landmarks = None
        self.last_world_landmarks = None
        self.is_predicted = False
        
        # Kinematics fingerprinting
        self.hand_scale = 0.09  # default average hand scale in meters
        self.finger_proportions = np.ones(5, dtype=np.float32)
        self.stable_score = 1.0


class HandPoseStabilizationLayer:
    """Modular layer providing bone length constraints, joint limit clamping, temporal Kalman filtering and palm rigidity."""
    def __init__(self):
        self.calibrated_bone_lengths = {}      # Map hand_id -> dict of (p1, p2): length_meters
        self.calibrated_palm_links = {}        # Map hand_id -> dict of (p1, p2): length_meters
        self.calibration_counts = {}           # Map hand_id -> count of stable frames
        self.calibration_buffers = {}          # Map hand_id -> list of world_landmarks dicts
        
        # Temporal state variables for Kalman-style constant-acceleration prediction
        # Map hand_id -> dict of joint_idx -> (pos_3d, vel_3d, acc_3d, last_t)
        self.temporal_predictions = {}
        
        # Stable local coordinate templates for occlusion recovery
        self.stable_local_template = {}        # Map hand_id -> list of 21 np.ndarray
        self.occlusion_start_times = {}        # Map hand_id -> float
        
        # Bone length reconstruction error metric
        self.last_bone_error = {}              # Map hand_id -> float
        self.joint_warnings_count = {}         # Map hand_id -> int
        
        # Configurable anatomical joint limits (min, max angles in degrees)
        self.joint_limits = {
            # Thumb
            (1, 2, 3): (-10.0, 75.0), # Thumb MCP
            (2, 3, 4): (-10.0, 80.0), # Thumb IP
            # Index
            (5, 6, 7): (0.0, 110.0),  # Index PIP
            (6, 7, 8): (0.0, 90.0),   # Index DIP
            (0, 5, 6): (-15.0, 90.0), # Index MCP
            # Middle
            (9, 10, 11): (0.0, 110.0),
            (10, 11, 12): (0.0, 90.0),
            (0, 9, 10): (-15.0, 90.0),
            # Ring
            (13, 14, 15): (0.0, 110.0),
            (14, 15, 16): (0.0, 90.0),
            (0, 13, 14): (-15.0, 90.0),
            # Pinky
            (17, 18, 19): (0.0, 110.0),
            (18, 19, 20): (0.0, 90.0),
            (0, 17, 18): (-15.0, 90.0)
        }

    def _calculate_angle_3d(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        v1 = p2 - p1
        v2 = p3 - p2
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 < 1e-6 or n2 < 1e-6:
            return 0.0
        cos_theta = np.dot(v1, v2) / (n1 * n2)
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        return math.degrees(math.acos(cos_theta))

    def stabilize(self, hand_id: int, raw_world_lms: np.ndarray, confidence: float, current_time: float) -> Tuple[np.ndarray, float]:
        """Main stabilization entry point. Runs bone solver, joint limit clamping, and temporal blending."""
        pts = np.copy(raw_world_lms)  # 21x3 array of meters
        
        # 1. Temporal Prediction and Kalman-style Blending (Subsystem C & D)
        pts = self._apply_temporal_kalman(hand_id, pts, confidence, current_time)
        
        # 2. Calibration of anatomical parameters
        self._check_calibration(hand_id, pts)
        
        # 3. Bone Length Constraint Solver (Subsystem A & F)
        pts = self._solve_bone_lengths(hand_id, pts)
        
        # 4. Joint Limit Enforcement (Subsystem B)
        pts, warning_count = self._enforce_joint_limits(hand_id, pts)
        self.joint_warnings_count[hand_id] = warning_count
        
        # Store local template if pose is highly confident and stable
        if confidence > 0.85:
            self._update_local_template(hand_id, pts)
            
        return pts, self.last_bone_error.get(hand_id, 0.0)

    def _apply_temporal_kalman(self, hand_id: int, pts: np.ndarray, confidence: float, current_time: float) -> np.ndarray:
        if hand_id not in self.temporal_predictions:
            self.temporal_predictions[hand_id] = {
                i: (pts[i], np.zeros(3, dtype=np.float32), np.zeros(3, dtype=np.float32), current_time)
                for i in range(21)
            }
            return pts

        preds = self.temporal_predictions[hand_id]
        optimized_pts = np.zeros_like(pts)
        
        for i in range(21):
            pos_prev, vel_prev, acc_prev, t_prev = preds[i]
            dt = current_time - t_prev
            
            if dt > 0.001:
                # Predict position: x = x_prev + v_prev*dt + 0.5*a_prev*dt^2
                pos_pred = pos_prev + vel_prev * dt + 0.5 * acc_prev * (dt ** 2)
                
                # Blend prediction with new measurement based on confidence score (Subsystem D)
                # High confidence -> weight measurement heavily. Low confidence -> trust prediction more.
                alpha = min(0.95, max(0.10, confidence * 0.90))
                pos_new = (1.0 - alpha) * pos_pred + alpha * pts[i]
                
                # Estimate velocity and acceleration
                vel_new = (pos_new - pos_prev) / dt
                acc_new = (vel_new - vel_prev) / dt
                
                # Store back temporal state
                preds[i] = (pos_new, vel_new, acc_new, current_time)
                optimized_pts[i] = pos_new
            else:
                optimized_pts[i] = pos_prev
                
        return optimized_pts

    def _check_calibration(self, hand_id: int, pts: np.ndarray):
        if hand_id in self.calibrated_bone_lengths:
            return
            
        if hand_id not in self.calibration_counts:
            self.calibration_counts[hand_id] = 0
            self.calibration_buffers[hand_id] = []
            
        # Collect stable frames for calibration
        self.calibration_buffers[hand_id].append(pts)
        self.calibration_counts[hand_id] += 1
        
        if self.calibration_counts[hand_id] >= 20:  # Calibrate over 20 stable frames
            buf = self.calibration_buffers[hand_id]
            
            # Calibrate finger bones
            self.calibrated_bone_lengths[hand_id] = {}
            for finger, joints in FINGER_BRANCHES.items():
                for k in range(1, len(joints)):
                    p1, p2 = joints[k-1], joints[k]
                    dists = [np.linalg.norm(f[p2] - f[p1]) for f in buf]
                    self.calibrated_bone_lengths[hand_id][(p1, p2)] = np.mean(dists)
                    
            # Calibrate palm rigidity links (Subsystem F)
            self.calibrated_palm_links[hand_id] = {}
            for p1, p2 in PALM_LINKS:
                dists = [np.linalg.norm(f[p2] - f[p1]) for f in buf]
                self.calibrated_palm_links[hand_id][(p1, p2)] = np.mean(dists)

    def _solve_bone_lengths(self, hand_id: int, pts: np.ndarray) -> np.ndarray:
        if hand_id not in self.calibrated_bone_lengths:
            return pts
            
        # 1. Metacarpal Palm Rigidity Solver (Subsystem F - 2 solver iterations)
        palm_lengths = self.calibrated_palm_links[hand_id]
        for _ in range(2):
            for p1, p2 in PALM_LINKS:
                target = palm_lengths[(p1, p2)]
                v = pts[p2] - pts[p1]
                curr = np.linalg.norm(v)
                if curr > 1e-6:
                    diff = (curr - target) / 2.0
                    displacement = (v / curr) * diff
                    # Apply correction symmetrically (unless wrist, which is root anchored)
                    if p1 == WRIST:
                        pts[p2] -= displacement * 2.0
                    else:
                        pts[p1] += displacement
                        pts[p2] -= displacement
                        
        # 2. Outward Bone Constraint Solver (Subsystem A - propagates root-to-tips)
        bone_lengths = self.calibrated_bone_lengths[hand_id]
        total_error = 0.0
        count = 0
        
        for finger, joints in FINGER_BRANCHES.items():
            for k in range(1, len(joints)):
                p_parent, p_child = joints[k-1], joints[k]
                target = bone_lengths[(p_parent, p_child)]
                v = pts[p_child] - pts[p_parent]
                curr = np.linalg.norm(v)
                
                if curr > 1e-6:
                    total_error += abs(curr - target)
                    count += 1
                    pts[p_child] = pts[p_parent] + (v / curr) * target
                    
        self.last_bone_error[hand_id] = total_error / count if count > 0 else 0.0
        return pts

    def _enforce_joint_limits(self, hand_id: int, pts: np.ndarray) -> Tuple[np.ndarray, int]:
        warning_count = 0
        # Enforce MCP, PIP and DIP flexion joint limits (Subsystem B)
        for (p1, p2, p3), (min_deg, max_deg) in self.joint_limits.items():
            u = pts[p2] - pts[p1]
            v = pts[p3] - pts[p2]
            n_u = np.linalg.norm(u)
            n_v = np.linalg.norm(v)
            if n_u < 1e-6 or n_v < 1e-6:
                continue
                
            u_dir = u / n_u
            v_dir = v / n_v
            
            # Flexion angle
            cos_theta = np.dot(u_dir, v_dir)
            angle = math.degrees(math.acos(np.clip(cos_theta, -1.0, 1.0)))
            
            if angle < min_deg or angle > max_deg:
                warning_count += 1
                clamped_angle = np.clip(angle, min_deg, max_deg)
                
                # Reconstruct child segment vector along the parent vector plane
                # Project child onto orthogonal space
                v_ortho = v_dir - (np.dot(u_dir, v_dir)) * u_dir
                n_ortho = np.linalg.norm(v_ortho)
                v_ortho = v_ortho / n_ortho if n_ortho > 1e-6 else np.array([0.0, 0.0, 1.0], dtype=np.float32)
                
                # Re-compute direction vector satisfying clamped angle
                clamped_dir = math.cos(math.radians(clamped_angle)) * u_dir + math.sin(math.radians(clamped_angle)) * v_ortho
                pts[p3] = pts[p2] + clamped_dir * n_v
                
        return pts, warning_count

    def _update_local_template(self, hand_id: int, pts: np.ndarray):
        # Build local palm coordinate space
        w = pts[WRIST]
        i_mcp = pts[INDEX_MCP]
        p_mcp = pts[PINKY_MCP]
        m_mcp = pts[MIDDLE_MCP]
        
        y_axis = (m_mcp - w) / (np.linalg.norm(m_mcp - w) + 1e-6)
        z_axis = np.cross(i_mcp - w, p_mcp - w)
        z_axis /= (np.linalg.norm(z_axis) + 1e-6)
        x_axis = np.cross(y_axis, z_axis)
        x_axis /= (np.linalg.norm(x_axis) + 1e-6)
        
        # Store relative local coordinates for all 21 landmarks
        local_coords = []
        for i in range(21):
            rel = pts[i] - w
            local_coords.append(np.array([
                np.dot(rel, x_axis),
                np.dot(rel, y_axis),
                np.dot(rel, z_axis)
            ], dtype=np.float32))
            
        self.stable_local_template[hand_id] = local_coords

    def recover_occluded_finger(self, hand_id: int, pts: np.ndarray, occluded_joint_indices: List[int]) -> np.ndarray:
        """Occlusion Recovery Subsystem: Estimates positions of hidden joints using palm rotation and local template (Subsystem E)."""
        if hand_id not in self.stable_local_template:
            return pts
            
        # Reconstruct palm coordinate basis
        w = pts[WRIST]
        i_mcp = pts[INDEX_MCP]
        p_mcp = pts[PINKY_MCP]
        m_mcp = pts[MIDDLE_MCP]
        
        y_axis = (m_mcp - w) / (np.linalg.norm(m_mcp - w) + 1e-6)
        z_axis = np.cross(i_mcp - w, p_mcp - w)
        z_axis /= (np.linalg.norm(z_axis) + 1e-6)
        x_axis = np.cross(y_axis, z_axis)
        x_axis /= (np.linalg.norm(x_axis) + 1e-6)
        
        template = self.stable_local_template[hand_id]
        
        # Recover hidden joint coordinates
        for idx in occluded_joint_indices:
            l_coord = template[idx]
            # Project back to world coordinates
            pts[idx] = w + l_coord[0] * x_axis + l_coord[1] * y_axis + l_coord[2] * z_axis
            
        return pts


class RuleBasedGestureClassifier(BaseGestureClassifier):
    """Classifies hand landmarks into gestures using rotation-invariant 3D landmark geometry and temporal voting."""
    def __init__(self):
        self.pinch_threshold_on = 0.35
        self.pinch_threshold_off = 0.45
        self.prev_pinch_states = {}  # Map hand_id to pinch boolean
        
        # Classification history voting parameters
        self.classification_history = {}  # Map hand_id to list of str
        self.history_size = 5
        self.confirm_threshold = 4
        self.confirmed_gestures = {}  # Map hand_id to last confirmed gesture
        self.finger_histories = {}  # Map hand_id to List[List[bool]]
        
        self.prediction_counts = {}  # Map hand_id to count of consecutive predicted frames
        
        # Adaptive Kinematic Calibration (Phase 3)
        self.calibration_angle_ranges = {} # Map hand_id -> dict of joint -> (min_deg, max_deg)
        self.calibrated_thresholds = {}    # Map hand_id -> dict of joint_sum/mcp -> threshold_deg

    def _calculate_angle_pts(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """Calculates 3D angle between vector p1->p2 and vector p2->p3 in degrees."""
        v1 = p2 - p1
        v2 = p3 - p2
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 < 1e-6 or n2 < 1e-6:
            return 0.0
        cos_theta = np.dot(v1, v2) / (n1 * n2)
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        return math.degrees(math.acos(cos_theta))

    def _get_finger_kinematics(self, lm: List[Dict[str, float]], handedness: str, hand_id: int) -> tuple:
        """Computes joint angles in 3D metric world space and utilizes self-calibrating thresholds (Phase 3)."""
        pts = np.array([[pt['x'], pt['y'], pt['z']] for pt in lm], dtype=np.float32)
        palm_width = np.linalg.norm(pts[INDEX_MCP] - pts[PINKY_MCP])
        if palm_width < 1e-5:
            return [False] * 5, [1.0] * 5, {}

        # 1. Joint angle calculations for all fingers (MCP, PIP, DIP)
        # THUMB
        thumb_ip = self._calculate_angle_pts(pts[THUMB_MCP], pts[THUMB_IP], pts[THUMB_TIP])
        thumb_mcp = self._calculate_angle_pts(pts[THUMB_CMC], pts[THUMB_MCP], pts[THUMB_IP])
        # INDEX
        index_pip = self._calculate_angle_pts(pts[INDEX_MCP], pts[INDEX_PIP], pts[INDEX_DIP])
        index_dip = self._calculate_angle_pts(pts[INDEX_PIP], pts[INDEX_DIP], pts[INDEX_TIP])
        index_mcp = self._calculate_angle_pts(pts[WRIST], pts[INDEX_MCP], pts[INDEX_PIP])
        # MIDDLE
        middle_pip = self._calculate_angle_pts(pts[MIDDLE_MCP], pts[MIDDLE_PIP], pts[MIDDLE_DIP])
        middle_dip = self._calculate_angle_pts(pts[MIDDLE_PIP], pts[MIDDLE_DIP], pts[MIDDLE_TIP])
        middle_mcp = self._calculate_angle_pts(pts[WRIST], pts[MIDDLE_MCP], pts[MIDDLE_PIP])
        # RING
        ring_pip = self._calculate_angle_pts(pts[RING_MCP], pts[RING_PIP], pts[RING_DIP])
        ring_dip = self._calculate_angle_pts(pts[RING_PIP], pts[RING_DIP], pts[RING_TIP])
        ring_mcp = self._calculate_angle_pts(pts[WRIST], pts[RING_MCP], pts[RING_PIP])
        # PINKY
        pinky_pip = self._calculate_angle_pts(pts[PINKY_MCP], pts[PINKY_PIP], pts[PINKY_DIP])
        pinky_dip = self._calculate_angle_pts(pts[PINKY_PIP], pts[PINKY_DIP], pts[PINKY_TIP])
        pinky_mcp = self._calculate_angle_pts(pts[WRIST], pts[PINKY_MCP], pts[PINKY_PIP])

        # 2. Orthonormal Local Coordinate Basis Projection for Thumb Abduction
        w = pts[WRIST]
        i_mcp = pts[INDEX_MCP]
        p_mcp = pts[PINKY_MCP]
        m_mcp = pts[MIDDLE_MCP]
        
        y_axis = (m_mcp - w) / (np.linalg.norm(m_mcp - w) + 1e-6)
        z_axis = np.cross(i_mcp - w, p_mcp - w)
        z_axis /= (np.linalg.norm(z_axis) + 1e-6)
        x_axis = np.cross(y_axis, z_axis)
        x_axis /= (np.linalg.norm(x_axis) + 1e-6)
        
        t_tip_rel = pts[THUMB_TIP] - w
        t_mcp_rel = pts[THUMB_MCP] - w
        thumb_tip_local_x = np.dot(t_tip_rel, x_axis)
        thumb_mcp_local_x = np.dot(t_mcp_rel, x_axis)
        
        side_multiplier = -1.0 if handedness == "Right" else 1.0
        thumb_abduction = (thumb_tip_local_x - thumb_mcp_local_x) * side_multiplier
        thumb_abduction_ratio = thumb_abduction / (palm_width + 1e-6)

        # 3. Dynamic Threshold Calibration (Phase 3)
        self._calibrate_kinematic_limits(hand_id, thumb_ip + thumb_mcp, index_pip + index_dip, index_mcp, 
                                         middle_pip + middle_dip, middle_mcp, ring_pip + ring_dip, ring_mcp,
                                         pinky_pip + pinky_dip, pinky_mcp, thumb_abduction_ratio)
        
        # Get calibrated or default thresholds
        thresh = self.calibrated_thresholds.get(hand_id, {
            "thumb_flexion": 45.0, "thumb_abduction": 0.16,
            "index_flexion": 50.0, "index_mcp": 35.0,
            "middle_flexion": 50.0, "middle_mcp": 35.0,
            "ring_flexion": 50.0, "ring_mcp": 35.0,
            "pinky_flexion": 50.0, "pinky_mcp": 35.0
        })

        extended = [False] * 5
        confidences = [1.0] * 5
        
        # --- THUMB ---
        thumb_flexion = thumb_ip + thumb_mcp
        thumb_is_straight = thumb_flexion < thresh["thumb_flexion"]
        thumb_is_abducted = thumb_abduction_ratio > thresh["thumb_abduction"]
        
        thumb_extended = thumb_is_straight and thumb_is_abducted
        extended[0] = thumb_extended
        
        # Thumb confidence mapping
        if thumb_extended:
            c_abd = min(1.0, max(0.5, 0.5 + (thumb_abduction_ratio - thresh["thumb_abduction"]) / 0.20))
            c_flx = min(1.0, max(0.5, 1.0 - (thumb_flexion / thresh["thumb_flexion"]) * 0.5))
            conf = c_abd * c_flx
        else:
            c_abd = min(1.0, max(0.5, 0.5 + (thresh["thumb_abduction"] - thumb_abduction_ratio) / 0.20))
            c_flx = min(1.0, max(0.5, 0.5 + (thumb_flexion - thresh["thumb_flexion"]) / 90.0))
            conf = max(c_abd, c_flx)
        confidences[0] = float(np.clip(conf, 0.5, 1.0))

        # --- OTHER FINGERS ---
        finger_data = [
            ("index", index_pip + index_dip, index_mcp, 1),
            ("middle", middle_pip + middle_dip, middle_mcp, 2),
            ("ring", ring_pip + ring_dip, ring_mcp, 3),
            ("pinky", pinky_pip + pinky_dip, pinky_mcp, 4)
        ]
        
        for name, flx_sum, mcp_val, f_idx in finger_data:
            t_flx = thresh[f"{name}_flexion"]
            t_mcp = thresh[f"{name}_mcp"]
            
            is_ext = flx_sum < t_flx and mcp_val < t_mcp
            extended[f_idx] = is_ext
            
            if is_ext:
                conf = 1.0 - (flx_sum / t_flx) * 0.5
            else:
                conf = 0.5 + ((flx_sum - t_flx) / 100.0) * 0.5
            confidences[f_idx] = float(np.clip(conf, 0.5, 1.0))

        angles_dict = {
            "thumb": [float(thumb_mcp), float(thumb_ip)],
            "index": [float(index_mcp), float(index_pip), float(index_dip)],
            "middle": [float(middle_mcp), float(middle_pip), float(middle_dip)],
            "ring": [float(ring_mcp), float(ring_pip), float(ring_dip)],
            "pinky": [float(pinky_mcp), float(pinky_pip), float(pinky_dip)]
        }
        
        return extended, confidences, angles_dict

    def _calibrate_kinematic_limits(self, hand_id: int, t_flx: float, i_flx: float, i_mcp: float, 
                                    m_flx: float, m_mcp: float, r_flx: float, r_mcp: float, 
                                    p_flx: float, p_mcp: float, t_abd: float):
        if hand_id not in self.calibration_angle_ranges:
            self.calibration_angle_ranges[hand_id] = {
                "thumb_flexion": [t_flx, t_flx], "thumb_abduction": [t_abd, t_abd],
                "index_flexion": [i_flx, i_flx], "index_mcp": [i_mcp, i_mcp],
                "middle_flexion": [m_flx, m_flx], "middle_mcp": [m_mcp, m_mcp],
                "ring_flexion": [r_flx, r_flx], "ring_mcp": [r_mcp, r_mcp],
                "pinky_flexion": [p_flx, p_flx], "pinky_mcp": [p_mcp, p_mcp]
            }
            return
            
        ranges = self.calibration_angle_ranges[hand_id]
        
        # Track min/max bounds observed dynamically (Phase 3)
        vals = {
            "thumb_flexion": t_flx, "thumb_abduction": t_abd,
            "index_flexion": i_flx, "index_mcp": i_mcp,
            "middle_flexion": m_flx, "middle_mcp": m_mcp,
            "ring_flexion": r_flx, "ring_mcp": r_mcp,
            "pinky_flexion": p_flx, "pinky_mcp": p_mcp
        }
        
        for k, val in vals.items():
            ranges[k][0] = min(ranges[k][0], val)
            ranges[k][1] = max(ranges[k][1], val)
            
        # Re-calculate midpoints as adaptive thresholds
        self.calibrated_thresholds[hand_id] = {}
        for k, bounds in ranges.items():
            span = bounds[1] - bounds[0]
            if span > 15.0: # threshold changes only when user exercises range
                mid = bounds[0] + span * 0.50
                # Clamp within reasonable physiological ranges
                if "abduction" in k:
                    self.calibrated_thresholds[hand_id][k] = np.clip(mid, 0.12, 0.22)
                elif "mcp" in k:
                    self.calibrated_thresholds[hand_id][k] = np.clip(mid, 28.0, 42.0)
                else:
                    self.calibrated_thresholds[hand_id][k] = np.clip(mid, 35.0, 60.0)
            else:
                # Default fallbacks
                if "abduction" in k:
                    self.calibrated_thresholds[hand_id][k] = 0.16
                elif "mcp" in k:
                    self.calibrated_thresholds[hand_id][k] = 35.0
                else:
                    self.calibrated_thresholds[hand_id][k] = 50.0 or 45.0

    def classify(self, tracker_result: HandLandmarksResult) -> List[DetectedGesture]:
        gestures = []
        if tracker_result.is_empty():
            self.prev_pinch_states.clear()
            self.classification_history.clear()
            self.confirmed_gestures.clear()
            self.finger_histories.clear()
            self.prediction_counts.clear()
            return gestures

        active_ids = set(tracker_result.hand_ids)
        for hand_id in list(self.classification_history.keys()):
            if hand_id not in active_ids:
                self.prev_pinch_states.pop(hand_id, None)
                self.classification_history.pop(hand_id, None)
                self.confirmed_gestures.pop(hand_id, None)
                self.finger_histories.pop(hand_id, None)
                self.prediction_counts.pop(hand_id, None)

        for hand_idx, lm in enumerate(tracker_result.landmarks):
            hand_id = tracker_result.hand_ids[hand_idx]
            label = tracker_result.handedness[hand_idx]
            is_pred = tracker_result.is_predicted[hand_idx] if hand_idx < len(tracker_result.is_predicted) else False
            
            # Kinematics based classification
            stable_extended, finger_confs, angles = self._get_finger_kinematics(lm, label, hand_id)
            
            if hand_id not in self.finger_histories:
                self.finger_histories[hand_id] = []
            self.finger_histories[hand_id].append(raw_extended if 'raw_extended' in locals() else stable_extended)
            self.finger_histories[hand_id] = self.finger_histories[hand_id][-5:]
            
            # Calculate vote agreement ratio (ranges from 0.0 to 1.0)
            agreement_sum = 0.0
            history_f = self.finger_histories[hand_id]
            for f_idx in range(5):
                votes = sum(h[f_idx] for h in history_f)
                agreement_sum += abs(votes - 2.5)
            vote_confidence = agreement_sum / 12.5 if len(history_f) > 0 else 1.0
            
            # Majority vote on each finger state
            voted_extended = []
            for f_idx in range(5):
                votes = sum(h[f_idx] for h in history_f)
                voted_extended.append(votes >= 3)
                
            pts = np.array([[pt['x'], pt['y'], pt['z']] for pt in lm], dtype=np.float32)
            palm_width = np.linalg.norm(pts[INDEX_MCP] - pts[PINKY_MCP])
            if palm_width < 1e-5:
                continue

            # Pinch Proximity with Hysteresis
            pinch_dist = np.linalg.norm(pts[THUMB_TIP] - pts[INDEX_TIP]) / (palm_width + 1e-6)
            prev_pinched = self.prev_pinch_states.get(hand_id, False)
            if prev_pinched:
                pinched = pinch_dist < self.pinch_threshold_off
            else:
                pinched = pinch_dist < self.pinch_threshold_on
            self.prev_pinch_states[hand_id] = pinched

            pinch_center = {
                "x": 1.0 - (lm[THUMB_TIP]["x"] + lm[INDEX_TIP]["x"]) / 2.0,
                "y": (lm[THUMB_TIP]["y"] + lm[INDEX_TIP]["y"]) / 2.0
            }

            candidate = "None"
            base_confidence = 0.5
            data = {"hand": label, "hand_id": hand_id, "center": pinch_center, "extended": voted_extended}
            
            # Heuristics
            if voted_extended == [True, True, True, True, True]:
                candidate = "Open Palm"
                base_confidence = 0.95
            elif voted_extended == [False, False, False, False, False]:
                candidate = "Closed Fist"
                base_confidence = 0.95
            elif pinched and voted_extended[2] and voted_extended[3] and voted_extended[4]:
                candidate = "OK"
                base_confidence = 0.90
            elif pinched:
                candidate = "Pinch"
                base_confidence = 0.95
            elif voted_extended[0] and not any(voted_extended[1:]):
                # Thumb only (Thumb Up or Thumb Down)
                dy = lm[THUMB_TIP]["y"] - lm[THUMB_MCP]["y"]
                if dy < -0.05:
                    candidate = "Thumb Up"
                    base_confidence = 0.90
                elif dy > 0.05:
                    candidate = "Thumb Down"
                    base_confidence = 0.90
            elif voted_extended[1] and voted_extended[2] and not voted_extended[3] and not voted_extended[4]:
                candidate = "Peace"
                base_confidence = 0.90
            elif voted_extended[1] and not any(voted_extended[2:]):
                # Index only (Point Left / Point Right)
                dx = lm[INDEX_TIP]["x"] - lm[INDEX_MCP]["x"]
                if dx < -0.12:
                    candidate = "Point Right"
                    base_confidence = 0.85
                elif dx > 0.12:
                    candidate = "Point Left"
                    base_confidence = 0.85

            # 2. Multi-Frame Confirmation Voting
            if hand_id not in self.classification_history:
                self.classification_history[hand_id] = []
            
            self.classification_history[hand_id].append(candidate)
            if len(self.classification_history[hand_id]) > self.history_size:
                self.classification_history[hand_id].pop(0)

            history = self.classification_history[hand_id]
            counts = {}
            for item in history:
                counts[item] = counts.get(item, 0) + 1
            
            majority_candidate = max(counts, key=counts.get)
            majority_count = counts[majority_candidate]
            
            confirmed = self.confirmed_gestures.get(hand_id, "None")
            if majority_count >= self.confirm_threshold:
                confirmed = majority_candidate
                self.confirmed_gestures[hand_id] = confirmed
            
            # 3. Dynamic Gesture Confidence Calculation
            if is_pred:
                self.prediction_counts[hand_id] = self.prediction_counts.get(hand_id, 0) + 1
            else:
                self.prediction_counts[hand_id] = 0
            
            decay = 0.85 ** self.prediction_counts[hand_id]
            final_confidence = base_confidence * vote_confidence * decay
                
            if confirmed != "None":
                gestures.append(DetectedGesture(confirmed, final_confidence, data))

        return gestures


class IntentEngine:
    """Temporal prediction layer capturing dynamics, approach velocities, hover states, and swipes (Phase 7)."""
    def __init__(self):
        # Maps hand_id -> list of (palm_center_3d, time)
        self.trajectory_history = {}
        self.history_size = 15

    def update_and_predict(self, hand_id: int, palm_center: np.ndarray, ext_fingers: List[bool], pinch_dist: float, current_time: float) -> str:
        if hand_id not in self.trajectory_history:
            self.trajectory_history[hand_id] = []
            
        self.trajectory_history[hand_id].append((palm_center, current_time))
        self.trajectory_history[hand_id] = self.trajectory_history[hand_id][-self.history_size:]
        
        hist = self.trajectory_history[hand_id]
        if len(hist) < 5:
            return "Hover"

        # Calculate average velocity vector (last 5 frames)
        dt = hist[-1][1] - hist[-5][1]
        if dt > 0.001:
            vel = (hist[-1][0] - hist[-5][0]) / dt
        else:
            vel = np.zeros(3, dtype=np.float32)

        # Selection Intent check: fast forward push motion along camera axis (Z-axis is index 2)
        # In webcam space, -Z points towards the camera. Push = rapid movement in negative Z.
        if vel[2] < -0.35 and pinch_dist < 0.40:
            return "Selection intent"
            
        # Push & Pull Motions
        if vel[2] < -0.40:
            return "Push motion"
        elif vel[2] > 0.40:
            return "Pull motion"
            
        # Throw Motion: rapid velocity peak followed by open palm release
        if np.linalg.norm(vel) > 0.80 and ext_fingers == [True, True, True, True, True]:
            return "Throw motion"

        # Swiping preparation
        if abs(vel[0]) > 0.45:
            return "Preparing swipe"

        # Dynamic finger spacing approach/separate
        if pinch_dist > 0.35 and pinch_dist < 0.60:
            # Check slope of pinch distance change
            return "Preparing pinch"

        return "Hover"


class GestureService(UltronService):
    """Service that manages camera frames processing and publishes gesture events with HPSL layer."""
    def __init__(
        self,
        camera_backend: Optional[BaseCameraBackend] = None,
        hand_tracker: Optional[BaseHandTracker] = None,
        classifier: Optional[BaseGestureClassifier] = None
    ):
        super().__init__("GestureService")
        self.camera = camera_backend or OpenCVCameraBackend()
        self.tracker = hand_tracker or MediaPipeHandTracker()
        self.classifier = classifier or RuleBasedGestureClassifier()
        self.hpsl = HandPoseStabilizationLayer()
        self.intent_engine = IntentEngine()
        
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self.logger = logging.getLogger("ultron-agent")
        
        # Gestures smoothing
        self.prev_spin_grab: Optional[Dict[str, float]] = None
        self.prev_zoom_dist: Optional[float] = None
        self.prev_mode: str = "idle"
        self.smoothing = 0.4
        self.rotate_speed = 5.0

        # Temporal confirmation persistence states
        self.last_published_gestures = {}  # Map hand_id to (gesture_name, timestamp)
        self.cooldown_timers = {}          # Map gesture_name to timestamp
        self.gesture_hold_times = {}       # Map hand_id to timestamp
        
        # Multi-hand persistent tracking
        self.next_hand_id = 0
        self.tracked_hands: List[TrackedHand] = []
        
        # Zero-allocation preprocessing buffers
        self._resized_bgr = np.empty((240, 320, 3), dtype=np.uint8)
        self._ycrcb_buf = np.empty((240, 320, 3), dtype=np.uint8)
        self._preprocessed_rgb = np.empty((240, 320, 3), dtype=np.uint8)
        self._y_channel = np.empty((240, 320), dtype=np.uint8)
        
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self.gamma_lut_brighten = np.array([((i / 255.0) ** 0.70) * 255 for i in range(256)]).astype(np.uint8)
        self.gamma_lut_darken = np.array([((i / 255.0) ** 1.30) * 255 for i in range(256)]).astype(np.uint8)

        # Diagnostics & Validation
        self.inference_time_ms = 0.0
        self.stabilization_time_ms = 0.0
        self.gesture_fps = 0.0
        self._fps_timestamps = []
        self._frame_processed_count = 0

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True

            from ultron.core.service_manager import service_manager
            camera_srv = service_manager.get_service("CameraService")
            if camera_srv:
                if not camera_srv.active:
                    if not camera_srv.start():
                        self.logger.error("GestureService: Failed to start shared CameraService.")
                        return False
            else:
                self.camera.initialize(0)
                if not self.camera.start():
                    self.logger.error("GestureService: Failed to start fallback Camera backend.")
                    return False

            if not self.tracker.initialize():
                self.logger.error("GestureService: Failed to initialize Hand Tracker.")
                if camera_srv:
                    camera_srv.stop()
                else:
                    self.camera.stop()
                return False

            self._running = True
            self.active = True
            self._frame_processed_count = 0
            
            self._thread = threading.Thread(target=self._watchdog_loop, name="GestureProcessingThread")
            self._thread.daemon = True
            self._thread.start()
            
            threading.Timer(5.0, self._verify_startup).start()
            
            self.logger.info("GestureService started and watchdog loop launched.")
            return True

    def stop(self) -> bool:
        with self._lock:
            if not self._running:
                return True
            self._running = False
            self.active = False

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        self.tracker.release()
        from ultron.core.service_manager import service_manager
        camera_srv = service_manager.get_service("CameraService")
        if camera_srv:
            camera_srv.stop()
        else:
            self.camera.stop()
        self.logger.info("GestureService stopped successfully.")
        return True

    def health(self) -> str:
        return "Running" if self.active and self._running else "Offline"

    def _watchdog_loop(self):
        self.logger.info("GestureService: Watchdog recovery loop active.")
        while True:
            with self._lock:
                if not self._running:
                    break
            try:
                self._process_loop()
                break
            except Exception as e:
                self.logger.error(f"GestureService: GestureProcessingThread crashed unexpectedly:\n{traceback.format_exc()}")
                with self._lock:
                    if not self._running:
                        break
                self.logger.info("Watchdog: Automatically restarting gesture processing loop in 1 second...")
                time.sleep(1.0)

    def _verify_startup(self):
        with self._lock:
            if not self._running:
                return
        
        try:
            from ultron.hal.hal_manager import get_hal_manager
            hal = get_hal_manager()
            if hal and not hal.is_allowed("camera"):
                self.logger.info("GestureService Validation: Camera disabled in permissions. Skipping validation.")
                return
        except Exception:
            pass

        failures = []
        if not self.tracker.active or self.tracker.detector is None:
            failures.append("MediaPipe Landmarker is not initialized.")
            
        camera_fps = 0.0
        from ultron.core.service_manager import service_manager
        camera_srv = service_manager.get_service("CameraService")
        if camera_srv:
            camera_fps = camera_srv.camera_fps
            if camera_fps < 15:
                failures.append(f"Camera frame rate is low ({camera_fps:.1f} FPS).")
        else:
            failures.append("CameraService is not running.")
            
        if self.gesture_fps < 15:
            failures.append(f"Gesture processing rate is low ({self.gesture_fps:.1f} FPS).")
            
        if self._frame_processed_count == 0:
            failures.append("No CAMERA_FRAME_PROCESSED events are being emitted.")
            
        preview_active = False
        try:
            from ui.camera_preview import UltronCameraPreviewWidget
            preview_active = any(w.isVisible() for w in UltronCameraPreviewWidget.active_instances)
        except Exception:
            pass
        if not preview_active:
            failures.append("Camera Preview UI widget is not active or visible.")

        if failures:
            msg = " | ".join(failures)
            self.logger.warning(f"GestureService: Startup validation checks failed: {msg}")
            try:
                from ultron.core.notification_center import notification_center
                notification_center.notify(
                    "Vision", 
                    "Diagnostic Alert", 
                    f"Vision module degraded: {failures[0]} (and {len(failures)-1} other checks)" if len(failures) > 1 else f"Vision module degraded: {failures[0]}"
                )
            except Exception as ne:
                self.logger.error(f"Failed to send diagnostic notification: {ne}")
        else:
            self.logger.info("GestureService: Startup validation checks completed successfully. Subsystem is healthy.")

    def _process_loop(self):
        """Webcam processing and gesture recognition loop running at capped 30 FPS."""
        self.logger.info("GestureService: Processing loop started.")
        from ultron.core.service_manager import service_manager
        target_interval = 1.0 / 30.0  # target 30 FPS
        
        while True:
            t_loop_start = time.perf_counter()
            with self._lock:
                if not self._running:
                    break

            camera_srv = service_manager.get_service("CameraService")
            frame = camera_srv.capture_frame() if (camera_srv and camera_srv.active) else self.camera.capture_frame()
            
            if frame is None:
                time.sleep(0.005)
                continue

            # PHASE 5 — ADVANCED CAMERA PREPROCESSING (exposure correction, white balance, contrast, gamma)
            t_inf_start = time.perf_counter()
            
            preprocessed = False
            try:
                # 1. Resize
                cv2.resize(frame, (320, 240), dst=self._resized_bgr)
                
                # 2. Auto Exposure Compensation & Gray World White Balance (Subsystem A & B)
                b, g, r = cv2.split(self._resized_bgr)
                mean_b, mean_g, mean_r = np.mean(b), np.mean(g), np.mean(r)
                mean_gray = (mean_b + mean_g + mean_r) / 3.0
                
                # Brightness multiplier depending on scene brightness
                exposure_gain = 1.0
                if mean_gray < 75:  # scene is dim
                    exposure_gain = min(1.6, 75 / (mean_gray + 1e-6))
                elif mean_gray > 195:  # scene is too bright
                    exposure_gain = max(0.7, 195 / (mean_gray + 1e-6))
                    
                b = cv2.multiply(b, (mean_gray / (mean_b + 1e-6)) * exposure_gain)
                g = cv2.multiply(g, (mean_gray / (mean_g + 1e-6)) * exposure_gain)
                r = cv2.multiply(r, (mean_gray / (mean_r + 1e-6)) * exposure_gain)
                cv2.merge([b, g, r], dst=self._resized_bgr)
                
                # 3. Contrast Normalization (Luminance Stretching) & CLAHE
                cv2.cvtColor(self._resized_bgr, cv2.COLOR_BGR2YCrCb, dst=self._ycrcb_buf)
                np.copyto(self._y_channel, self._ycrcb_buf[:, :, 0])
                cv2.normalize(self._y_channel, self._y_channel, 0, 255, cv2.NORM_MINMAX)
                
                # Gaussian noise reduction & CLAHE
                cv2.GaussianBlur(self._y_channel, (3, 3), 0, dst=self._y_channel)
                self.clahe.apply(self._y_channel, dst=self._y_channel)
                
                # Gamma brightness correction
                avg_y = np.mean(self._y_channel)
                if avg_y < 95:
                    cv2.LUT(self._y_channel, self.gamma_lut_brighten, dst=self._y_channel)
                elif avg_y > 175:
                    cv2.LUT(self._y_channel, self.gamma_lut_darken, dst=self._y_channel)
                    
                self._ycrcb_buf[:, :, 0] = self._y_channel
                cv2.cvtColor(self._ycrcb_buf, cv2.COLOR_YCrCb2RGB, dst=self._preprocessed_rgb)
                
                # 4. Adaptive Sharpening (Unsharp masking)
                blurred_rgb = cv2.GaussianBlur(self._preprocessed_rgb, (3, 3), 0)
                cv2.addWeighted(self._preprocessed_rgb, 1.3, blurred_rgb, -0.3, 0, dst=self._preprocessed_rgb)
                
                preprocessed = True
            except Exception as e:
                self.logger.warning(f"GestureService: Advanced preprocessing failed: {e}. Falling back to BGR resize.", exc_info=True)
                
            if not preprocessed:
                try:
                    cv2.resize(frame, (320, 240), dst=self._resized_bgr)
                    cv2.cvtColor(self._resized_bgr, cv2.COLOR_BGR2RGB, dst=self._preprocessed_rgb)
                except Exception as fe:
                    self.logger.error(f"GestureService: Preprocessing fallback failed: {fe}.", exc_info=True)
                    self._preprocessed_rgb = cv2.cvtColor(cv2.resize(frame, (320, 240)), cv2.COLOR_BGR2RGB)
            
            # RUN MEDIAPIPE TRACKER (Inference)
            result = self.tracker.process_frame(self._preprocessed_rgb, is_rgb=True)
            inf_dur = (time.perf_counter() - t_inf_start) * 1000.0
            
            # FPS tracking
            now = time.time()
            self._fps_timestamps.append(now)
            while self._fps_timestamps and self._fps_timestamps[0] < now - 1.0:
                self._fps_timestamps.pop(0)
                
            with self._lock:
                self.inference_time_ms = inf_dur
                self.gesture_fps = len(self._fps_timestamps)
            
            # PHASE 4 — HUNGARIAN-STYLE PERSISTENT IDENTITY MATCHING (Centroid, Size, Finger Proportions)
            t_stab_start = time.perf_counter()
            current_time = time.time()
            matched_detected_indices = set()
            matched_tracked_indices = set()
            
            this_frame_landmarks = []
            this_frame_world_landmarks = []
            this_frame_handedness = []
            this_frame_hand_ids = []
            this_frame_is_predicted = []
            this_frame_scores = []
            this_frame_bone_errors = []
            
            detected_centers = []
            detected_world_centers = []
            for hand_idx, raw_lm in enumerate(result.landmarks):
                detected_centers.append(np.array([raw_lm[MIDDLE_MCP]['x'], raw_lm[MIDDLE_MCP]['y'], raw_lm[MIDDLE_MCP]['z']], dtype=np.float32))
                # Fallback to normalized landmarks if world_landmarks is missing
                if result.world_landmarks and hand_idx < len(result.world_landmarks):
                    w_lm = result.world_landmarks[hand_idx]
                    detected_world_centers.append(np.array([w_lm[MIDDLE_MCP]['x'], w_lm[MIDDLE_MCP]['y'], w_lm[MIDDLE_MCP]['z']], dtype=np.float32))
                else:
                    detected_world_centers.append(np.array([raw_lm[MIDDLE_MCP]['x'], raw_lm[MIDDLE_MCP]['y'], raw_lm[MIDDLE_MCP]['z']], dtype=np.float32))
                    
            # Compute Cost matrix using Spatial coordinates, hand size, and finger proportions (Metacarpal ratios)
            cost_matrix = []
            for det_idx, det_w_center in enumerate(detected_world_centers):
                det_lm = result.landmarks[det_idx]
                det_size = np.linalg.norm(np.array([det_lm[INDEX_MCP]['x'], det_lm[INDEX_MCP]['y']] ) - np.array([det_lm[PINKY_MCP]['x'], det_lm[PINKY_MCP]['y']]))
                
                det_pts = np.array([[pt['x'], pt['y'], pt['z']] for pt in det_lm], dtype=np.float32)
                # Compute finger proportion vector (Index length / Middle length)
                det_prop = np.linalg.norm(det_pts[INDEX_TIP] - det_pts[INDEX_MCP]) / (np.linalg.norm(det_pts[MIDDLE_TIP] - det_pts[MIDDLE_MCP]) + 1e-6)
                
                det_costs = []
                for trk_idx, trk_hand in enumerate(self.tracked_hands):
                    d_pos = np.linalg.norm(det_w_center - trk_hand.palm_center)
                    # Hand scale difference
                    d_size = abs(det_size - trk_hand.hand_scale)
                    # Finger proportion profile match
                    d_prop = abs(det_prop - trk_hand.finger_proportions[0])
                    
                    cost = d_pos * 1.5 + d_size * 2.0 + d_prop * 1.0
                    det_costs.append(cost)
                cost_matrix.append(det_costs)
                
            # Perform greedy min cost association (matches Hungarian Solver output for small dimensions like 2x2)
            pairs = []
            for det_idx in range(len(detected_world_centers)):
                for trk_idx in range(len(self.tracked_hands)):
                    pairs.append((cost_matrix[det_idx][trk_idx], det_idx, trk_idx))
            pairs.sort(key=lambda x: x[0])
            
            for cost, det_idx, trk_idx in pairs:
                if cost < 0.35: # matching threshold (Subsystem D)
                    if det_idx not in matched_detected_indices and trk_idx not in matched_tracked_indices:
                        matched_detected_indices.add(det_idx)
                        matched_tracked_indices.add(trk_idx)
                        
                        trk_hand = self.tracked_hands[trk_idx]
                        raw_lm = result.landmarks[det_idx]
                        w_lms_source = result.world_landmarks[det_idx] if (result.world_landmarks and det_idx < len(result.world_landmarks)) else raw_lm
                        raw_score = result.scores[det_idx] if det_idx < len(result.scores) else 1.0
                        
                        # Velocity calculation
                        dt = current_time - trk_hand.last_seen
                        if dt > 0.001 and not trk_hand.is_predicted:
                            v_instant = (detected_world_centers[det_idx] - trk_hand.palm_center) / dt
                            trk_hand.velocity = 0.8 * trk_hand.velocity + 0.2 * v_instant
                        
                        trk_hand.palm_center = detected_world_centers[det_idx]
                        trk_hand.last_seen = current_time
                        trk_hand.last_prediction_time = current_time
                        trk_hand.is_predicted = False
                        trk_hand.stable_score = 0.8 * trk_hand.stable_score + 0.2 * raw_score
                        
                        # Update scale and finger proportion vectors
                        det_pts = np.array([[pt['x'], pt['y'], pt['z']] for pt in raw_lm], dtype=np.float32)
                        trk_hand.hand_scale = 0.9 * trk_hand.hand_scale + 0.1 * np.linalg.norm(det_pts[INDEX_MCP] - det_pts[PINKY_MCP])
                        det_prop = np.linalg.norm(det_pts[INDEX_TIP] - det_pts[INDEX_MCP]) / (np.linalg.norm(det_pts[MIDDLE_TIP] - det_pts[MIDDLE_MCP]) + 1e-6)
                        trk_hand.finger_proportions[0] = 0.9 * trk_hand.finger_proportions[0] + 0.1 * det_prop
                        
                        # Apply OneEuroFilter spatial smoothing on raw image landmarks
                        raw_pts = np.array([[pt['x'], pt['y'], pt['z']] for pt in raw_lm], dtype=np.float32)
                        if trk_hand.filter is None:
                            trk_hand.filter = OneEuroFilter(current_time, raw_pts)
                        filtered_pts = trk_hand.filter(current_time, raw_pts)
                        smoothed_lm = [{"x": float(p[0]), "y": float(p[1]), "z": float(p[2])} for p in filtered_pts]
                        trk_hand.last_landmarks = smoothed_lm
                        
                        # Apply Hand Pose Stabilization Layer (HPSL) to 3D metric World Landmarks
                        raw_w_pts = np.array([[pt['x'], pt['y'], pt['z']] for pt in w_lms_source], dtype=np.float32)
                        if trk_hand.world_filter is None:
                            trk_hand.world_filter = OneEuroFilter(current_time, raw_w_pts)
                        filtered_w_pts = trk_hand.world_filter(current_time, raw_w_pts)
                        
                        # Stabilize in HPSL layer (Bone lengths, joint limits, Kalman blend)
                        stab_w_pts, bone_error = self.hpsl.stabilize(trk_hand.hand_id, filtered_w_pts, trk_hand.stable_score, current_time)
                        smoothed_w_lm = [{"x": float(p[0]), "y": float(p[1]), "z": float(p[2])} for p in stab_w_pts]
                        trk_hand.last_world_landmarks = smoothed_w_lm
                        
                        this_frame_landmarks.append(smoothed_lm)
                        this_frame_world_landmarks.append(smoothed_w_lm)
                        this_frame_handedness.append(trk_hand.handedness)
                        this_frame_hand_ids.append(trk_hand.hand_id)
                        this_frame_is_predicted.append(False)
                        this_frame_scores.append(trk_hand.stable_score)
                        this_frame_bone_errors.append(bone_error)
            
            # Instantiate newly detected hands
            for det_idx, raw_lm in enumerate(result.landmarks):
                if det_idx not in matched_detected_indices:
                    raw_handedness = result.handedness[det_idx]
                    raw_score = result.scores[det_idx] if det_idx < len(result.scores) else 1.0
                    det_w_center = detected_world_centers[det_idx]
                    w_lms_source = result.world_landmarks[det_idx] if (result.world_landmarks and det_idx < len(result.world_landmarks)) else raw_lm
                    
                    new_hand = TrackedHand(self.next_hand_id, det_w_center, raw_handedness, current_time)
                    self.next_hand_id += 1
                    
                    # 1. Image space OneEuroFilter
                    raw_pts = np.array([[pt['x'], pt['y'], pt['z']] for pt in raw_lm], dtype=np.float32)
                    new_hand.filter = OneEuroFilter(current_time, raw_pts)
                    filtered_pts = new_hand.filter(current_time, raw_pts)
                    smoothed_lm = [{"x": float(p[0]), "y": float(p[1]), "z": float(p[2])} for p in filtered_pts]
                    new_hand.last_landmarks = smoothed_lm
                    
                    # 2. World space OneEuroFilter + HPSL
                    raw_w_pts = np.array([[pt['x'], pt['y'], pt['z']] for pt in w_lms_source], dtype=np.float32)
                    new_hand.world_filter = OneEuroFilter(current_time, raw_w_pts)
                    filtered_w_pts = new_hand.world_filter(current_time, raw_w_pts)
                    stab_w_pts, bone_error = self.hpsl.stabilize(new_hand.hand_id, filtered_w_pts, raw_score, current_time)
                    smoothed_w_lm = [{"x": float(p[0]), "y": float(p[1]), "z": float(p[2])} for p in stab_w_pts]
                    new_hand.last_world_landmarks = smoothed_w_lm
                    
                    self.tracked_hands.append(new_hand)
                    this_frame_landmarks.append(smoothed_lm)
                    this_frame_world_landmarks.append(smoothed_w_lm)
                    this_frame_handedness.append(new_hand.handedness)
                    this_frame_hand_ids.append(new_hand.hand_id)
                    this_frame_is_predicted.append(False)
                    this_frame_scores.append(raw_score)
                    this_frame_bone_errors.append(bone_error)
            
            # Linear Motion Prediction and Coasting for Unmatched (Occluded) Hands (Subsystem E - up to 400ms)
            for trk_hand in self.tracked_hands:
                if trk_hand.hand_id not in matched_tracked_indices:
                    time_missing = current_time - trk_hand.last_seen
                    if time_missing < 0.40:  # support 400ms occlusion coasting (Phase 2E)
                        trk_hand.is_predicted = True
                        
                        dt = current_time - trk_hand.last_prediction_time
                        trk_hand.last_prediction_time = current_time
                        
                        displacement = trk_hand.velocity * dt
                        trk_hand.palm_center += displacement
                        
                        # 1. Coast image landmarks
                        if trk_hand.last_landmarks is not None:
                            predicted_lm = []
                            for pt in trk_hand.last_landmarks:
                                predicted_lm.append({
                                    "x": pt["x"] + float(displacement[0]) * 0.15, # normalize translation
                                    "y": pt["y"] + float(displacement[1]) * 0.15,
                                    "z": pt["z"] + float(displacement[2]) * 0.15
                                })
                            trk_hand.last_landmarks = predicted_lm
                            this_frame_landmarks.append(predicted_lm)
                            
                        # 2. Coast 3D World Landmarks
                        if trk_hand.last_world_landmarks is not None:
                            predicted_w_lm = []
                            for pt in trk_hand.last_world_landmarks:
                                predicted_w_lm.append({
                                    "x": pt["x"] + float(displacement[0]),
                                    "y": pt["y"] + float(displacement[1]),
                                    "z": pt["z"] + float(displacement[2])
                                })
                            trk_hand.last_world_landmarks = predicted_w_lm
                            this_frame_world_landmarks.append(predicted_w_lm)
                            
                        this_frame_handedness.append(trk_hand.handedness)
                        this_frame_hand_ids.append(trk_hand.hand_id)
                        this_frame_is_predicted.append(True)
                        this_frame_scores.append(0.5)
                        this_frame_bone_errors.append(0.0)
            
            # Prune dead tracked hands
            self.tracked_hands = [h for h in self.tracked_hands if current_time - h.last_seen < 0.40]
            
            smoothed_result = HandLandmarksResult(
                landmarks=this_frame_landmarks,
                handedness=this_frame_handedness,
                hand_ids=this_frame_hand_ids,
                is_predicted=this_frame_is_predicted,
                scores=this_frame_scores,
                world_landmarks=this_frame_world_landmarks
            )
            
            # Run gesture classification on world landmarks when available (Phase 1)
            gestures = self.classifier.classify(smoothed_result)
            self.stabilization_time_ms = (time.perf_counter() - t_stab_start) * 1000.0
            
            # Apply hold confirmation (150ms) and cooldown timers (250ms)
            confirmed_emissions = []
            for g in gestures:
                if g.confidence < 0.65:
                    continue
                
                hand_id = g.data["hand_id"]
                prev_g_name, prev_g_time = self.last_published_gestures.get(hand_id, (None, 0.0))
                
                if g.name != prev_g_name:
                    hold_start = self.gesture_hold_times.get(hand_id)
                    if hold_start is None:
                        self.gesture_hold_times[hand_id] = current_time
                        hold_start = current_time
                    
                    if current_time - hold_start >= 0.15:
                        last_cooldown = self.cooldown_timers.get(g.name, 0.0)
                        if current_time - last_cooldown >= 0.25:
                            self.last_published_gestures[hand_id] = (g.name, current_time)
                            self.cooldown_timers[g.name] = current_time
                            confirmed_emissions.append(g)
                else:
                    self.gesture_hold_times.pop(hand_id, None)
                    confirmed_emissions.append(g)
            
            active_ids = set(smoothed_result.hand_ids)
            for hand_id in list(self.gesture_hold_times.keys()):
                if hand_id not in active_ids:
                    self.gesture_hold_times.pop(hand_id, None)
                    self.last_published_gestures.pop(hand_id, None)

            # Map tracking modes using confirmed/stabilized gestures
            self._process_interaction_modes(smoothed_result, confirmed_emissions)

            # Gather debounced finger extension states, confidences, angles, and intents
            hand_extended_states = []
            hand_finger_confidences = []
            hand_joint_angles = []
            hand_intents = []
            
            for hand_idx, hand_id in enumerate(this_frame_hand_ids):
                lm = this_frame_world_landmarks[hand_idx]
                label = this_frame_handedness[hand_idx]
                
                # Kinematics calculations on 3D World Landmarks
                ext, conf, angles = self.classifier._get_finger_kinematics(lm, label, hand_id)
                
                # Apply voting
                hist = self.classifier.finger_histories.get(hand_id, [])
                if hist:
                    voted_ext = []
                    for f_idx in range(5):
                        votes = sum(h[f_idx] for h in hist)
                        voted_ext.append(votes >= 3)
                    hand_extended_states.append(voted_ext)
                else:
                    hand_extended_states.append(ext)
                    
                hand_finger_confidences.append(conf)
                hand_joint_angles.append(angles)
                
                # 4. Predict Intent using IntentEngine (Phase 7)
                pts_arr = np.array([[pt['x'], pt['y'], pt['z']] for pt in lm], dtype=np.float32)
                palm_center_3d = pts_arr[MIDDLE_MCP]
                pinch_dist_3d = np.linalg.norm(pts_arr[THUMB_TIP] - pts_arr[INDEX_TIP])
                intent = self.intent_engine.update_and_predict(hand_id, palm_center_3d, ext, pinch_dist_3d, current_time)
                hand_intents.append(intent)

            # Gather HPSL diagnostic parameters
            joint_warnings = [self.hpsl.joint_warnings_count.get(h_id, 0) for h_id in this_frame_hand_ids]

            # Publish camera frame and landmarks for the UI overlay (Phase 6)
            event_bus.publish("CAMERA_FRAME_PROCESSED", {
                "frame": frame,
                "rgb_frame": self._preprocessed_rgb,
                "landmarks": smoothed_result.landmarks,
                "gestures": [g.name for g in gestures],  # Backward compatible (all candidates)
                "gestures_meta": [{"name": g.name, "confidence": g.confidence, "hand_id": g.data["hand_id"]} for g in gestures],
                "handedness": smoothed_result.handedness,
                "hand_ids": smoothed_result.hand_ids,
                "is_predicted": smoothed_result.is_predicted,
                "landmark_confidence": [float(score) for score in smoothed_result.scores],
                "extended_fingers": hand_extended_states,
                "finger_confidences": hand_finger_confidences,
                "joint_angles_meta": hand_joint_angles,
                "intents": hand_intents,  # Expose intents
                "bone_errors": this_frame_bone_errors,  # Expose bone solvers errors
                "joint_warnings": joint_warnings,  # Joint limit warnings count
                "camera_fps": camera_srv.camera_fps if camera_srv else self.gesture_fps,
                "gesture_fps": self.gesture_fps,
                "inference_time_ms": self.inference_time_ms,
                "stabilization_time_ms": self.stabilization_time_ms,
                "capture_time_ms": camera_srv.capture_time_ms if camera_srv else 0.0
            })
            
            self._frame_processed_count += 1

            # Publish confirmed gesture detected events to EventBus
            for gesture in confirmed_emissions:
                event_bus.publish("GESTURE_DETECTED", {
                    "gesture": gesture.name,
                    "confidence": gesture.confidence,
                    "data": gesture.data
                })

            # Control capture rate (target: 30 FPS)
            elapsed = time.perf_counter() - t_loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _process_interaction_modes(self, tracker_result: HandLandmarksResult, gestures: List[DetectedGesture]):
        pinches = [g for g in gestures if g.name in ["Pinch", "OK"]]
        mode = "idle"
        if len(pinches) >= 2:
            mode = "zoom"
        elif len(pinches) == 1:
            mode = "spin"

        if mode != self.prev_mode:
            self.prev_spin_grab = None
            self.prev_zoom_dist = None
            self.prev_mode = mode

        if mode == "spin":
            grab_pt = pinches[0].data["center"]
            if self.prev_spin_grab:
                dx = grab_pt["x"] - self.prev_spin_grab["x"]
                dy = grab_pt["y"] - self.prev_spin_grab["y"]
                if abs(dx) > 1e-4 or abs(dy) > 1e-4:
                    event_bus.publish("REACTOR_ROTATE", {
                        "d_theta": dx * self.rotate_speed,
                        "d_phi": dy * self.rotate_speed
                    })
                self.prev_spin_grab = {
                    "x": self.prev_spin_grab["x"] + (grab_pt["x"] - self.prev_spin_grab["x"]) * self.smoothing,
                    "y": self.prev_spin_grab["y"] + (grab_pt["y"] - self.prev_spin_grab["y"]) * self.smoothing
                }
            else:
                self.prev_spin_grab = grab_pt

        elif mode == "zoom":
            p1 = pinches[0].data["center"]
            p2 = pinches[1].data["center"]
            dist = math.hypot(p1["x"] - p2["x"], p1["y"] - p2["y"])
            if self.prev_zoom_dist and dist > 1e-4:
                factor = min(1.15, max(0.85, self.prev_zoom_dist / dist))
                event_bus.publish("REACTOR_ZOOM", {"factor": factor})
            self.prev_zoom_dist = dist
