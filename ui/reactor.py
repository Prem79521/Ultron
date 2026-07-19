import time
import math
import logging
from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtGui import QPainter, QMouseEvent, QWheelEvent, QColor

from ultron.core.event_bus import event_bus, Event
from ui.reactor_renderer import BaseReactorRenderer, QPainterReactorRenderer

class UltronReactorWidget(QWidget):
    """PySide6 custom painted dashboard widget rendering the Cognitive Reactor."""
    def __init__(self, parent=None, renderer: Optional[BaseReactorRenderer] = None):
        super().__init__(parent)
        self.renderer = renderer or QPainterReactorRenderer()
        
        # State parameters
        self.state = "sleeping"  # sleeping, listening, thinking, speaking, executing, idle
        self.time_start = time.time()
        self.time_elapsed = 0.0
        
        # Rotations and zoom offsets
        self.rot_x = 0.0
        self.rot_y = 0.0
        self.zoom_factor = 1.0
        
        # Smooth interpolation targets
        self.target_rot_x = 0.0
        self.target_rot_y = 0.0
        self.target_zoom_factor = 1.0
        
        # Mouse interaction tracking
        self.last_mouse_pos = None
        self.is_dragging = False

        # Diagnostics
        self.ui_fps = 0.0
        self.render_time_ms = 0.0
        self._last_paint_time = time.perf_counter()

        # Refresh Timer (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(16)

        # Connect to EventBus messages
        event_bus.subscribe("VOICE_STATE_CHANGED", self._on_voice_state_changed, priority=10)
        event_bus.subscribe("REACTOR_ROTATE", self._on_reactor_rotate, priority=5)
        event_bus.subscribe("REACTOR_ZOOM", self._on_reactor_zoom, priority=5)
        
        self.destroyed.connect(self._cleanup)

    def set_state(self, state: str):
        """Programmatic state setter."""
        self.state = state.lower()
        self.update()

    @Slot()
    def _on_tick(self):
        self.time_elapsed = time.time() - self.time_start
        
        # Smoothly interpolate rotations/zooms towards targets (damping)
        self.rot_x += (self.target_rot_x - self.rot_x) * 0.12
        self.rot_y += (self.target_rot_y - self.rot_y) * 0.12
        self.zoom_factor += (self.target_zoom_factor - self.zoom_factor) * 0.12

        # Add subtle ambient drifting animation (float/sway effect)
        if not self.is_dragging:
            self.rot_x += math.sin(self.time_elapsed * 0.4) * 0.0008
            self.rot_y += math.cos(self.time_elapsed * 0.35) * 0.0006
        
        self.update()

    def _on_voice_state_changed(self, event: Event):
        # Event payload format: {"state": "SLEEPING", "old_state": ...}
        payload = event.payload
        if isinstance(payload, dict) and "state" in payload:
            self.set_state(payload["state"])

    def _on_reactor_rotate(self, event: Event):
        payload = event.payload
        if isinstance(payload, dict):
            # Coordinates are deltas in degrees/radians
            self.target_rot_x += payload.get("d_theta", 0.0)
            self.target_rot_y += payload.get("d_phi", 0.0)

    def _on_reactor_zoom(self, event: Event):
        payload = event.payload
        if isinstance(payload, dict):
            factor = payload.get("factor", 1.0)
            # Apply scaling boundary
            self.target_zoom_factor = min(3.5, max(0.4, self.target_zoom_factor * factor))

    # ── MOUSE INTERACTION EVENT HANDLERS (ORBIT CONTROLS EQUIVALENT) ──
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.position()
            self.is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging and self.last_mouse_pos:
            pos = event.position()
            dx = pos.x() - self.last_mouse_pos.x()
            dy = pos.y() - self.last_mouse_pos.y()
            
            # Map drag movement to sphere coordinates scaling
            self.target_rot_x += dx * 0.007
            self.target_rot_y = min(math.pi / 2.1, max(-math.pi / 2.1, self.target_rot_y - dy * 0.007))
            
            self.last_mouse_pos = pos

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event: QWheelEvent):
        # Scroll up zooms in, scroll down zooms out
        steps = event.angleDelta().y() / 120.0
        factor = 1.0 - (steps * 0.08)
        self.target_zoom_factor = min(3.5, max(0.4, self.target_zoom_factor * factor))

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        # Reset camera view on double click
        self.target_rot_x = 0.0
        self.target_rot_y = 0.0
        self.target_zoom_factor = 1.0

    def paintEvent(self, event):
        t0 = time.perf_counter()
        painter = QPainter(self)
        try:
            self.renderer.render(
                painter,
                self.rect(),
                self.state,
                self.time_elapsed,
                self.rot_x,
                self.rot_y,
                self.zoom_factor
            )
        finally:
            painter.end()
        self.render_time_ms = (time.perf_counter() - t0) * 1000.0
        
        now = time.perf_counter()
        dt = now - self._last_paint_time
        self._last_paint_time = now
        if dt > 0.0:
            fps = 1.0 / dt
            self.ui_fps = 0.95 * self.ui_fps + 0.05 * fps

    def _cleanup(self):
        # Clean up subscriptions on delete
        event_bus.unsubscribe("VOICE_STATE_CHANGED", self._on_voice_state_changed)
        event_bus.unsubscribe("REACTOR_ROTATE", self._on_reactor_rotate)
        event_bus.unsubscribe("REACTOR_ZOOM", self._on_reactor_zoom)
        self.timer.stop()
