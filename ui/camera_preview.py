import cv2
import math
import numpy as np
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Slot, QPointF, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush, QFont

from ultron.core.event_bus import event_bus, Event

class UltronCameraPreviewWidget(QWidget):
    """Native PySide6 camera preview overlay displaying Sepia/Amber video feed and landmarks."""
    frame_processed = Signal(QImage, dict)
    active_instances = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(208, 156)
        self.setObjectName("GlassPanel")
        
        # Track active instance
        UltronCameraPreviewWidget.active_instances.append(self)
        
        self.current_pixmap: Optional[QPixmap] = None
        self.meta: dict = {}
        self.active_status = "STANDBY"
        
        # Load initial debug overlay setting from database
        self.debug_mode = False
        try:
            from ultron.memory import get_memory_manager
            mem = get_memory_manager()
            if mem:
                records = mem.list_records("provider_settings", limit=100)
                rec = next((r for r in records if r["title"] == "vision_debug_overlay"), None)
                if rec:
                    self.debug_mode = rec["content"].lower() == "true"
        except Exception:
            pass
        
        self.setStyleSheet("""
            QWidget#GlassPanel {
                background-color: rgba(20, 10, 0, 0.4);
                border: 1px solid rgba(255, 170, 48, 0.3);
                border-radius: 4px;
            }
        """)

        # Connect custom signal to apply slot on main thread
        self.frame_processed.connect(self._apply_frame, Qt.ConnectionType.QueuedConnection)

        # Subscribe to frame and debug toggle notifications
        event_bus.subscribe("CAMERA_FRAME_PROCESSED", self._on_frame_processed, priority=5)
        event_bus.subscribe("VISION_DEBUG_TOGGLED", self._on_debug_toggled)
        
        self.destroyed.connect(self._cleanup)

    def _on_debug_toggled(self, event: Event):
        payload = event.payload
        if isinstance(payload, dict):
            self.debug_mode = payload.get("enabled", False)

    def _on_frame_processed(self, event: Event):
        payload = event.payload
        if not isinstance(payload, dict):
            return

        frame = payload.get("frame")
        rgb_frame = payload.get("rgb_frame")
        
        if rgb_frame is not None:
            # 1. Flip horizontally to achieve mirror behavior
            rgb = cv2.flip(rgb_frame, 1)
            # 2. Scale image to widget size for performance (320x240 to 208x156)
            rgb = cv2.resize(rgb, (208, 156))
        elif frame is not None:
            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (208, 156))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            return

        # 3. Apply custom amber-sepia color mapping (highly optimized in-place operations)
        rgb[:, :, 1] = (rgb[:, :, 1] * 0.70).astype(np.uint8)
        rgb[:, :, 2] = (rgb[:, :, 2] * 0.20).astype(np.uint8)

        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()

        landmarks = payload.get("landmarks", [])
        gestures = payload.get("gestures", [])
        is_predicted = payload.get("is_predicted", [])
        intents = payload.get("intents", [])
        
        # Determine status description (with occlusion/coasting flag)
        hands_count = len(landmarks)
        if hands_count > 0:
            gesture_name = gestures[0] if gestures else "TRACKING"
            intent_name = intents[0] if intents else "HOVER"
            coasting_suffix = " (COAST)" if any(is_predicted) else ""
            active_status = f"{hands_count} HAND{'S' if hands_count > 1 else ''} · {gesture_name.upper()} · {intent_name.upper()}{coasting_suffix}"
        else:
            active_status = "SHOW HANDS"

        meta = {
            "landmarks": landmarks,
            "gestures": gestures,
            "gestures_meta": payload.get("gestures_meta", []),
            "handedness": payload.get("handedness", []),
            "hand_ids": payload.get("hand_ids", []),
            "is_predicted": is_predicted,
            "landmark_confidence": payload.get("landmark_confidence", []),
            "extended_fingers": payload.get("extended_fingers", []),
            "finger_confidences": payload.get("finger_confidences", []),
            "intents": intents,
            "bone_errors": payload.get("bone_errors", []),
            "joint_warnings": payload.get("joint_warnings", []),
            "camera_fps": payload.get("camera_fps", 0.0),
            "gesture_fps": payload.get("gesture_fps", 0.0),
            "inference_time_ms": payload.get("inference_time_ms", 0.0),
            "stabilization_time_ms": payload.get("stabilization_time_ms", 0.0),
            "capture_time_ms": payload.get("capture_time_ms", 0.0),
            "active_status": active_status
        }

        # Safely emit signal to run on main thread
        self.frame_processed.emit(q_img, meta)

    @Slot(QImage, dict)
    def _apply_frame(self, q_img: QImage, meta: dict) -> None:
        """Applies a processed QImage as the display pixmap. Called only on the main thread."""
        self.current_pixmap = QPixmap.fromImage(q_img)
        self.meta = meta
        self.active_status = meta.get("active_status", "STANDBY")
        self.update()

    def _calculate_angle(self, p1: dict, p2: dict, p3: dict) -> float:
        """Calculates the 3D joint bending angle in degrees."""
        v1 = np.array([p2["x"] - p1["x"], p2["y"] - p1["y"], p2["z"] - p1["z"]], dtype=np.float32)
        v2 = np.array([p3["x"] - p1["x"], p3["y"] - p1["y"], p3["z"] - p1["z"]], dtype=np.float32) # relative to joint
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 < 1e-5 or n2 < 1e-5:
            return 0.0
        cos_theta = np.dot(v1, v2) / (n1 * n2)
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        return math.degrees(math.acos(cos_theta))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Render sepia/amber background frame
        if self.current_pixmap:
            painter.drawPixmap(0, 0, self.current_pixmap)
        else:
            painter.fillRect(self.rect(), QColor(10, 5, 0, 180))
            
        # 2. Render landmark overlay (Pinch indicator or full skeleton in debug mode)
        landmarks = self.meta.get("landmarks", [])
        hand_ids = self.meta.get("hand_ids", [])
        handedness = self.meta.get("handedness", [])
        is_predicted = self.meta.get("is_predicted", [])
        extended_fingers = self.meta.get("extended_fingers", [])
        finger_confidences = self.meta.get("finger_confidences", [])
        landmark_confidence = self.meta.get("landmark_confidence", [])
        gestures = self.meta.get("gestures", [])
        gestures_meta = self.meta.get("gestures_meta", [])
        intents = self.meta.get("intents", [])
        bone_errors = self.meta.get("bone_errors", [])
        joint_warnings = self.meta.get("joint_warnings", [])
        
        skeleton_links = [
            (0, 1), (1, 2), (2, 3), (3, 4),      # Thumb
            (0, 5), (5, 6), (6, 7), (7, 8),      # Index
            (0, 9), (9, 10), (10, 11), (11, 12),  # Middle
            (0, 13), (13, 14), (14, 15), (15, 16),# Ring
            (0, 17), (17, 18), (18, 19), (19, 20),# Pinky
            (5, 9), (9, 13), (13, 17)            # Palm base
        ]
        
        if landmarks:
            for hand_idx, lm in enumerate(landmarks):
                h_id = hand_ids[hand_idx] if hand_idx < len(hand_ids) else hand_idx
                h_label = handedness[hand_idx] if hand_idx < len(handedness) else "Unknown"
                ext_states = extended_fingers[hand_idx] if hand_idx < len(extended_fingers) else [False]*5
                is_coasting = is_predicted[hand_idx] if hand_idx < len(is_predicted) else False
                
                # Fetch gesture name and confidence from metadata
                g_meta = next((g for g in gestures_meta if g["hand_id"] == h_id), None)
                g_name = g_meta["name"] if g_meta else "None"
                g_conf = g_meta["confidence"] if g_meta else 0.0
                f_count = sum(ext_states)
                
                # 2a. Draw Palm Center crosshairs (geometric centroid of Wrist, Index, Middle, and Pinky MCPs)
                pts_centroid = [0, 5, 9, 17]
                cx = sum((1.0 - lm[p]["x"]) for p in pts_centroid) / 4.0 * self.width()
                cy = sum(lm[p]["y"] for p in pts_centroid) / 4.0 * self.height()
                
                painter.setPen(QPen(QColor(255, 170, 48, 180) if not is_coasting else QColor(255, 200, 100, 100), 1.0, Qt.PenStyle.SolidLine))
                painter.drawLine(QPointF(cx - 6, cy), QPointF(cx + 6, cy))
                painter.drawLine(QPointF(cx, cy - 6), QPointF(cx, cy + 6))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(cx, cy), 3.5, 3.5)
                
                # 2b. Draw Palm Coordinate Axes & Palm Normal Vector in Screen space (Phase 6)
                if self.debug_mode:
                    # Y axis vector (green line, Wrist to Middle MCP)
                    vy_x = ((1.0 - lm[9]["x"]) - (1.0 - lm[0]["x"])) * self.width()
                    vy_y = (lm[9]["y"] - lm[0]["y"]) * self.height()
                    len_y = math.hypot(vy_x, vy_y) + 1e-6
                    vy_x, vy_y = vy_x / len_y, vy_y / len_y
                    
                    # X axis vector (red line, Index MCP to Pinky MCP)
                    vx_x = ((1.0 - lm[5]["x"]) - (1.0 - lm[17]["x"])) * self.width()
                    vx_y = (lm[5]["y"] - lm[17]["y"]) * self.height()
                    len_x = math.hypot(vx_x, vx_y) + 1e-6
                    vx_x, vx_y = vx_x / len_x, vx_y / len_x
                    
                    # Z Palm Normal vector (blue line, cross product representation)
                    vz_x = -vy_y
                    vz_y = vy_x
                    
                    # Draw RGB Axes starting from centroid
                    painter.setPen(QPen(QColor(230, 57, 70), 1.2, Qt.PenStyle.SolidLine)) # Red = X
                    painter.drawLine(QPointF(cx, cy), QPointF(cx + 12 * vx_x, cy + 12 * vx_y))
                    
                    painter.setPen(QPen(QColor(46, 196, 182), 1.2, Qt.PenStyle.SolidLine)) # Green = Y
                    painter.drawLine(QPointF(cx, cy), QPointF(cx + 12 * vy_x, cy + 12 * vy_y))
                    
                    painter.setPen(QPen(QColor(0, 119, 182), 1.2, Qt.PenStyle.SolidLine))  # Blue = Z (Normal)
                    painter.drawLine(QPointF(cx, cy), QPointF(cx + 12 * vz_x, cy + 12 * vz_y))

                    # 2c. Draw Skeleton connections (Dashed if predicted/coasting, Solid if tracked)
                    pen_style = Qt.PenStyle.DashLine if is_coasting else Qt.PenStyle.SolidLine
                    pen_color = QColor(255, 200, 100, 90) if is_coasting else QColor(255, 170, 48, 120)
                    painter.setPen(QPen(pen_color, 1.0, pen_style))
                    for p1, p2 in skeleton_links:
                        x1 = (1.0 - lm[p1]["x"]) * self.width()
                        y1 = lm[p1]["y"] * self.height()
                        x2 = (1.0 - lm[p2]["x"]) * self.width()
                        y2 = lm[p2]["y"] * self.height()
                        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                    
                    # 2d. Draw joint nodes
                    for joint_id in range(21):
                        x = (1.0 - lm[joint_id]["x"]) * self.width()
                        y = lm[joint_id]["y"] * self.height()
                        
                        if joint_id in [4, 8, 12, 16, 20]:  # Finger tips
                            f_idx = [4, 8, 12, 16, 20].index(joint_id)
                            is_ext = ext_states[f_idx]
                            color = QColor(46, 196, 182) if is_ext else QColor(230, 57, 70)  # Green/Red
                            sz = 4.5
                        else:
                            color = QColor(255, 200, 100, 180)
                            sz = 2.0
                        
                        painter.setBrush(QBrush(color))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawEllipse(QPointF(x, y), sz, sz)
                        
                        # Draw joint ID labels in tiny font
                        painter.setPen(QPen(QColor(255, 255, 255, 160), 1.0, Qt.PenStyle.SolidLine))
                        painter.setFont(QFont("Courier New", 5))
                        painter.drawText(int(x + 4), int(y + 3), str(joint_id))
                    
                    # 2e. Draw finger extension labels near tips
                    finger_labels = ["T", "I", "M", "R", "P"]
                    tip_ids = [4, 8, 12, 16, 20]
                    for f_idx, tip_id in enumerate(tip_ids):
                        x = (1.0 - lm[tip_id]["x"]) * self.width()
                        y = lm[tip_id]["y"] * self.height()
                        is_ext = ext_states[f_idx]
                        
                        painter.setPen(QPen(QColor(46, 196, 182) if is_ext else QColor(230, 57, 70), 1.0, Qt.PenStyle.SolidLine))
                        painter.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
                        painter.drawText(int(x - 12), int(y - 5), finger_labels[f_idx])
                        
                    # 2f. Draw Hand Identification Label near wrist
                    wrist_x = (1.0 - lm[0]["x"]) * self.width()
                    wrist_y = lm[0]["y"] * self.height()
                    
                    if is_coasting:
                        painter.setPen(QPen(QColor(230, 200, 50), 1.0, Qt.PenStyle.SolidLine))
                        painter.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
                        painter.drawText(int(wrist_x - 20), int(wrist_y + 12), f"{h_label[0]}-{h_id} (COAST)")
                    else:
                        painter.setPen(QPen(QColor(255, 170, 48), 1.0, Qt.PenStyle.SolidLine))
                        painter.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
                        painter.drawText(int(wrist_x - 15), int(wrist_y + 12), f"{h_label[0]}-{h_id}")
                    
                    # 2g. Draw gesture name, confidence and finger count
                    painter.setFont(QFont("Courier New", 6))
                    painter.setPen(QPen(QColor(255, 220, 150), 1.0, Qt.PenStyle.SolidLine))
                    painter.drawText(int(wrist_x - 20), int(wrist_y + 22), f"{g_name.upper()} ({int(g_conf * 100)}%)")
                    painter.drawText(int(wrist_x - 20), int(wrist_y + 30), f"FINGERS: {f_count}")
                    
                else:
                    # Normal mode: draw thumb-to-index line segment
                    thumb_x = (1.0 - lm[4]["x"]) * self.width()
                    thumb_y = lm[4]["y"] * self.height()
                    index_x = (1.0 - lm[8]["x"]) * self.width()
                    index_y = lm[8]["y"] * self.height()
                    
                    wrist = lm[0]
                    mcp = lm[9]
                    scale = math.hypot(wrist["x"] - mcp["x"], wrist["y"] - mcp["y"])
                    dist = math.hypot(lm[4]["x"] - lm[8]["x"], lm[4]["y"] - lm[8]["y"])
                    pinched = scale > 1e-5 and (dist / scale) < 0.35
                    
                    pen_color = QColor(255, 200, 100) if pinched else QColor(255, 170, 48, 120)
                    pen_width = 2.0 if pinched else 1.0
                    painter.setPen(QPen(pen_color, pen_width, Qt.PenStyle.SolidLine))
                    painter.drawLine(QPointF(thumb_x, thumb_y), QPointF(index_x, index_y))
                    
                    painter.setBrush(QBrush(QColor(255, 220, 120) if pinched else QColor(255, 170, 48, 200)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    node_sz = 5.0 if pinched else 3.5
                    painter.drawEllipse(QPointF(thumb_x, thumb_y), node_sz, node_sz)
                    painter.drawEllipse(QPointF(index_x, index_y), node_sz, node_sz)

        # 3. Phase 6 HUD Diagnostic Panels (Bone Errors, Warnings, Intents, Confidences)
        if self.debug_mode and landmarks:
            for hand_idx, lm in enumerate(landmarks):
                if hand_idx >= 2:
                    break
                
                h_id = hand_ids[hand_idx] if hand_idx < len(hand_ids) else hand_idx
                h_label = handedness[hand_idx] if hand_idx < len(handedness) else "Unknown"
                is_coasting = is_predicted[hand_idx] if hand_idx < len(is_predicted) else False
                ext_states = extended_fingers[hand_idx] if hand_idx < len(extended_fingers) else [False]*5
                
                l_conf = landmark_confidence[hand_idx] if hand_idx < len(landmark_confidence) else 1.0
                f_confs = finger_confidences[hand_idx] if hand_idx < len(finger_confidences) else [1.0]*5
                intent = intents[hand_idx] if hand_idx < len(intents) else "HOVER"
                b_err = bone_errors[hand_idx] if hand_idx < len(bone_errors) else 0.0
                j_warn = joint_warnings[hand_idx] if hand_idx < len(joint_warnings) else 0
                
                # Panel position: Hand 0 at top-left, Hand 1 at top-right
                px = 6 if hand_idx == 0 else 138
                py = 38
                pw = 64
                ph = 70  # taller to fit extra diagnostics
                
                # Draw transparent panel background & border
                painter.fillRect(px, py, pw, ph, QColor(20, 10, 0, 175))
                painter.setPen(QPen(QColor(255, 170, 48, 120), 1.0, Qt.PenStyle.SolidLine))
                painter.drawRect(px, py, pw - 1, ph - 1)
                
                # Header: "L-0 (98%)" or "R-1 (COAST)"
                h_text = f"{h_label[0]}-{h_id}"
                c_text = "COAST" if is_coasting else f"{int(l_conf * 100)}%"
                painter.setFont(QFont("Courier New", 5, QFont.Weight.Bold))
                painter.drawText(px + 4, py + 8, f"{h_text} ({c_text})")
                
                # Intent: "INT: SELECT" (in Cyan for cinematic style)
                painter.setPen(QPen(QColor(0, 180, 216), 1.0, Qt.PenStyle.SolidLine))
                painter.drawText(px + 4, py + 15, f"INT:{intent.upper()[:7]}")
                
                # Bone Error & Warnings: "E:0.2c W:0"
                painter.setPen(QPen(QColor(255, 200, 100, 180), 1.0, Qt.PenStyle.SolidLine))
                # bone error converted to centimeters for readability
                painter.drawText(px + 4, py + 22, f"E:{b_err*100:.1f}c W:{j_warn}")
                
                # Draw 5 fingers diagnostics
                finger_names = ["THU", "IND", "MID", "RNG", "PNK"]
                painter.setFont(QFont("Courier New", 5))
                for f_idx in range(5):
                    is_ext = ext_states[f_idx]
                    f_conf = f_confs[f_idx]
                    state_text = "EXT" if is_ext else "FLD"
                    
                    text_color = QColor(46, 196, 182) if is_ext else QColor(230, 57, 70)
                    painter.setPen(QPen(text_color, 1.0, Qt.PenStyle.SolidLine))
                    
                    line_y = py + 31 + f_idx * 7.5
                    painter.drawText(px + 4, int(line_y), f"{finger_names[f_idx]}:{state_text} {int(f_conf * 100)}%")

        # 4. HUD overlay info bar at the bottom
        painter.fillRect(0, self.height() - 22, self.width(), 22, QColor(10, 5, 0, 180))
        painter.setPen(QPen(QColor(255, 170, 48), 1.0, Qt.PenStyle.SolidLine))
        font = QFont("Courier New", 7, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(6, self.height() - 7, self.active_status)
        
        # 5. Debug overlay diagnostics bar at the top (Task 13 / Phase 6)
        if self.debug_mode:
            painter.fillRect(0, 0, self.width(), 35, QColor(10, 5, 0, 200))
            painter.setPen(QPen(QColor(255, 170, 48), 1.0, Qt.PenStyle.SolidLine))
            painter.setFont(QFont("Courier New", 6))
            
            cam_fps = self.meta.get("camera_fps", 0.0)
            ges_fps = self.meta.get("gesture_fps", 0.0)
            cap_ms = self.meta.get("capture_time_ms", 0.0)
            inf_ms = self.meta.get("inference_time_ms", 0.0)
            stab_ms = self.meta.get("stabilization_time_ms", 0.0)
            g_state = gestures[0] if gestures else "NONE"
            
            painter.drawText(6, 10, f"CAM/GES FPS: {cam_fps:<2.0f}/{ges_fps:<2.0f} | STAB: {stab_ms:<3.1f}ms")
            painter.drawText(6, 20, f"CAP: {cap_ms:<3.1f}ms | INF: {inf_ms:<3.1f}ms")
            painter.drawText(6, 30, f"GESTURE: {g_state.upper()}")
        
        # Frame border
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 170, 48, 90), 1.0, Qt.PenStyle.SolidLine))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        
        painter.end()

    def _cleanup(self):
        event_bus.unsubscribe("CAMERA_FRAME_PROCESSED", self._on_frame_processed)
        event_bus.unsubscribe("VISION_DEBUG_TOGGLED", self._on_debug_toggled)
        if self in UltronCameraPreviewWidget.active_instances:
            UltronCameraPreviewWidget.active_instances.remove(self)
