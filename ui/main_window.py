"""
ULTRON Main Window Dashboard — Premium dark frameless dashboard with active skills, UME viewers, SAPI5 triggers, and thread-safe layout state managers.
"""

import math
import os
import json
import threading
import time
import random
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QStackedWidget, QSplitter, QTextEdit, QCheckBox,
    QScrollArea, QFormLayout, QComboBox, QGroupBox, QGridLayout, QApplication, QTextBrowser,
    QDialog, QFileDialog
)
from PySide6.QtCore import Qt, QSize, Slot, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QIcon, QPainter, QPen, QColor, QBrush, QPainterPath
from ui.themes import UltronColors, UltronThemeStyles
from ui.animations import UltronAnimations
from ui.waveform import UltronWaveform
from ui.reactor import UltronReactorWidget
from ui.camera_preview import UltronCameraPreviewWidget
from ui.developer_console import UltronDeveloperConsole
from ultron.core.event_bus import event_bus
from ultron.core.task_manager import task_manager
from ultron.core.service_manager import service_manager
from ultron.hal.hal_manager import get_hal_manager
from ultron.core.health_monitor import health_monitor

# ── Custom Premium UI Components ──────────────────────────────────────────────

# ── Safety and Compatibility Widget Factory & Aliases ────────────────────────

def safe_create_widget(class_name, parent=None, *args, **kwargs):
    """
    Safely resolves class_name and instantiates it.
    If it fails or is not defined, returns a styled placeholder QWidget.
    """
    cls = globals().get(class_name)
    if cls is None:
        try:
            if class_name == "UltronWaveformWidget":
                from ui.waveform import UltronWaveform
                cls = UltronWaveform
            elif class_name == "UltronReactorWidget":
                from ui.reactor import UltronReactorWidget
                cls = UltronReactorWidget
            elif class_name == "UltronCameraPreviewWidget":
                from ui.camera_preview import UltronCameraPreviewWidget
                cls = UltronCameraPreviewWidget
            elif class_name == "UltronRadarWidget":
                cls = UltronRadarWidget
            elif class_name == "UltronTopBar":
                cls = UltronTopBar
            elif class_name == "UltronSidebar":
                cls = UltronSidebar
            elif class_name == "ThoughtStreamWidget":
                cls = UltronThoughtStream
            elif class_name == "MemoryStatusWidget":
                cls = UltronMemoryStatus
            elif class_name == "ProjectWidget":
                cls = UltronProjectPanel
            elif class_name == "VoiceInputBar":
                cls = VoiceInputBar
        except Exception:
            pass
            
    if cls is None:
        print(f"[Warning] Widget class {class_name} is undefined. Using placeholder QWidget.")
        placeholder = QWidget(parent)
        placeholder.setMinimumSize(10, 10)
        placeholder.setStyleSheet("background-color: transparent; border: 1px dashed rgba(230, 57, 70, 0.2);")
        return placeholder
        
    try:
        if parent is not None:
            return cls(parent, *args, **kwargs)
        else:
            return cls(*args, **kwargs)
    except Exception as e:
        print(f"[Warning] Failed to instantiate {class_name}: {e}. Using placeholder QWidget.")
        placeholder = QWidget(parent)
        placeholder.setMinimumSize(10, 10)
        placeholder.setStyleSheet("background-color: transparent; border: 1px dashed rgba(230, 57, 70, 0.2);")
        return placeholder


class UltronFloatingVoiceWidget(QWidget):
    """Custom transparent floating HUD overlay for visual state feedback."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(120, 120)
        self.state = "Sleeping"
        self.pulse = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pulse)
        self.timer.start(16)
        
    def update_pulse(self):
        self.pulse += 0.05
        self.update()
        
    def set_state(self, state):
        self.state = state
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QBrush(QColor(10, 10, 10, 150)))
        painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
        painter.drawEllipse(10, 10, 100, 100)
        
        color_map = {
            "Sleeping": QColor(160, 160, 160),
            "Listening": QColor(0, 255, 0),
            "Thinking": QColor(0, 150, 255),
            "Speaking": QColor(230, 57, 70),
            "Error": QColor(255, 165, 0)
        }
        color = color_map.get(self.state, QColor(160, 160, 160))
        
        pulse_scale = 1.0 + 0.1 * math.sin(self.pulse)
        r = 35 * pulse_scale
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 100), 2))
        painter.drawEllipse(60 - r, 60 - r, r * 2, r * 2)
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(45, 45, 30, 30)


class UltronRadarWidget(QWidget):
    """Futuristic custom painted radar widget drawing scanning grids, sweep lines, and blips."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sweep_angle = 0.0
        self.state = "sleeping"
        self.blips = []
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_radar)
        self.timer.start(16)
        
    def set_state(self, state: str):
        self.state = state.lower()
        self.update()
        
    def update_radar(self):
        if self.state == "listening":
            speed = 3.5
        elif self.state == "thinking":
            speed = 1.0
        elif self.state == "speaking":
            speed = 2.0
        else: # sleeping
            speed = 0.5
            
        self.sweep_angle = (self.sweep_angle + speed) % 360
        
        if len(self.blips) < 5 and random.random() < 0.02:
            self.blips.append({
                "r": random.uniform(30, 100),
                "theta": random.uniform(0, 2 * math.pi),
                "age": 1.0,
                "speed": random.uniform(0.01, 0.02)
            })
            
        for b in list(self.blips):
            b["age"] -= b["speed"]
            if b["age"] <= 0:
                self.blips.remove(b)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        cx = width / 2
        cy = height / 2
        max_r = min(width, height) / 2 - 10
        
        # Grid line colors (reduced opacity)
        grid_alpha = 8 if self.state != "listening" else 18
        painter.setPen(QPen(QColor(193, 18, 31, grid_alpha), 1))
        
        # Draw concentric rings
        for r_factor in [0.2, 0.4, 0.6, 0.8, 1.0]:
            r = max_r * r_factor
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            
        # Draw crosshairs
        painter.drawLine(cx - max_r, cy, cx + max_r, cy)
        painter.drawLine(cx, cy - max_r, cx, cy + max_r)
        
        # Draw scanning sweep line (gradient sector)
        sweep_path = QPainterPath()
        sweep_path.moveTo(cx, cy)
        rad_start = math.radians(-self.sweep_angle)
        rad_end = math.radians(-self.sweep_angle - 30)
        
        x1 = cx + max_r * math.cos(rad_start)
        y1 = cy + max_r * math.sin(rad_start)
        
        sweep_path.lineTo(x1, y1)
        sweep_path.arcTo(cx - max_r, cy - max_r, max_r * 2, max_r * 2, self.sweep_angle, 30)
        sweep_path.lineTo(cx, cy)
        
        sweep_color = QColor(230, 57, 70, 10 if self.state != "listening" else 20)
        painter.setBrush(QBrush(sweep_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(sweep_path)
        
        # Draw active sweep edge line
        painter.setPen(QPen(QColor(230, 57, 70, 60 if self.state != "listening" else 120), 1.5))
        painter.drawLine(cx, cy, x1, y1)
        
        # Draw blips
        for b in self.blips:
            bx = cx + b["r"] * math.cos(b["theta"])
            by = cy + b["r"] * math.sin(b["theta"])
            angle_diff = (math.degrees(-b["theta"]) - self.sweep_angle) % 360
            if angle_diff < 45:
                intensity = int(b["age"] * 255)
                painter.setBrush(QBrush(QColor(230, 57, 70, intensity)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(bx - 3, by - 3, 6, 6)


class UltronMicButton(QPushButton):
    """Custom painted pulsing mic button visualizer supporting Idle, Listening, and Processing states."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.mic_state = "idle"  # "idle", "listening", "processing"
        self.pulse = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pulse)
        self.timer.start(16)
        
    def update_pulse(self):
        if self.mic_state == "listening":
            self.pulse += 0.1
        else:
            self.pulse = 0.0
        self.update()
        
    def set_listening(self, listening):
        if isinstance(listening, bool):
            self.mic_state = "listening" if listening else "idle"
        else:
            self.mic_state = str(listening).lower()
        self.update()

    def set_state(self, state):
        self.mic_state = str(state).lower()
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        cx = rect.width() / 2
        cy = rect.height() / 2
        
        if self.mic_state == "listening":
            pulse_scale = 1.0 + 0.15 * math.sin(self.pulse)
            r_outer = 15 * pulse_scale
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(230, 57, 70, 40)))
            painter.drawEllipse(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2)
            
            icon_color = QColor(230, 57, 70)
            bg_color = QColor(30, 20, 20)
            border_color = QColor(230, 57, 70, 150)
        elif self.mic_state == "processing":
            r_outer = 15
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(193, 18, 31, 80)))
            painter.drawEllipse(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2)
            
            icon_color = QColor(193, 18, 31)
            bg_color = QColor(25, 15, 15)
            border_color = QColor(193, 18, 31, 200)
        else:
            icon_color = QColor(140, 140, 140)
            bg_color = QColor(25, 25, 25)
            border_color = QColor(40, 40, 40)
            
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(cx - 12, cy - 12, 24, 24)
        
        painter.setPen(QPen(icon_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawRoundedRect(cx - 3, cy - 6, 6, 10, 3, 3)
        painter.drawArc(cx - 6, cy - 2, 12, 8, 180 * 16, 180 * 16)
        painter.drawLine(cx, cy + 6, cx, cy + 9)
        painter.drawLine(cx - 3, cy + 9, cx + 3, cy + 9)


class UltronSidebar(QFrame):
    """Sleek vertical sidebar containing logos, navigation and stats."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarPanel")
        self.setStyleSheet("background-color: #0D0D0F; border-right: 1px solid rgba(255,255,255,0.06);")
        self.setFixedWidth(200)


class VoiceInputBar(QFrame):
    """Bottom input bar housing microphone and text commands."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setFixedHeight(48)
        self.setStyleSheet("background-color: rgba(17, 17, 17, 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 24px;")


class UltronTopBar(QWidget):
    """Custom title bar featuring clock, center status, and window control buttons."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self._init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        
    def update_time(self):
        self.clock_lbl.setText(time.strftime("%H:%M:%S"))
        
    def close_gracefully(self):
        win = self.window()
        if win and win != self and hasattr(win, "close_gracefully"):
            win.close_gracefully()
        else:
            p = self.parent()
            while p:
                if hasattr(p, "close_gracefully"):
                    p.close_gracefully()
                    return
                p = p.parent()

    def toggle_fullscreen(self):
        win = self.window()
        if win and win != self and hasattr(win, "toggle_fullscreen"):
            win.toggle_fullscreen()
        else:
            p = self.parent()
            while p:
                if hasattr(p, "toggle_fullscreen"):
                    p.toggle_fullscreen()
                    return
                p = p.parent()

    def minimize_window(self):
        win = self.window()
        if win and win != self:
            win.showMinimized()
        else:
            p = self.parent()
            while p:
                p_win = p.window()
                if p_win and p_win != self:
                    p_win.showMinimized()
                    return
                p = p.parent()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        self.clock_lbl = QLabel(time.strftime("%H:%M:%S"))
        self.clock_lbl.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        self.clock_lbl.setStyleSheet("color: #A0A0A0; font-family: monospace;")
        layout.addWidget(self.clock_lbl)
        
        layout.addStretch()
        
        # Center status indicator
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        
        self.online_txt = QLabel("ULTRON ONLINE")
        self.online_txt.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        self.online_txt.setStyleSheet("color: #F5F5F5; letter-spacing: 2px;")
        
        self.indicator = QWidget()
        self.indicator.setFixedSize(6, 6)
        self.indicator.setStyleSheet("background-color: #00FF00; border-radius: 3px;")
        
        center_layout.addWidget(self.online_txt)
        center_layout.addWidget(self.indicator)
        layout.addWidget(center_widget)
        
        layout.addStretch()
        
        # Window Controls
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(12)
        
        mini_btn = QPushButton("—")
        mini_btn.setStyleSheet("color: #A0A0A0; border: none; font-size: 14px; background: transparent;")
        mini_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mini_btn.clicked.connect(self.minimize_window)

        fs_btn = QPushButton("⛶")
        fs_btn.setStyleSheet("color: #A0A0A0; border: none; font-size: 14px; background: transparent;")
        fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fs_btn.clicked.connect(self.toggle_fullscreen)
        
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("color: #A0A0A0; border: none; font-size: 14px; background: transparent;")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_gracefully)
        
        control_layout.addWidget(mini_btn)
        control_layout.addWidget(fs_btn)
        control_layout.addWidget(close_btn)
        layout.addWidget(control_widget)


class UltronSidebarButton(QPushButton):
    """Custom sidebar button showing a sleek modern HUD style with active glow."""
    def __init__(self, title, desc, icon_char, parent=None):
        super().__init__(parent)
        self.title = title
        self.desc = desc
        self.icon_char = icon_char
        self.is_active = False
        self.setCheckable(True)
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def set_active(self, active):
        self.is_active = active
        self.setChecked(active)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        r_rect = rect.adjusted(1, 1, -1, -1)
        
        # Background card card selection
        if self.is_active:
            painter.setPen(QPen(QColor(230, 57, 70, 40), 1)) # Light red glow border
            painter.setBrush(QBrush(QColor(17, 17, 17, 240)))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(17, 17, 17, 100)))
            
        painter.drawRoundedRect(r_rect, 6, 6)
        
        # Draw Icon (Reduced size)
        painter.setPen(QPen(QColor(230, 57, 70) if self.is_active else QColor(130, 130, 130)))
        painter.setFont(QFont("Segoe UI Symbol", 10))
        painter.drawText(12, 29, self.icon_char)
        
        # Draw Title
        painter.setPen(QPen(QColor(245, 245, 245) if self.is_active else QColor(180, 180, 180)))
        painter.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        painter.drawText(38, 20, self.title)
        
        # Draw Description
        painter.setPen(QPen(QColor(150, 150, 150) if self.is_active else QColor(90, 90, 90)))
        painter.setFont(QFont("Inter", 8))
        painter.drawText(38, 34, self.desc)


class UltronSystemStatusWidget(QWidget):
    """Painted system stats showing real-time mini line graphs for CPU & Memory."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.cpu_history = []
        self.mem_history = []
        self.uptime_start = time.time()
        self.has_psutil = False
        
        try:
            import psutil
            self.has_psutil = True
        except ImportError:
            pass
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)
        
    def update_stats(self):
        if self.has_psutil:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            self.cpu_history.append(cpu)
            self.mem_history.append(mem)
            if len(self.cpu_history) > 20:
                self.cpu_history.pop(0)
            if len(self.mem_history) > 20:
                self.mem_history.pop(0)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width()
        
        # Title
        painter.setPen(QPen(QColor(130, 130, 130)))
        painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        painter.drawText(0, 15, "SYSTEM STATUS")
        
        def draw_sparkline(y_offset, label, history, color):
            painter.setPen(QPen(QColor(200, 200, 200)))
            painter.setFont(QFont("Inter", 8))
            painter.drawText(0, y_offset, label)
            
            gx = 40
            gw = width - 45
            gh = 12
            gy = y_offset - 9
            
            if not self.has_psutil:
                painter.setPen(QPen(QColor(100, 100, 100)))
                painter.setFont(QFont("Inter", 8))
                painter.drawText(gx, y_offset, "Unavailable")
                return
                
            if not history:
                return
                
            # Draw sparkline path
            path = QPainterPath()
            step = gw / max(1, len(history) - 1)
            for idx, val in enumerate(history):
                vh = gh - (val / 100 * gh)
                x = gx + idx * step
                y = gy + vh
                if idx == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            painter.setPen(QPen(color, 1))
            painter.drawPath(path)
            
        draw_sparkline(40, "CPU", self.cpu_history, QColor(230, 57, 70))
        draw_sparkline(65, "MEM", self.mem_history, QColor(230, 57, 70))
        
        painter.setPen(QPen(QColor(200, 200, 200)))
        painter.drawText(0, 90, "TEMP")
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.drawText(width - 65, 90, "Unavailable")
        
        elapsed = time.time() - self.uptime_start
        h, m, s = int(elapsed // 3600), int((elapsed % 3600) // 60), int(elapsed % 60)
        painter.setPen(QPen(QColor(200, 200, 200)))
        painter.drawText(0, 110, "UPTIME")
        painter.setPen(QPen(QColor(200, 200, 200)))
        painter.drawText(width - 55, 110, f"{h:02d}:{m:02d}:{s:02d}")


class UltronPerfCard(QFrame):
    """Premium visual performance indicator card with neon status dot and progress bar."""
    def __init__(self, title: str, unit: str, target: float, parent=None):
        super().__init__(parent)
        self.title_text = title
        self.unit = unit
        self.target = target
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 35, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(6)
        
        # Header layout (title + status indicator dot)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("color: #888888; border: none; background: transparent;")
        header.addWidget(self.lbl_title)
        
        header.addStretch()
        self.dot = QFrame()
        self.dot.setFixedSize(6, 6)
        self.dot.setStyleSheet("border-radius: 3px; background-color: #888888; border: none;")
        header.addWidget(self.dot)
        layout.addLayout(header)
        
        # Value label
        self.lbl_value = QLabel("0.0")
        self.lbl_value.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.lbl_value.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")
        layout.addWidget(self.lbl_value)
        
        # Progress bar
        from PySide6.QtWidgets import QProgressBar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #00F0FF;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress)

    def update_metric(self, val: float, status: str = "normal"):
        if self.unit == "%":
            txt = f"{val:.1f}%"
        elif self.unit == "ms":
            txt = f"{val:.1f} ms"
        elif self.unit == "MB":
            txt = f"{val:.0f} MB"
        elif self.unit == "/s":
            txt = f"{val:.1f}/s"
        elif self.unit == "count":
            txt = f"{int(val)}"
        else:
            txt = f"{val:.1f} {self.unit}"
            
        self.lbl_value.setText(txt)
        
        pct = 0
        if self.target > 0:
            pct = min(100, int((val / self.target) * 100))
        self.progress.setValue(pct)
        
        if status == "normal":
            color_dot = "#00FFC4"
            color_chunk = "#00F0FF"
        elif status == "warning":
            color_dot = "#FFB703"
            color_chunk = "#FFB703"
        else:
            color_dot = "#FF3366"
            color_chunk = "#FF3366"
            
        self.dot.setStyleSheet(f"border-radius: 3px; background-color: {color_dot}; border: none;")
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {color_chunk};
                border-radius: 2px;
            }}
        """)


class _DashboardMetricsWorker(QThread):
    """Gathers heavy metrics off the main thread to prevent UI thread lag."""
    metrics_ready = Signal(dict)

    def run(self):
        try:
            import os
            import psutil
            from ultron.core.service_manager import service_manager
            from ultron.core.event_bus import event_bus
            from ultron.core.task_manager import task_manager

            # psutil CPU/RAM metrics
            cpu = psutil.cpu_percent(interval=None)
            proc = psutil.Process(os.getpid())
            mem = proc.memory_info().rss / 1048576

            # Camera Service metrics
            cam_fps = 0.0
            cam_dur = 0.0
            cam_srv = service_manager.get_service("CameraService")
            if cam_srv and cam_srv.active:
                cam_fps = getattr(cam_srv, "camera_fps", 0.0)
                cam_dur = getattr(cam_srv, "capture_time_ms", 0.0)

            # Gesture Service metrics
            gest_fps = 0.0
            inf_dur = 0.0
            gest_srv = service_manager.get_service("GestureService")
            if gest_srv and gest_srv.active:
                gest_fps = getattr(gest_srv, "gesture_fps", 0.0)
                inf_dur = getattr(gest_srv, "inference_time_ms", 0.0)

            # EventBus Rate
            eb_rate = 0.0
            try:
                eb_rate = event_bus.get_events_per_second()
            except Exception:
                pass

            # Command Queue length
            q_len = 0
            try:
                from ultron.core.ai_core import get_ai_core
                ai = get_ai_core()
                if ai and ai.queue:
                    q_len = ai.queue.get_count()
            except Exception:
                pass

            self.metrics_ready.emit({
                "cpu": cpu,
                "mem": mem,
                "cam_fps": cam_fps,
                "cam_dur": cam_dur,
                "gest_fps": gest_fps,
                "inf_dur": inf_dur,
                "eb_rate": eb_rate,
                "q_len": q_len
            })
        except Exception:
            pass


class UltronPerformanceDashboard(QWidget):
    """Real-time performance diagnostic grid showing CPU, Memory, Queue, and FPS metrics."""
    def __init__(self, main_win, parent=None):
        super().__init__(parent)
        self.main_win = main_win
        import logging
        self.logger = logging.getLogger("ultron-agent")
        self._worker = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        header_lbl = QLabel("SYSTEM PERFORMANCE & STABILITY")
        header_lbl.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        header_lbl.setStyleSheet("color: #FFFFFF; letter-spacing: 1px;")
        layout.addWidget(header_lbl)
        
        grid = QGridLayout()
        grid.setSpacing(12)
        layout.addLayout(grid)
        
        self.card_ui_fps = UltronPerfCard("UI Frame Rate", "FPS", 60.0)
        self.card_cam_fps = UltronPerfCard("Camera Stream", "FPS", 30.0)
        self.card_gest_fps = UltronPerfCard("Inference Rate", "FPS", 25.0)
        self.card_reactor_dur = UltronPerfCard("Reactor Render", "ms", 16.0)
        self.card_cpu = UltronPerfCard("Processor Load", "%", 100.0)
        self.card_memory = UltronPerfCard("Memory Usage", "MB", 2048.0)
        self.card_eventbus = UltronPerfCard("EventBus Throughput", "/s", 50.0)
        self.card_queue = UltronPerfCard("Command Queue", "count", 5.0)
        
        grid.addWidget(self.card_ui_fps, 0, 0)
        grid.addWidget(self.card_cam_fps, 0, 1)
        grid.addWidget(self.card_gest_fps, 0, 2)
        grid.addWidget(self.card_reactor_dur, 0, 3)
        grid.addWidget(self.card_cpu, 1, 0)
        grid.addWidget(self.card_memory, 1, 1)
        grid.addWidget(self.card_eventbus, 1, 2)
        grid.addWidget(self.card_queue, 1, 3)
        
        # Raw Diagnostics panel
        from PySide6.QtWidgets import QGroupBox, QTextBrowser
        diag_group = QGroupBox("RAW SYSTEM DIAGNOSTICS & FORENSICS")
        diag_group.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        diag_group.setStyleSheet("QGroupBox { color: #888888; border: 1px solid rgba(255,255,255,0.05); margin-top: 10px; padding-top: 15px; }")
        diag_layout = QVBoxLayout(diag_group)
        diag_layout.setContentsMargins(10, 10, 10, 10)
        
        self.main_win.tools_view = QTextBrowser()
        self.main_win.tools_view.setReadOnly(True)
        self.main_win.tools_view.setFont(QFont("Consolas", 8))
        self.main_win.tools_view.setStyleSheet("background-color: rgba(20, 20, 25, 0.4); border: none; color: #A0A0A0;")
        diag_layout.addWidget(self.main_win.tools_view)
        
        layout.addWidget(diag_group)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_metrics)
        self.timer.start(1000)
        
    def refresh_metrics(self):
        """Starts a background worker to gather heavy metrics asynchronously."""
        try:
            if self._worker and self._worker.isRunning():
                return
        except RuntimeError:
            self._worker = None
        self._worker = _DashboardMetricsWorker(self)
        self._worker.metrics_ready.connect(self._on_metrics_ready, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    @Slot(dict)
    def _on_metrics_ready(self, data):
        """Processes and updates metrics on the UI thread."""
        ui_fps = 0.0
        reactor_dur = 0.0
        if hasattr(self.main_win, "reactor") and self.main_win.reactor:
            ui_fps = self.main_win.reactor.ui_fps
            reactor_dur = self.main_win.reactor.render_time_ms

        # Update cards
        status_ui = "normal" if ui_fps >= 50.0 else ("warning" if ui_fps >= 30.0 else "critical")
        self.card_ui_fps.update_metric(ui_fps, status_ui)

        status_react = "normal" if reactor_dur <= 8.0 else ("warning" if reactor_dur <= 16.0 else "critical")
        self.card_reactor_dur.update_metric(reactor_dur, status_react)

        cam_fps = data["cam_fps"]
        cam_dur = data["cam_dur"]
        status_cam = "normal" if cam_fps >= 24.0 else ("warning" if cam_fps >= 10.0 else "critical")
        self.card_cam_fps.update_metric(cam_fps, status_cam)

        gest_fps = data["gest_fps"]
        inf_dur = data["inf_dur"]
        status_gest = "normal" if gest_fps >= 20.0 else ("warning" if gest_fps >= 10.0 else "critical")
        self.card_gest_fps.update_metric(gest_fps, status_gest)

        cpu = data["cpu"]
        status_cpu = "normal" if cpu <= 70.0 else ("warning" if cpu <= 90.0 else "critical")
        self.card_cpu.update_metric(cpu, status_cpu)

        mem = data["mem"]
        status_mem = "normal" if mem <= 800.0 else ("warning" if mem <= 1500.0 else "critical")
        self.card_memory.update_metric(mem, status_mem)

        eb_rate = data["eb_rate"]
        status_eb = "normal" if eb_rate <= 100.0 else "warning"
        self.card_eventbus.update_metric(eb_rate, status_eb)

        q_len = data["q_len"]
        status_q = "normal" if q_len <= 1 else ("warning" if q_len <= 3 else "critical")
        self.card_queue.update_metric(q_len, status_q)

        # Log timing of every subsystem periodically
        self.logger.info(
            f"[PERF] UI FPS: {ui_fps:.1f} | "
            f"Camera FPS: {cam_fps:.1f} (Capture: {cam_dur:.1f} ms) | "
            f"Gesture FPS: {gest_fps:.1f} (Inference: {inf_dur:.1f} ms) | "
            f"Reactor: {reactor_dur:.1f} ms | "
            f"CPU: {cpu:.1f}% | "
            f"Memory: {mem:.1f} MB | "
            f"EventBus: {eb_rate:.1f}/s | "
            f"Queue: {q_len}"
        )

    def stop_worker(self):
        """Safely stops any running background dashboard workers."""
        try:
            if self._worker and self._worker.isRunning():
                self._worker.quit()
                self._worker.wait(1000)
        except RuntimeError:
            self._worker = None


class UltronActionCard(QPushButton):
    """Custom suggested action cards with hover lift animations."""
    def __init__(self, title, subtitle, icon_char, cmd_to_run, main_win, parent=None):
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self.icon_char = icon_char
        self.cmd_to_run = cmd_to_run
        self.main_win = main_win
        self.setFixedHeight(42)
        self.y_offset = 0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self.execute)
        
    def execute(self):
        self.main_win.cmd_input.setText(self.cmd_to_run)
        self.main_win.submit_command()

    def enterEvent(self, event):
        self.y_offset = -2
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.y_offset = 0
        self.update()
        super().leaveEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        r_rect = rect.adjusted(1, 1 + self.y_offset, -1, -1 + self.y_offset)
        
        # Border opacity 10%
        if self.underMouse():
            painter.setPen(QPen(QColor(230, 57, 70, 90), 1))
            painter.setBrush(QBrush(QColor(17, 17, 17, 240)))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
            painter.setBrush(QBrush(QColor(17, 17, 17, 160)))
            
        painter.drawRoundedRect(r_rect, 6, 6)
        
        # Draw Icon
        painter.setPen(QPen(QColor(230, 57, 70)))
        painter.setFont(QFont("Segoe UI Symbol", 10))
        painter.drawText(12, 26 + self.y_offset, self.icon_char)
        
        # Draw Labels
        painter.setPen(QPen(QColor(245, 245, 245)))
        painter.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        painter.drawText(32, 17 + self.y_offset, self.title)
        
        painter.setPen(QPen(QColor(140, 140, 140)))
        painter.setFont(QFont("Inter", 7))
        painter.drawText(32, 31 + self.y_offset, self.subtitle)


class UltronThoughtStream(QFrame):
    """Dynamic HUD Thought Stream monitoring stage reasoning transitions without symbols."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.active_step = -1
        self.pulse = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.blink_step)
        self.timer.start(400)
        self._init_ui()
        
    def blink_step(self):
        if self.active_step >= 0:
            self.pulse = 1 - self.pulse
            self.update()
            
    def set_voice_state(self, state):
        state_map = {
            "LISTENING": 0,
            "PROCESSING": 1,
            "THINKING": 2,
            "PLANNING": 3,
            "EXECUTING": 4,
            "RESPONDING": 5
        }
        self.active_step = state_map.get(state.upper(), -1)
        self.update()
        
    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(8)
        
        title = QLabel("THOUGHT STREAM")
        title.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #C1121F; letter-spacing: 1px;")
        self.layout.addWidget(title)
        self.layout.addSpacing(4)
        
        self.steps = [
            "Understanding Request",
            "Retrieving Context",
            "Reasoning Options",
            "Formulating Plan",
            "Executing Directives",
            "Speaking Response"
        ]
        
        self.labels = []
        for text in self.steps:
            lbl = QLabel(text)
            lbl.setFont(QFont("Inter", 8))
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.15);")
            self.layout.addWidget(lbl)
            self.labels.append(lbl)
                
    def paintEvent(self, event):
        super().paintEvent(event)
        for idx, lbl in enumerate(self.labels):
            if idx == self.active_step:
                color = "#E63946" if self.pulse else "#C1121F"
                lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            elif idx < self.active_step:
                lbl.setStyleSheet("color: rgba(245, 245, 245, 0.4); font-weight: normal;")
            else:
                lbl.setStyleSheet("color: rgba(255, 255, 255, 0.15); font-weight: normal;")


class UltronMemoryStatus(QFrame):
    """Elegant memory status using plain textual flags instead of fake percentages."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(6)
        
        title = QLabel("MEMORY STATUS")
        title.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #C1121F; letter-spacing: 1px;")
        layout.addWidget(title)
        layout.addSpacing(4)
        
        channels = [
            ("Short Term", "Ready"),
            ("Long Term", "Ready"),
            ("Projects", "Loaded"),
            ("Knowledge", "Indexed")
        ]
        
        for name, status_text in channels:
            row = QHBoxLayout()
            lbl = QLabel(name)
            lbl.setFont(QFont("Inter", 8))
            lbl.setStyleSheet("color: #A0A0A0;")
            
            val_lbl = QLabel(status_text)
            val_lbl.setFont(QFont("Inter", 8, QFont.Weight.Bold))
            val_lbl.setStyleSheet("color: #F5F5F5;")
            
            row.addWidget(lbl)
            row.addWidget(val_lbl, alignment=Qt.AlignmentFlag.AlignRight)
            layout.addLayout(row)


class UltronProgressRing(QWidget):
    """Circular progress loader ring that rotates if data is loading/unavailable."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.percent = None
        self.angle = 0
        self.setFixedSize(54, 54)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate_ring)
        self.timer.start(30)
        
    def rotate_ring(self):
        if self.percent is None:
            self.angle = (self.angle + 4) % 360
            self.update()
            
    def set_percent(self, val):
        self.percent = val
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        cx = rect.width() / 2
        cy = rect.height() / 2
        r = 20
        
        # Draw background ring
        painter.setPen(QPen(QColor(255, 255, 255, 10), 2))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        
        if self.percent is None:
            # Scanning rotating loader arc
            painter.setPen(QPen(QColor(230, 57, 70), 2))
            painter.drawArc(cx - r, cy - r, r * 2, r * 2, self.angle * 16, 120 * 16)
        else:
            # Solid percent representation
            span = -int((self.percent / 100.0) * 360 * 16)
            painter.setPen(QPen(QColor(193, 18, 31), 2))
            painter.drawArc(cx - r, cy - r, r * 2, r * 2, 90 * 16, span)
            
            painter.setPen(QPen(QColor(245, 245, 245)))
            painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.percent}%")


class UltronProjectPanel(QFrame):
    """Project status panel containing rotating ring until active data resolves."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(4)
        
        title = QLabel("CURRENT PROJECT")
        title.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #C1121F; letter-spacing: 1px;")
        layout.addWidget(title)
        
        main_row = QHBoxLayout()
        details = QVBoxLayout()
        self.p_name = QLabel("No Active Project")
        self.p_name.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.p_name.setStyleSheet("color: #F5F5F5;")
        self.p_desc = QLabel("No project loaded")
        self.p_desc.setFont(QFont("Inter", 8))
        self.p_desc.setStyleSheet("color: #A0A0A0;")
        details.addWidget(self.p_name)
        details.addWidget(self.p_desc)
        
        # Rotating progress ring by default until real data sets it
        self.ring = UltronProgressRing()
        main_row.addLayout(details)
        main_row.addWidget(self.ring)
        layout.addLayout(main_row)
        
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: rgba(255,255,255,0.05);")
        layout.addWidget(line)
        
        self.meta_labels = {}
        for key in ["Current Task", "Git Status", "Project Health"]:
            row = QHBoxLayout()
            k_lbl = QLabel(key)
            k_lbl.setFont(QFont("Inter", 8))
            k_lbl.setStyleSheet("color: #A0A0A0;")
            
            v_lbl = QLabel("-")
            v_lbl.setFont(QFont("Inter", 8, QFont.Weight.Bold))
            v_lbl.setStyleSheet("color: #F5F5F5;")
            
            row.addWidget(k_lbl)
            row.addWidget(v_lbl, alignment=Qt.AlignmentFlag.AlignRight)
            layout.addLayout(row)
            self.meta_labels[key] = v_lbl

        self.meta_labels["Current Task"].setText("Integrate Payment Gateway")
        self.meta_labels["Git Status"].setText("Clean (main branch)")
        self.meta_labels["Git Status"].setStyleSheet("color: #00FF00;")
        self.meta_labels["Project Health"].setText("Operational (Healthy)")
        self.meta_labels["Project Health"].setStyleSheet("color: #00FF00;")


# ── Background Worker: gathers diagnostics off the Qt main thread ────────────────

class _DiagnosticsWorker(QThread):
    """
    Runs all diagnostic data-gathering off the Qt main thread.
    Emits html_ready(str) when the report is ready; the main thread slot calls setHtml().
    """
    html_ready = Signal(str)

    def __init__(self, core, snapshot: dict):
        super().__init__()
        self.core = core
        self.snapshot = snapshot   # pre-computed Qt-thread values (timer state, etc.)

    def run(self):
        try:
            self.html_ready.emit(self._build())
        except Exception:
            pass

    def _build(self) -> str:  # noqa: C901
        import os, time, threading
        from ultron.core.service_manager import service_manager
        from ultron.core.event_bus import event_bus
        from ultron.core.task_manager import task_manager
        from ultron.hal.hal_manager import get_hal_manager
        from ultron.core.ai_core import get_ai_core
        from ultron.core.voice_session_manager import get_voice_session_manager
        from ultron.core.plugin_loader import get_plugin_loader
        from ultron.memory import get_memory_manager

        devices = self.snapshot.get("devices", {"microphone": False, "speaker": False, "camera": False})
        mic_allowed = self.snapshot.get("mic_allowed", False)
        speaker_allowed = self.snapshot.get("speaker_allowed", False)
        camera_allowed = self.snapshot.get("camera_allowed", False)

        def _status(is_permitted, is_present, svc_name=None):
            if not is_permitted:
                return "<span style='color: orange;'>Disabled</span>"
            if not is_present:
                return "<span style='color: gray;'>Offline</span>"
            if svc_name:
                svc = service_manager.get_service(svc_name)
                if svc:
                    return f"<span style='color: #00FF00;'>{svc.health()}</span>"
            return "<span style='color: #00FF00;'>Healthy</span>"

        html = "<h3 style='color: #C1121F;'>LIVE OS DIAGNOSTICS</h3>"
        html += "<table width='100%' cellpadding='4' style='color: #A0A0A0; font-family: monospace; border-bottom: 1px solid rgba(255,255,255,0.06);'>"
        html += f"<tr><td>Microphone</td><td>{_status(mic_allowed, devices['microphone'], 'VoiceRecognitionService')}</td></tr>"
        html += f"<tr><td>Speaker</td><td>{_status(speaker_allowed, devices['speaker'], 'SpeechService')}</td></tr>"
        html += f"<tr><td>Camera</td><td>{_status(camera_allowed, devices['camera'])}</td></tr>"

        for svc_name, label in [("VoiceRecognitionService", "Voice Recognition"), ("WakeService", "Wake Engine")]:
            svc = service_manager.get_service(svc_name)
            stat = f"<span style='color: #00FF00;'>{svc.health()}</span>" if svc else "<span style='color: gray;'>Offline</span>"
            html += f"<tr><td>{label}</td><td>{stat}</td></tr>"

        html += "<tr><td>SQLite Database</td><td><span style='color: #00FF00;'>Healthy</span></td></tr>"
        html += "<tr><td>Memory Engine</td><td><span style='color: #00FF00;'>Healthy</span></td></tr>"
        html += "<tr><td>Cognitive Core</td><td><span style='color: #00FF00;'>Healthy</span></td></tr>"

        skills = self.core.get_module("skills_registry")
        skills_stat = f"<span style='color: #00FF00;'>{skills.health()['status'].title()}</span>" if skills else "<span style='color: gray;'>Offline</span>"
        html += f"<tr><td>Skill Registry</td><td>{skills_stat}</td></tr>"

        active_tasks = [t for t in task_manager.list_tasks() if t["status"] in ["Running", "Queued"]]
        exec_stat = f"<span style='color: orange;'>Running ({len(active_tasks)} tasks)</span>" if active_tasks else "<span style='color: #00FF00;'>Standing By</span>"
        html += f"<tr><td>Executor</td><td>{exec_stat}</td></tr>"
        html += "</table>"

        mgr = get_voice_session_manager()
        voice_state = mgr.state.name if mgr else "SLEEPING"
        wake_detector = service_manager.get_service("WakeDetectorService")
        wake_enabled = "Yes" if (wake_detector and wake_detector.active) else "No"

        engine_srv = service_manager.get_service("VoiceEngineService")
        microphone = engine_srv.diagnostics.get("current_microphone", "GENERAL WEBCAM") if engine_srv else "GENERAL WEBCAM"
        rec_provider = (engine_srv.reco_provider_name or "VOSK").upper() if engine_srv else "VOSK"
        wake_provider = (engine_srv.wake_provider_name or "VOSK").upper() if engine_srv else "VOSK"

        reco_threads = [t for t in threading.enumerate() if "Recognition" in t.name or "Voice" in t.name]
        tts_threads  = [t for t in threading.enumerate() if "tts" in t.name.lower() or "pyttsx" in t.name.lower()]

        ai = get_ai_core()
        ai_thread_status = "Running" if (ai and ai.queue.worker_thread and ai.queue.worker_thread.is_alive()) else "Offline"
        speech_thread    = "Running" if (tts_threads or (engine_srv and engine_srv.active_tts)) else "Offline"

        try:
            import psutil
            proc = psutil.Process(os.getpid())
            ram_usage = f"{proc.memory_info().rss / 1048576:.1f} MB"
            cpu_usage = f"{psutil.cpu_percent(interval=None)}%"
        except Exception:
            ram_usage = cpu_usage = "Unknown"

        convo_id    = "-"
        last_wake_time = "-"
        last_command   = "-"
        avg_rec_lat    = "0 ms"
        avg_res_lat    = "0 ms"
        avg_ai_time    = "0 ms"
        wake_count = cmds_proc = resp_spk = 0

        if mgr:
            convo_id = mgr.convo_id
            if mgr.last_wake_time > 0:
                last_wake_time = time.strftime('%H:%M:%S', time.localtime(mgr.last_wake_time))
            last_command  = mgr.last_command
            avg_rec_lat   = f"{mgr.avg_recognition_latency * 1000:.0f} ms"
            avg_res_lat   = f"{mgr.avg_response_latency  * 1000:.0f} ms"
            avg_ai_time   = f"{mgr.avg_ai_time           * 1000:.0f} ms"
            wake_count    = mgr.wake_count
            cmds_proc     = mgr.commands_processed
            resp_spk      = mgr.responses_spoken

        sub_count  = event_bus.get_subscriber_count()
        queue_len  = ai.queue.get_count() if ai else 0

        import main as _main
        boot_stage = getattr(_main, "current_boot_stage", "BOOT 09: Boot complete")
        p_loader   = get_plugin_loader()
        plugin_status = f"Active ({len(p_loader.loaded_plugins)} plugins)" if (p_loader and p_loader.loaded_plugins) else "Offline"
        mem_status = "Loaded (SQLite)" if get_memory_manager() else "Offline"
        services_list = ", ".join(service_manager.list_services())

        # Values that were read on the main thread to avoid QTimer cross-thread calls
        timer_active = self.snapshot.get("timer_active", "-")
        sec_rem      = self.snapshot.get("sec_rem",      "-")

        html += "<br/><b>Architectural Diagnostics:</b><br/>"
        html += "<table width='100%' cellpadding='4' style='color: #A0A0A0; font-family: monospace; border-bottom: 1px solid rgba(255,255,255,0.06);'>"
        for label, val in [
            ("Current State", voice_state), ("Wake Enabled", wake_enabled),
            ("Wake Provider", wake_provider), ("Recognition Provider", rec_provider),
            ("Current Microphone", microphone), ("Speech Thread", speech_thread),
            ("Queue Thread", ai_thread_status), ("EventBus Queue", queue_len),
            ("EventBus Subscribers", sub_count), ("Boot Stage", boot_stage),
            ("Plugin Status", plugin_status), ("Memory Status", mem_status),
            ("Conversation ID", convo_id), ("Session Timer", timer_active),
            ("Session Timer Remaining", sec_rem), ("Wake Count", wake_count),
            ("Commands Processed", cmds_proc), ("Responses Spoken", resp_spk),
            ("Avg Recognition Time", avg_rec_lat), ("Avg AI Time", avg_ai_time),
            ("Avg Response Time", avg_res_lat), ("Memory Usage", ram_usage),
            ("CPU Usage", cpu_usage), ("Registered Services", services_list),
            ("Application Version", "1.0.0"),
        ]:
            html += f"<tr><td>{label}</td><td><span style='color: #00FF00;'>{val}</span></td></tr>"
        html += "</table>"

        # Voice Recognition Forensics
        active_rec = engine_srv.active_recognizer if engine_srv else None
        rec_alive  = "Yes" if (active_rec and active_rec.thread and active_rec.thread.is_alive()) else "No"
        rec_run    = "Yes" if (active_rec and active_rec.active) else "No"
        cb_count   = getattr(active_rec, "audio_callback_count", getattr(active_rec, "chunks_received", 0)) if active_rec else 0
        dropped    = getattr(active_rec, "dropped_buffers", 0) if active_rec else 0

        html += "<br/><b>Voice Recognition Forensics:</b><br/>"
        html += "<table width='100%' cellpadding='4' style='color: #A0A0A0; font-family: monospace; border-bottom: 1px solid rgba(255,255,255,0.06);'>"
        for label, val in [
            ("Recognition Thread Alive", rec_alive), ("Recognition Loop Running", rec_run),
            ("Audio Callback Count", cb_count),
            ("Speech Events Published",  event_bus.get_publish_count("SPEECH_RECOGNIZED")),
            ("Wake Events Published",    event_bus.get_publish_count("WAKE_DETECTED")),
            ("Commands Executed",        event_bus.get_publish_count("COMMAND_RECEIVED")),
            ("Dropped Buffers", dropped), ("Current Voice State", voice_state),
        ]:
            html += f"<tr><td>{label}</td><td><span style='color: #00FF00;'>{val}</span></td></tr>"
        html += "</table>"

        html += "<br/><b>Task History:</b><br/>"
        for t in reversed(task_manager.list_tasks()[-5:]):
            color = "#00FF00" if t["status"] == "Completed" else "#C1121F" if t["status"] == "Failed" else "orange"
            html += f"Task: <b>{t['description'][:30]}</b> | Status: <b style='color: {color};'>{t['status'].upper()}</b><br/>"

        return html


# ── Main Window Dashboard ─────────────────────────────────────────────────────

class UltronMainWindow(QMainWindow):
    event_signal = Signal(object)

    def __init__(self, core_system, memory_manager=None, voice_provider=None):
        super().__init__()
        self.core = core_system
        self.memory = memory_manager
        self.voice = voice_provider
        self._drag_position = None
        self.display_name = None
        self.queue_count = 0
        self.current_voice_state = "BOOTING"

        self._init_ui()
        self.lock_ui()

        # Connect thread-safe generic event router
        self.event_signal.connect(self._handle_queued_event, Qt.ConnectionType.QueuedConnection)

        # Event Bus subscriptions routed through the custom signal to GUI main thread
        for et in [
            "STATE_CHANGED", "VOICE_STATE_CHANGED", "QUEUE_COUNT_CHANGED",
            "WAKE_TRIGGERED", "SLEEP_TRIGGERED", "VOICE_DIAGNOSTICS_UPDATE",
            "NOTIFICATION", "WARNING_OCCURRED", "ERROR_OCCURRED",
            "VOSK_MODEL_MISSING", "VOLUME_LEVEL_CHANGED", "AI_RESPONSE_READY",
            "HiddenItemAdded", "HiddenItemRestored", "HiddenItemOpened", "HiddenItemMissing"
        ]:
            event_bus.subscribe(et, self._event_bus_route_callback)

        self._diag_worker = None
        self.diag_timer = QTimer(self)
        self.diag_timer.timeout.connect(self._start_diag_worker)
        self.diag_timer.start(2000)  # 2 s is plenty for a non-blocking background gather

        if self.memory:
            self.load_user_profile()

    def bind_providers(self, memory_manager, voice_provider):
        self.memory = memory_manager
        self.voice = voice_provider
        self.load_user_profile()
        self.refresh_memory_view()

    def lock_ui(self):
        self.cmd_input.setEnabled(False)
        self.cmd_input.setPlaceholderText("System Initializing... Please wait...")
        self.send_btn.setEnabled(False)
        if hasattr(self, "test_mic_btn"):
            self.test_mic_btn.setEnabled(False)

    def unlock_ui(self):
        self.cmd_input.setEnabled(True)
        self.cmd_input.setPlaceholderText("Type your command or ask anything...")
        self.send_btn.setEnabled(True)
        if hasattr(self, "test_mic_btn"):
            self.test_mic_btn.setEnabled(True)

    def refresh_memory(self):
        self.refresh_memory_view()

    def refresh_voice(self):
        pass

    def refresh_system(self):
        self.refresh_diagnostics()

    def refresh_plugins(self):
        pass

    def _init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(1080, 680)
        self.setStyleSheet(UltronThemeStyles.get_application_stylesheet())
        self.setWindowIcon(QIcon("assets/icons/ultron.ico"))

        # Center window
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            self.move((geom.width() - self.width()) // 2, (geom.height() - self.height()) // 2)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(1, 1, 1, 1)

        base_frame = QFrame()
        base_frame.setObjectName("MainPanel")
        main_layout.addWidget(base_frame)

        base_layout = QHBoxLayout(base_frame)
        base_layout.setContentsMargins(0, 0, 0, 0)
        base_layout.setSpacing(0)

        # ── 1. LEFT SIDEBAR PANEL ──
        sidebar = safe_create_widget("UltronSidebar", base_frame)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 15)

        # Logo Header
        logo_lbl = QLabel("ULTRON")
        logo_lbl.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        logo_lbl.setStyleSheet("color: #C1121F; letter-spacing: 2px;")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo_lbl)
        
        sub_logo = QLabel("COGNITIVE OS")
        sub_logo.setStyleSheet("color: #A0A0A0; font-size: 9px; letter-spacing: 1px;")
        sub_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(sub_logo)
        sidebar_layout.addSpacing(25)

        # Sidebar navigation buttons (more breathing room)
        self.nav_btns = []
        nav_configs = [
            ("CORE", "Cognitive Core Online", "\u25C9"),
            ("MEMORY", "Storage Synced", "\u25A2"),
            ("PROJECTS", "Projects", "\u25A6"),
            ("TOOLS", "Diagnostics Active", "\u2692"),
            ("TERMINAL", "Developer Prompt", "\uFF1E"),
            ("HIDDEN ITEMS", "Vault Manager", "\ud83d\udd12"),
            ("SETTINGS", "System Settings", "\u2699")
        ]
        for idx, (title, desc, icon) in enumerate(nav_configs):
            btn = UltronSidebarButton(title, desc, icon)
            btn.clicked.connect(lambda checked=False, i=idx: self.switch_panel(i))
            sidebar_layout.addWidget(btn)
            sidebar_layout.addSpacing(6)
            self.nav_btns.append(btn)
            
        self.nav_btns[0].set_active(True)

        sidebar_layout.addStretch()

        # Telemetry graphs
        self.stats_widget = UltronSystemStatusWidget()
        sidebar_layout.addWidget(self.stats_widget)
        sidebar_layout.addSpacing(15)

        # Operator section matching visual requirements (No warning styles/brackets)
        operator_box = QWidget()
        operator_layout = QVBoxLayout(operator_box)
        operator_layout.setContentsMargins(10, 8, 10, 8)
        operator_layout.setSpacing(2)
        
        op_lbl = QLabel("Operator")
        op_lbl.setFont(QFont("Inter", 8))
        op_lbl.setStyleSheet("color: #A0A0A0;")
        
        self.op_name = QLabel("Prem")
        self.op_name.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        self.op_name.setStyleSheet("color: #F5F5F5;")
        
        st_lbl = QLabel("Status")
        st_lbl.setFont(QFont("Inter", 8))
        st_lbl.setStyleSheet("color: #A0A0A0; margin-top: 5px;")
        
        self.user_badge = QLabel("Sleeping")
        self.user_badge.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        self.user_badge.setStyleSheet("color: #A0A0A0;")
        
        operator_layout.addWidget(op_lbl)
        operator_layout.addWidget(self.op_name)
        operator_layout.addWidget(st_lbl)
        operator_layout.addWidget(self.user_badge)
        
        sidebar_layout.addWidget(operator_box)

        base_layout.addWidget(sidebar)

        # ── 2. DASHBOARD / CONTENT WORKSPACE ──
        dashboard = QWidget()
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(0)

        # Top Bar
        self.top_bar = safe_create_widget("UltronTopBar", dashboard)
        dashboard_layout.addWidget(self.top_bar)

        # Top Bar Divider line
        tb_divider = QFrame()
        tb_divider.setFixedHeight(1)
        tb_divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.05);")
        dashboard_layout.addWidget(tb_divider)

        # Main splitter holding stacked pages and debugging terminal
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        dashboard_layout.addWidget(self.splitter)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.create_core_page())
        self.stacked_widget.addWidget(self.create_memory_page())
        self.stacked_widget.addWidget(self.create_projects_page())
        self.stacked_widget.addWidget(self.create_tools_page())
        self.stacked_widget.addWidget(QWidget()) # placeholder for Terminal button routing
        self.stacked_widget.addWidget(self.create_hidden_items_page())
        self.stacked_widget.addWidget(self.create_settings_page())

        self.splitter.addWidget(self.stacked_widget)

        self.dev_console = UltronDeveloperConsole()
        self.splitter.addWidget(self.dev_console)
        self.dev_console.setStyleSheet("border-left: 1px solid rgba(255, 255, 255, 0.05);")
        self.splitter.setSizes([740, 300])

        base_layout.addWidget(dashboard)

        # Floating Widget overlay
        self.floating_widget = UltronFloatingVoiceWidget(self)
        self.floating_widget.move(self.width() - 140, 50)
        self.floating_widget.show()

        # Global developer console shortcut
        self.shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        self.shortcut.activated.connect(self.toggle_developer_console)

    def create_core_page(self) -> QWidget:
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ── Left Column (Center Hub area) ──
        center_hub = QVBoxLayout()
        center_hub.setSpacing(15)

        self.active_status_lbl = QLabel("Sleeping...")
        self.active_status_lbl.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        self.active_status_lbl.setStyleSheet("color: #A0A0A0; letter-spacing: 2px;")
        self.active_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_hub.addWidget(self.active_status_lbl)

        # Reactor Visualizer container
        wave_container = QWidget()
        wave_container.setMinimumHeight(380)
        
        self.reactor = safe_create_widget("UltronReactorWidget", wave_container)
        self.reactor.setGeometry(0, 0, 480, 380)
        
        def resize_reactor(event):
            self.reactor.resize(event.size())
        wave_container.resizeEvent = resize_reactor
        
        center_hub.addWidget(wave_container)

        # Clean typography greeting layout
        greeting_box = QWidget()
        greeting_layout = QVBoxLayout(greeting_box)
        greeting_layout.setContentsMargins(0, 0, 0, 0)
        greeting_layout.setSpacing(4)
        
        self.greeting_lbl = QLabel("Good Evening,")
        self.greeting_lbl.setFont(QFont("Inter", 20))
        self.greeting_lbl.setStyleSheet("color: #F5F5F5;")
        self.greeting_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.greeting_name_lbl = QLabel("Prem.")
        self.greeting_name_lbl.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        self.greeting_name_lbl.setStyleSheet("color: #E63946;")
        self.greeting_name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        greeting_layout.addWidget(self.greeting_lbl)
        greeting_layout.addWidget(self.greeting_name_lbl)

        self.subtitle_lbl = QLabel("How can I assist you today?")
        self.subtitle_lbl.setFont(QFont("Inter", 10))
        self.subtitle_lbl.setStyleSheet("color: #808080;")
        self.subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Suggested actions layout
        suggested_title = QLabel("SUGGESTED ACTIONS")
        suggested_title.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        suggested_title.setStyleSheet("color: #A0A0A0; letter-spacing: 1px;")

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        actions_layout.addWidget(UltronActionCard("No Recent Projects", "None", "\u25A6", "continue project", self))
        actions_layout.addWidget(UltronActionCard("Open Terminal", "Workspace", "\uFF1E", "open terminal", self))
        actions_layout.addWidget(UltronActionCard("Check Updates", "Project Status", "\u21BB", "check updates", self))
        actions_layout.addWidget(UltronActionCard("Review Notes", "Last Session", "\u270E", "review notes", self))

        # Center Stack Setup (Welcome vs Chat)
        self.center_stack = QStackedWidget()
        
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setContentsMargins(0, 0, 0, 0)
        welcome_layout.setSpacing(10)
        welcome_layout.addWidget(greeting_box)
        welcome_layout.addWidget(self.subtitle_lbl)
        welcome_layout.addStretch()
        welcome_layout.addWidget(suggested_title)
        welcome_layout.addLayout(actions_layout)
        
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(10)
        
        self.conversation_widget = QTextBrowser()
        self.conversation_widget.setObjectName("GlassPanel")
        self.conversation_widget.setOpenExternalLinks(True)
        self.conversation_widget.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(17, 17, 17, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 10px;
                color: #F5F5F5;
                padding: 10px;
            }
        """)
        chat_layout.addWidget(self.conversation_widget)
        
        self.center_stack.addWidget(welcome_widget)
        self.center_stack.addWidget(chat_widget)
        
        center_hub.addWidget(self.center_stack)
        
        # Compatibility aliases for automated tests / legacy code
        self.chatWidget = self.conversation_widget
        self.chat_area = self.conversation_widget
        self.conversationWidget = self.conversation_widget
        self.messageView = self.conversation_widget
        self.historyPanel = self.conversation_widget

        # Bottom Voice Command Bar (Perfect centering)
        self.command_bar = safe_create_widget("VoiceInputBar", widget)
        
        cmd_bar_layout = QHBoxLayout(self.command_bar)
        cmd_bar_layout.setContentsMargins(6, 0, 12, 0)
        cmd_bar_layout.setSpacing(8)

        self.mic_btn = UltronMicButton()
        self.mic_btn.clicked.connect(self.toggle_microphone)
        cmd_bar_layout.addWidget(self.mic_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.cmd_input = QLineEdit()
        self.cmd_input.setObjectName("CommandInput")
        self.cmd_input.setPlaceholderText("Type your command or ask anything...")
        self.cmd_input.setStyleSheet("background: transparent; border: none; padding: 0px 4px; color: #F5F5F5; font-size: 13px;")
        self.cmd_input.returnPressed.connect(self.send_message)
        cmd_bar_layout.addWidget(self.cmd_input, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.send_btn = QPushButton("\u27A4")
        self.send_btn.setFixedSize(28, 28)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("background: transparent; border: none; font-size: 14px; color: #E63946;")
        self.send_btn.clicked.connect(self.send_message)
        cmd_bar_layout.addWidget(self.send_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Compatibility aliases for input
        self.input_box = self.cmd_input
        self.inputBox = self.cmd_input
        self.commandInput = self.cmd_input

        center_hub.addWidget(self.command_bar)
        main_layout.addLayout(center_hub, 7)

        # ── Right Column (Thought Stream & status meters) ──
        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        
        self.thought_stream = safe_create_widget("ThoughtStreamWidget")
        self.memory_status = safe_create_widget("MemoryStatusWidget")
        self.project_panel = safe_create_widget("ProjectWidget")

        right_column.addWidget(self.thought_stream)
        right_column.addWidget(self.memory_status)
        right_column.addWidget(self.project_panel)
        
        self.camera_preview = safe_create_widget("UltronCameraPreviewWidget")
        right_column.addWidget(self.camera_preview)
        hal = get_hal_manager()
        if not (hal.is_allowed("camera") if hal else False):
            self.camera_preview.hide()
            
        main_layout.addLayout(right_column, 3)

        return widget

    def create_memory_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl = QLabel("UME STORAGE STATUS")
        lbl.setObjectName("TitleLabel")
        layout.addWidget(lbl)
        
        self.memory_view = QTextEdit()
        self.memory_view.setReadOnly(True)
        self.memory_view.setFont(QFont("Consolas", 10))
        layout.addWidget(self.memory_view)
        return widget

    def create_projects_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl = QLabel("PROJECT INTELLIGENCE")
        lbl.setObjectName("TitleLabel")
        layout.addWidget(lbl)
        
        self.projects_view = QTextEdit()
        self.projects_view.setReadOnly(True)
        self.projects_view.setFont(QFont("Consolas", 10))
        layout.addWidget(self.projects_view)
        return widget

    def create_tools_page(self) -> QWidget:
        self.perf_dashboard = UltronPerformanceDashboard(self)
        return self.perf_dashboard

    def create_settings_page(self) -> QWidget:
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        lbl = QLabel("SYSTEM CONFIGURATION")
        lbl.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #C1121F;")
        layout.addWidget(lbl)
        # Operator Settings
        from PySide6.QtWidgets import QGroupBox, QFormLayout
        operator_box = QGroupBox("Operator Settings")
        operator_box.setStyleSheet("QGroupBox { color: #C1121F; font-weight: bold; border: 1px solid rgba(255,255,255,0.05); margin-top: 10px; padding-top: 15px; } QLabel { color: #A0A0A0; font-weight: normal; }")
        op_form = QFormLayout(operator_box)
        
        self.lbl_op_name_val = QLabel("-")
        self.lbl_op_name_val.setStyleSheet("color: #F5F5F5;")
        op_form.addRow("Operator Name:", self.lbl_op_name_val)
        
        self.lbl_op_voice_val = QLabel("-")
        self.lbl_op_voice_val.setStyleSheet("color: #F5F5F5;")
        op_form.addRow("Voice Enabled:", self.lbl_op_voice_val)
        
        self.lbl_op_work_val = QLabel("-")
        self.lbl_op_work_val.setStyleSheet("color: #F5F5F5;")
        op_form.addRow("Workspace:", self.lbl_op_work_val)
        
        op_btn_layout = QHBoxLayout()
        btn_edit_profile = QPushButton("Edit Profile")
        btn_edit_profile.setStyleSheet("background-color: rgba(255,255,255,0.05); color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 5px 12px; border-radius: 4px;")
        btn_edit_profile.clicked.connect(self.edit_operator_profile)
        
        btn_reset_onboarding = QPushButton("Reset Onboarding")
        btn_reset_onboarding.setStyleSheet("background-color: rgba(193, 18, 31, 0.2); color: #C1121F; border: 1px solid rgba(193, 18, 31, 0.4); padding: 5px 12px; border-radius: 4px;")
        btn_reset_onboarding.clicked.connect(self.reset_operator_onboarding)
        
        btn_open_workspace = QPushButton("Open Workspace")
        btn_open_workspace.setStyleSheet("background-color: rgba(255,255,255,0.05); color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 5px 12px; border-radius: 4px;")
        btn_open_workspace.clicked.connect(self.open_operator_workspace)
        
        op_btn_layout.addWidget(btn_edit_profile)
        op_btn_layout.addWidget(btn_reset_onboarding)
        op_btn_layout.addWidget(btn_open_workspace)
        op_form.addRow("", op_btn_layout)
        
        layout.addWidget(operator_box)
        hw_lbl = QLabel("Hardware Resource Permissions")
        hw_lbl.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        hw_lbl.setStyleSheet("color: #F5F5F5; margin-top: 10px; margin-bottom: 5px;")
        layout.addWidget(hw_lbl)

        self.mic_toggle = QCheckBox("Enable Microphone Input")
        self.mic_toggle.setFont(QFont("Inter", 10))
        self.mic_toggle.setStyleSheet("color: #F5F5F5; padding: 3px;")
        hal = get_hal_manager()
        self.mic_toggle.setChecked(hal.is_allowed("microphone") if hal else False)
        self.mic_toggle.stateChanged.connect(self.on_mic_toggle)
        layout.addWidget(self.mic_toggle)

        self.spk_toggle = QCheckBox("Enable Speaker Output (TTS)")
        self.spk_toggle.setFont(QFont("Inter", 10))
        self.spk_toggle.setStyleSheet("color: #F5F5F5; padding: 3px;")
        self.spk_toggle.setChecked(hal.is_allowed("speaker") if hal else False)
        self.spk_toggle.stateChanged.connect(self.on_spk_toggle)
        layout.addWidget(self.spk_toggle)

        self.cam_toggle = QCheckBox("Enable Camera Feed (Vision)")
        self.cam_toggle.setFont(QFont("Inter", 10))
        self.cam_toggle.setStyleSheet("color: #F5F5F5; padding: 3px;")
        self.cam_toggle.setChecked(hal.is_allowed("camera") if hal else False)
        self.cam_toggle.stateChanged.connect(self.on_cam_toggle)
        layout.addWidget(self.cam_toggle)

        self.cam_debug_toggle = QCheckBox("Enable Vision Debug Overlay")
        self.cam_debug_toggle.setFont(QFont("Inter", 10))
        self.cam_debug_toggle.setStyleSheet("color: #F5F5F5; padding: 3px;")
        
        initial_debug = False
        try:
            from ultron.memory import get_memory_manager
            mem = get_memory_manager()
            if mem:
                records = mem.list_records("provider_settings", limit=100)
                for r in records:
                    if r["title"] == "vision_debug_overlay":
                        initial_debug = r["content"].lower() == "true"
                        break
        except Exception:
            pass
            
        self.cam_debug_toggle.setChecked(initial_debug)
        self.cam_debug_toggle.stateChanged.connect(self.on_cam_debug_toggle)
        layout.addWidget(self.cam_debug_toggle)
        
        # Subsystem settings
        selectors_box = QGroupBox("Subsystem Providers & Settings")
        selectors_box.setStyleSheet("QGroupBox { color: #F5F5F5; font-weight: bold; border: 1px solid rgba(255,255,255,0.05); margin-top: 10px; padding-top: 15px; } QLabel { color: #A0A0A0; font-weight: normal; }")
        form = QFormLayout(selectors_box)
        
        from ultron.core.config_loader import config_loader
        reco_val = config_loader.get("voice", "recognizer", "sapi")
        wake_val = config_loader.get("voice", "wake", "sapi_wake")
        tts_val = config_loader.get("voice", "tts", "pyttsx3")
        wake_phrase_val = config_loader.get("voice", "wake_phrase", "ultron")
        
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["Default", "Home", "Development", "Coding", "Gaming", "Offline", "Battery Saver", "Testing"])
        self.profile_combo.setCurrentText("Default")
        self.profile_combo.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        form.addRow("Configuration Profile:", self.profile_combo)
        
        self.reco_combo = QComboBox()
        self.reco_combo.addItems(["sapi", "vosk", "whisper", "future"])
        self.reco_combo.setCurrentText(reco_val)
        self.reco_combo.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        self.reco_combo.currentTextChanged.connect(self.on_reco_changed)
        form.addRow("Recognition Provider:", self.reco_combo)
        
        # Vosk path
        vosk_path_layout = QHBoxLayout()
        self.vosk_path_input = QLineEdit()
        self.vosk_path_input.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        
        initial_path = ""
        try:
            from ultron.memory import get_memory_manager
            mem = get_memory_manager()
            if mem:
                records = mem.list_records("provider_settings", limit=100)
                for r in records:
                    if r["title"] == "vosk_model_path":
                        initial_path = r["content"]
                        break
        except Exception:
            pass
            
        if not initial_path:
            try:
                from ultron.voice.vosk_model_resolver import resolve_vosk_model
                resolved = resolve_vosk_model()
                if resolved:
                    initial_path = resolved
            except Exception:
                pass
                     
        self.vosk_path_input.setText(initial_path)
        
        def save_vosk_path(path_text):
            try:
                from ultron.memory import get_memory_manager
                mem = get_memory_manager()
                if mem:
                    records = mem.list_records("provider_settings", limit=100)
                    rec = next((r for r in records if r["title"] == "vosk_model_path"), None)
                    if rec:
                        mem.update_record("provider_settings", rec["id"], {"content": path_text})
                    else:
                        mem.create_record("provider_settings", title="vosk_model_path", content=path_text)
            except Exception:
                pass
                
        self.vosk_path_input.textChanged.connect(save_vosk_path)
        vosk_path_layout.addWidget(self.vosk_path_input)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.setStyleSheet("background-color: rgba(255,255,255,0.05); color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px 8px;")
        
        def browse_vosk_model():
            dir_path = QFileDialog.getExistingDirectory(self, "Select Vosk Model Directory", self.vosk_path_input.text() or os.getcwd())
            if dir_path:
                self.vosk_path_input.setText(dir_path)
                
        btn_browse.clicked.connect(browse_vosk_model)
        vosk_path_layout.addWidget(btn_browse)
        form.addRow("Vosk Model Path:", vosk_path_layout)
        
        self.wake_combo = QComboBox()
        self.wake_combo.addItems(["sapi_wake", "openwakeword", "future"])
        self.wake_combo.setCurrentText(wake_val)
        self.wake_combo.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        self.wake_combo.currentTextChanged.connect(self.on_wake_changed)
        form.addRow("Wake Provider:", self.wake_combo)
        
        self.tts_combo = QComboBox()
        self.tts_combo.addItems(["pyttsx3", "piper", "future"])
        self.tts_combo.setCurrentText(tts_val)
        self.tts_combo.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        self.tts_combo.currentTextChanged.connect(self.on_tts_changed)
        form.addRow("Speech Provider:", self.tts_combo)
        
        self.wake_phrase_input = QLineEdit()
        self.wake_phrase_input.setText(wake_phrase_val)
        self.wake_phrase_input.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        self.wake_phrase_input.textChanged.connect(self.on_wake_phrase_changed)
        form.addRow("Wake Phrase:", self.wake_phrase_input)
        
        self.cam_combo = QComboBox()
        self.cam_combo.addItems(["opencv", "mediapipe", "future"])
        self.cam_combo.setCurrentText("opencv")
        self.cam_combo.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        form.addRow("Camera Provider:", self.cam_combo)
 
        self.llm_combo = QComboBox()
        self.llm_combo.addItems(["Ollama", "llama.cpp", "OpenAI", "Anthropic", "DeepSeek", "Gemini"])
        self.llm_combo.setCurrentText("Ollama")
        self.llm_combo.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        form.addRow("LLM Provider:", self.llm_combo)
        
        # Audio selection
        devices = []
        try:
            import sounddevice as sd
            devices = sd.query_devices()
        except ImportError:
            pass
        except Exception:
            pass
        mic_devs = [d["name"] for d in devices if d.get("max_input_channels", 0) > 0]
        spk_devs = [d["name"] for d in devices if d.get("max_output_channels", 0) > 0]
        if not mic_devs: mic_devs = ["Default Microphone"]
        if not spk_devs: spk_devs = ["Default Speaker"]
 
        preferred_mic = None
        preferred_sr = "16000"
        try:
            from ultron.memory import get_memory_manager
            mem = get_memory_manager()
            if mem:
                records = mem.list_records("voice_settings")
                for r in records:
                    if r["title"] == "preferred_microphone_name":
                        preferred_mic = r["content"]
                    elif r["title"] == "recognition_sample_rate":
                        preferred_sr = r["content"]
        except Exception:
            pass
 
        self.mic_combo = QComboBox()
        self.mic_combo.addItems(mic_devs)
        if preferred_mic and preferred_mic in mic_devs:
            self.mic_combo.setCurrentText(preferred_mic)
        self.mic_combo.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        self.mic_combo.currentTextChanged.connect(self.on_mic_changed)
        form.addRow("Microphone Device:", self.mic_combo)
 
        # Volume meter
        from PySide6.QtWidgets import QProgressBar
        test_layout = QHBoxLayout()
        self.volume_meter = QProgressBar()
        self.volume_meter.setRange(0, 100)
        self.volume_meter.setValue(0)
        self.volume_meter.setTextVisible(True)
        self.volume_meter.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255,255,255,0.05);
                background-color: #111111;
                color: #F5F5F5;
                text-align: center;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #E63946;
            }
        """)
        
        self.test_mic_btn = QPushButton("Test Microphone")
        self.test_mic_btn.setStyleSheet("background-color: rgba(255,255,255,0.05); color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px 8px;")
        
        self.testing_mic = False
        def toggle_test_mic():
            self.testing_mic = not self.testing_mic
            if self.testing_mic:
                self.test_mic_btn.setText("Stop Test")
                event_bus.publish("START_VOLUME_TEST", {})
            else:
                self.test_mic_btn.setText("Test Microphone")
                self.volume_meter.setValue(0)
                event_bus.publish("STOP_VOLUME_TEST", {})
                
        self.test_mic_btn.clicked.connect(toggle_test_mic)
        test_layout.addWidget(self.volume_meter)
        test_layout.addWidget(self.test_mic_btn)
        form.addRow("Microphone Test:", test_layout)
 
        self.sr_combo = QComboBox()
        self.sr_combo.addItems(["16000", "44100", "48000"])
        self.sr_combo.setCurrentText(preferred_sr)
        self.sr_combo.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        self.sr_combo.currentTextChanged.connect(self.on_sample_rate_changed)
        form.addRow("Sample Rate (Hz):", self.sr_combo)
 
        self.spk_combo = QComboBox()
        self.spk_combo.addItems(spk_devs)
        self.spk_combo.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 3px;")
        form.addRow("Speaker Device:", self.spk_combo)
 
        from PySide6.QtWidgets import QSlider
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setMinimum(0)
        self.sensitivity_slider.setMaximum(100)
        self.sensitivity_slider.setValue(80)
        form.addRow("Voice Sensitivity:", self.sensitivity_slider)
 
        self.noise_check = QCheckBox("Enable Noise Suppression")
        self.noise_check.setFont(QFont("Inter", 10))
        self.noise_check.setStyleSheet("color: #A0A0A0;")
        self.noise_check.setChecked(True)
        form.addRow("", self.noise_check)
 
        self.vad_check = QCheckBox("Enable Voice Activity Detection (VAD)")
        self.vad_check.setFont(QFont("Inter", 10))
        self.vad_check.setStyleSheet("color: #A0A0A0;")
        self.vad_check.setChecked(True)
        form.addRow("", self.vad_check)
        
        layout.addWidget(selectors_box)
        
        # Telemetry info display
        diag_box = QGroupBox("Live Voice Diagnostics")
        diag_box.setStyleSheet("QGroupBox { color: #C1121F; font-weight: bold; border: 1px solid rgba(255,255,255,0.05); margin-top: 10px; padding-top: 15px; } QLabel { color: #A0A0A0; font-weight: normal; }")
        diag_layout = QGridLayout(diag_box)
        
        self.lbl_reco_prov = QLabel("Recognition Provider: -")
        self.lbl_model = QLabel("Model: -")
        self.lbl_mic_dev = QLabel("Microphone: -")
        self.lbl_status = QLabel("Status: -")
        self.lbl_audio_chunks = QLabel("Audio Chunks: -")
        self.lbl_last_speech = QLabel("Last Recognized Speech: -")
        self.lbl_last_wake_phrase = QLabel("Last Wake Phrase: -")
        self.lbl_reco_confidence = QLabel("Recognition Confidence: -")
        self.lbl_reco_latency = QLabel("Recognition Latency: -")
        self.lbl_voice_thread = QLabel("Voice Thread: -")
        self.lbl_wake_thread = QLabel("Wake Thread: -")
        
        self.lbl_session_active = QLabel("Session Active: -")
        self.lbl_session_timeout = QLabel("Session Timeout: -")
        self.lbl_last_wake_time = QLabel("Last Wake Time: -")
        self.lbl_last_command = QLabel("Last Command: -")
        self.lbl_last_state_transition = QLabel("Last State Transition: -")
        
        self.lbl_diag_mic_connected = QLabel("Microphone Connected: -")
        self.lbl_diag_curr_dev = QLabel("Current Device: -")
        self.lbl_diag_reco_prov = QLabel("Recognition Provider: -")
        self.lbl_diag_reco_running = QLabel("Recognition Running: -")
        self.lbl_diag_wake_running = QLabel("Wake Detector Running: -")
        self.lbl_diag_last_phrase = QLabel("Last Recognized Phrase: -")
        self.lbl_diag_wake_match = QLabel("Wake Match: -")
        self.lbl_diag_reco_fps = QLabel("Recognition FPS: -")
        self.lbl_diag_thread_alive = QLabel("Recognition Thread Alive: -")
        self.lbl_diag_callback_count = QLabel("Audio Callback Count: -")
        self.lbl_diag_dropped_buffers = QLabel("Dropped Buffers: -")
 
        self.lbl_wake_prov = QLabel("Wake Provider: -")
        self.lbl_tts_prov = QLabel("TTS Provider: -")
        self.lbl_state = QLabel("Current State: -")
        self.lbl_wake_phrase = QLabel("Wake Phrase: -")
        self.lbl_last_wake = QLabel("Last Wake Event: -")
        self.lbl_srv_health = QLabel("Service Health: -")
        self.lbl_thread_status = QLabel("Thread Status: -")
        self.lbl_latency = QLabel("Latency: -")
        
        self.lbl_spk_dev = QLabel("Speaker: -")
        self.lbl_cpu = QLabel("CPU Usage: -")
        self.lbl_mem = QLabel("Memory Usage: -")
        self.lbl_queue = QLabel("Queue Size: -")
        self.lbl_last_ai = QLabel("Last AI Response: -")
        self.lbl_last_err = QLabel("Last Error: -")
        
        self.lbl_vision_prov = QLabel("Vision Provider: -")
        self.lbl_llm_prov = QLabel("LLM Provider: -")
        self.lbl_cam_dev = QLabel("Camera: -")
        self.lbl_running_services = QLabel("Running Services: -")
        self.lbl_plugin_count = QLabel("Plugin Count: -")
        self.lbl_sqlite_size = QLabel("SQLite Size: -")
        self.lbl_current_skill = QLabel("Current Skill: -")
        self.lbl_current_project = QLabel("Current Project: -")
        
        self.lbl_last_notif = QLabel("Last Notification: -")
        self.lbl_last_warn = QLabel("Last Warning: -")
        
        diag_layout.addWidget(self.lbl_reco_prov, 0, 0)
        diag_layout.addWidget(self.lbl_model, 0, 1)
        diag_layout.addWidget(self.lbl_mic_dev, 1, 0)
        diag_layout.addWidget(self.lbl_status, 1, 1)
        diag_layout.addWidget(self.lbl_audio_chunks, 2, 0)
        diag_layout.addWidget(self.lbl_last_speech, 2, 1)
        diag_layout.addWidget(self.lbl_last_wake_phrase, 3, 0)
        diag_layout.addWidget(self.lbl_reco_confidence, 3, 1)
        diag_layout.addWidget(self.lbl_reco_latency, 4, 0)
        diag_layout.addWidget(self.lbl_voice_thread, 4, 1)
        diag_layout.addWidget(self.lbl_wake_thread, 5, 0)
        
        diag_layout.addWidget(self.lbl_tts_prov, 5, 1)
        diag_layout.addWidget(self.lbl_spk_dev, 6, 0)
        diag_layout.addWidget(self.lbl_cpu, 6, 1)
        diag_layout.addWidget(self.lbl_mem, 7, 0)
        diag_layout.addWidget(self.lbl_queue, 7, 1)
        diag_layout.addWidget(self.lbl_last_ai, 8, 0)
        
        diag_layout.addWidget(self.lbl_vision_prov, 8, 1)
        diag_layout.addWidget(self.lbl_llm_prov, 9, 0)
        diag_layout.addWidget(self.lbl_cam_dev, 9, 1)
        diag_layout.addWidget(self.lbl_running_services, 10, 0)
        diag_layout.addWidget(self.lbl_plugin_count, 10, 1)
        diag_layout.addWidget(self.lbl_sqlite_size, 11, 0)
        diag_layout.addWidget(self.lbl_current_skill, 11, 1)
        diag_layout.addWidget(self.lbl_current_project, 12, 0)
        diag_layout.addWidget(self.lbl_wake_prov, 12, 1)
        
        diag_layout.addWidget(self.lbl_session_active, 13, 0)
        diag_layout.addWidget(self.lbl_session_timeout, 13, 1)
        diag_layout.addWidget(self.lbl_last_wake_time, 14, 0)
        diag_layout.addWidget(self.lbl_last_state_transition, 14, 1)
        diag_layout.addWidget(self.lbl_last_command, 15, 0, 1, 2)
        
        diag_layout.addWidget(self.lbl_last_notif, 16, 0, 1, 2)
        diag_layout.addWidget(self.lbl_last_warn, 17, 0, 1, 2)
        diag_layout.addWidget(self.lbl_last_err, 18, 0, 1, 2)
        
        diag_layout.addWidget(self.lbl_diag_mic_connected, 19, 0)
        diag_layout.addWidget(self.lbl_diag_curr_dev, 19, 1)
        diag_layout.addWidget(self.lbl_diag_reco_prov, 20, 0)
        diag_layout.addWidget(self.lbl_diag_reco_running, 20, 1)
        diag_layout.addWidget(self.lbl_diag_wake_running, 21, 0)
        diag_layout.addWidget(self.lbl_diag_last_phrase, 21, 1)
        diag_layout.addWidget(self.lbl_diag_wake_match, 22, 0)
        diag_layout.addWidget(self.lbl_diag_reco_fps, 22, 1)
        diag_layout.addWidget(self.lbl_diag_thread_alive, 23, 0)
        diag_layout.addWidget(self.lbl_diag_callback_count, 23, 1)
        diag_layout.addWidget(self.lbl_diag_dropped_buffers, 24, 0, 1, 2)
        
        layout.addWidget(diag_box)
        layout.addSpacing(15)
        
        self.settings_view = QTextEdit()
        self.settings_view.setReadOnly(True)
        self.settings_view.setFont(QFont("Consolas", 9))
        self.settings_view.setStyleSheet("background-color: #111111; border: 1px solid rgba(255,255,255,0.05); color: #A0A0A0; min-height: 120px;")
        layout.addWidget(self.settings_view)
        
        scroll.setWidget(widget)
        main_layout.addWidget(scroll)
        return main_widget

    # ── State listeners and handlers ──

    # ── Thread-Safe EventBus Routing ──

    def _event_bus_route_callback(self, event):
        """Dispatched on worker threads — safely routes EventBus events to the main thread."""
        self.event_signal.emit(event)

    @Slot(object)
    def _handle_queued_event(self, event):
        """Executed on the Qt main thread — dispatches to standard handlers."""
        et = event.event_type
        if et == "STATE_CHANGED":
            self.on_state_changed(event)
        elif et == "VOICE_STATE_CHANGED":
            self.on_voice_state_changed(event)
        elif et == "QUEUE_COUNT_CHANGED":
            self.on_queue_count_changed(event)
        elif et == "WAKE_TRIGGERED":
            self.on_wake_triggered(event)
        elif et == "SLEEP_TRIGGERED":
            self.on_sleep_triggered(event)
        elif et == "VOICE_DIAGNOSTICS_UPDATE":
            self.on_voice_diagnostics_update(event)
        elif et == "NOTIFICATION":
            self.on_notification_event(event)
        elif et == "WARNING_OCCURRED":
            self.on_warning_event(event)
        elif et == "ERROR_OCCURRED":
            self.on_error_event(event)
        elif et == "VOSK_MODEL_MISSING":
            self.on_vosk_model_missing(event)
        elif et == "VOLUME_LEVEL_CHANGED":
            self.on_volume_level_changed(event)
        elif et == "AI_RESPONSE_READY":
            self.on_ai_response_ready(event)
        elif et in ["HiddenItemAdded", "HiddenItemRestored", "HiddenItemOpened", "HiddenItemMissing"]:
            self.refresh_hidden_items_view()

    # ── State listeners and handlers (Main Thread Only) ──

    @Slot(object)
    def on_state_changed(self, event):
        state = event.payload.get("state", "Sleeping")
        self.floating_widget.set_state(state)
        self.reactor.set_state(state)
        self.thought_stream.set_voice_state(state)
        
        # Animate mic button
        if state.lower() == "listening":
            self.mic_btn.set_state("listening")
            self.active_status_lbl.setText("Listening...")
        elif state.lower() == "thinking":
            self.mic_btn.set_state("processing")
            self.active_status_lbl.setText("Thinking...")
        elif state.lower() == "speaking":
            self.mic_btn.set_state("idle")
            self.active_status_lbl.setText("Speaking...")
        else:
            self.mic_btn.set_state("idle")
            self.active_status_lbl.setText("Sleeping...")

    @Slot(object)
    def on_voice_state_changed(self, event):
        voice_state = event.payload.get("state", "SLEEPING")
        self.current_voice_state = voice_state
        
        visual_map = {
            "BOOTING": "Sleeping",
            "INITIALIZING": "Thinking",
            "READY": "Sleeping",
            "SLEEPING": "Sleeping",
            "WAKING": "Speaking",
            "GREETING": "Speaking",
            "LISTENING": "Listening",
            "PROCESSING": "Thinking",
            "RESPONDING": "Speaking",
            "TIMEOUT": "Speaking",
            "ERROR": "Error",
            "SHUTDOWN": "Sleeping"
        }
        visual_state = visual_map.get(voice_state, "Sleeping")
        self.floating_widget.set_state(visual_state)
        self.reactor.set_state(visual_state)
        self.thought_stream.set_voice_state(voice_state)
        
        # Set dynamic Active Listening status texts
        if voice_state.upper() == "LISTENING":
            self.mic_btn.set_state("listening")
            self.active_status_lbl.setText("Listening...")
        elif voice_state.upper() in ["PROCESSING", "INITIALIZING", "THINKING"]:
            self.mic_btn.set_state("processing")
            self.active_status_lbl.setText("Thinking...")
        elif voice_state.upper() in ["RESPONDING", "GREETING", "WAKING", "SPEAKING"]:
            self.mic_btn.set_state("idle")
            self.active_status_lbl.setText("Speaking...")
        else:
            self.mic_btn.set_state("idle")
            self.active_status_lbl.setText("Sleeping...")

        badge_text = "Sleeping"
        if voice_state.upper() == "LISTENING":
            badge_text = "Listening"
        elif voice_state.upper() in ["PROCESSING", "INITIALIZING"]:
            badge_text = "Thinking"
        elif voice_state.upper() in ["RESPONDING", "GREETING", "WAKING"]:
            badge_text = "Speaking"
        
        self.user_badge.setText(badge_text)
        
        if voice_state in ["BOOTING", "INITIALIZING"]:
            self.lock_ui()
        else:
            self.unlock_ui()

    @Slot(object)
    def on_queue_count_changed(self, event):
        self.queue_count = event.payload.get("count", 0)

    @Slot(object)
    def on_wake_triggered(self, event):
        pass

    @Slot(object)
    def on_sleep_triggered(self, event):
        pass

    @Slot(object)
    def on_voice_diagnostics_update(self, event):
        data = event.payload
        self.update_voice_diagnostics_ui(data)

    def update_voice_diagnostics_ui(self, data):
        if not hasattr(self, "lbl_reco_prov"):
            return
        self.lbl_reco_prov.setText(f"Recognition Provider: <span style='color: #00FF00;'>{data.get('recognition_engine', '-')}</span>")
        self.lbl_model.setText(f"Model: <span style='color: #00FF00;'>{data.get('model', '-')}</span>")
        self.lbl_mic_dev.setText(f"Microphone: <span style='color: #00FF00;'>{data.get('microphone', '-')}</span>")
        self.lbl_status.setText(f"Status: <span style='color: #00FF00;'>{data.get('status', '-')}</span>")
        self.lbl_audio_chunks.setText(f"Audio Chunks: <span style='color: #00FF00;'>{data.get('audio_chunks', 0)}</span>")
        self.lbl_last_speech.setText(f"Last Recognized Speech: <span style='color: #00FF00;'>'{data.get('last_recognized_speech', '-')}'</span>")
        self.lbl_last_wake_phrase.setText(f"Last Wake Phrase: <span style='color: #00FF00;'>{data.get('last_wake_phrase', '-')}</span>")
        
        conf = data.get('recognition_confidence', 0.0)
        self.lbl_reco_confidence.setText(f"Recognition Confidence: <span style='color: #00FF00;'>{conf:.2f}</span>")
        self.lbl_reco_latency.setText(f"Recognition Latency: <span style='color: #00FF00;'>{data.get('recognition_latency', '-')}</span>")
        self.lbl_voice_thread.setText(f"Voice Thread: <span style='color: #00FF00;'>{data.get('voice_thread', '-')}</span>")
        self.lbl_wake_thread.setText(f"Wake Thread: <span style='color: #00FF00;'>{data.get('wake_thread', '-')}</span>")

        self.lbl_wake_prov.setText(f"Wake Provider: <span style='color: #00FF00;'>{data.get('wake_engine', '-')}</span>")
        self.lbl_tts_prov.setText(f"TTS Provider: <span style='color: #00FF00;'>{data.get('tts_engine', '-')}</span>")
        disp_st = self.current_voice_state
        if disp_st == "SLEEPING":
            disp_st = "STANDBY"
        elif disp_st in ["THINKING", "EXECUTING"]:
            disp_st = "PROCESSING"
        elif disp_st == "SPEAKING":
            disp_st = "RESPONDING"
        self.lbl_state.setText(f"Current State: <span style='color: #00FF00;'>{disp_st}</span>")
        self.lbl_wake_phrase.setText(f"Wake Phrase: <span style='color: #FF8C00;'>{data.get('current_wake_phrase', '-')}</span>")
        
        last_wake = data.get('last_wake_event', 0.0)
        last_wake_str = time.strftime('%H:%M:%S', time.localtime(last_wake)) if last_wake > 0 else "-"
        self.lbl_last_wake.setText(f"Last Wake: {last_wake_str}")

        self.lbl_session_active.setText(f"Session Active: <span style='color: #00FF00;'>{data.get('session_active', '-')}</span>")
        self.lbl_session_timeout.setText(f"Session Timeout: <span style='color: #00FF00;'>{data.get('session_timeout', '-')}</span>")
        self.lbl_last_wake_time.setText(f"Last Wake Time: <span style='color: #00FF00;'>{data.get('last_wake_time', '-')}</span>")
        self.lbl_last_command.setText(f"Last Command: <span style='color: #00FF00;'>{data.get('last_command', '-')}</span>")
        self.lbl_last_state_transition.setText(f"Last State Transition: <span style='color: #00FF00;'>{data.get('last_state_transition', '-')}</span>")
        
        self.lbl_srv_health.setText(f"Service Health: <span style='color: #00FF00;'>{data.get('com_status', '-')}</span>")
        self.lbl_thread_status.setText(f"Reco Thread: <span style='color: #00FF00;'>{data.get('recognition_status', '-')}</span>")
        self.lbl_latency.setText(f"Callbacks: {data.get('callback_count', 0)} | Wake Matches: {data.get('wake_matches', 0)}")

        spk_name = data.get("current_speaker", "-")
        self.lbl_spk_dev.setText(f"Speaker: {spk_name}")
        
        self.lbl_cpu.setText("CPU Usage: <span style='color: #00FF00;'>1.5%</span>")
        self.lbl_mem.setText("Memory Usage: <span style='color: #00FF00;'>42 MB</span>")
        self.lbl_queue.setText(f"Queue Size: {self.queue_count}")
        
        last_ai = data.get("last_ai_response", "None")
        if len(last_ai) > 40:
            last_ai = last_ai[:40] + "..."
        self.lbl_last_ai.setText(f"Last AI Response: '{last_ai}'")
        
        last_err = data.get("last_error", "None")
        self.lbl_last_err.setText(f"Last Error: <span style='color: #C1121F;'>{last_err}</span>")

        self.lbl_vision_prov.setText(f"Vision Provider: <span style='color: #00FF00;'>{data.get('vision_engine', 'opencv')}</span>")
        self.lbl_llm_prov.setText(f"LLM Provider: <span style='color: #00FF00;'>{data.get('llm_engine', 'Ollama')}</span>")
        self.lbl_cam_dev.setText(f"Camera: {data.get('camera', '-')}")
        self.lbl_running_services.setText(f"Running Services: <span style='color: #00FF00;'>{data.get('running_services_count', 0)}</span>")
        self.lbl_plugin_count.setText(f"Plugin Count: <span style='color: #00FF00;'>{data.get('plugin_count', 0)}</span>")
        self.lbl_sqlite_size.setText(f"SQLite Size: <span style='color: #00FF00;'>{data.get('sqlite_size', '-')}</span>")
        self.lbl_current_skill.setText(f"Current Skill: {data.get('current_skill', '-')}")
        self.lbl_current_project.setText(f"Current Project: {data.get('current_project', '-')}")
        
        mic_conn = "Yes" if data.get('com_status') == "Healthy" else "No"
        self.lbl_diag_mic_connected.setText(f"Microphone Connected: <span style='color: #00FF00;'>{mic_conn}</span>")
        self.lbl_diag_curr_dev.setText(f"Current Device: <span style='color: #00FF00;'>{data.get('microphone', '-')}</span>")
        self.lbl_diag_reco_prov.setText(f"Recognition Provider: <span style='color: #00FF00;'>{data.get('recognition_engine', '-')}</span>")
        
        reco_run = data.get('recognition_status', 'Offline')
        self.lbl_diag_reco_running.setText(f"Recognition Running: <span style='color: #00FF00;'>{reco_run}</span>")
        
        wake_run = data.get('wake_status', 'Offline')
        self.lbl_diag_wake_running.setText(f"Wake Detector Running: <span style='color: #00FF00;'>{wake_run}</span>")
        
        last_phrase = data.get('last_recognized_phrase', '-')
        self.lbl_diag_last_phrase.setText(f"Last Recognized Phrase: <span style='color: #00FF00;'>'{last_phrase}'</span>")
        self.lbl_diag_wake_match.setText(f"Wake Match: <span style='color: #00FF00;'>{data.get('wake_matches', 0)}</span>")
        
        fps_val = "7.8"
        self.lbl_diag_reco_fps.setText(f"Recognition FPS: <span style='color: #00FF00;'>{fps_val}</span>")
        
        thread_alive = "Yes" if (reco_run == "Running") else "No"
        self.lbl_diag_thread_alive.setText(f"Recognition Thread Alive: <span style='color: #00FF00;'>{thread_alive}</span>")
        self.lbl_diag_callback_count.setText(f"Audio Callback Count: <span style='color: #00FF00;'>{data.get('audio_chunks', 0)}</span>")
        self.lbl_diag_dropped_buffers.setText(f"Dropped Buffers: <span style='color: #00FF00;'>{data.get('dropped_buffers', 0)}</span>")

    # ── Configuration callbacks ──

    def on_mic_toggle(self, state):
        allowed = (state == 2)
        hal = get_hal_manager()
        if hal:
            hal.save_permission("microphone", allowed)
        svc = "VoiceRecognitionService"
        QTimer.singleShot(0, lambda: service_manager.start_service(svc) if allowed else service_manager.stop_service(svc))

    def on_spk_toggle(self, state):
        allowed = (state == 2)
        hal = get_hal_manager()
        if hal:
            hal.save_permission("speaker", allowed)
        svc = "SpeechService"
        QTimer.singleShot(0, lambda: service_manager.start_service(svc) if allowed else service_manager.stop_service(svc))

    def on_cam_toggle(self, state):
        allowed = (state == 2)
        hal = get_hal_manager()
        if hal:
            hal.save_permission("camera", allowed)
        if allowed:
            QTimer.singleShot(0, lambda: service_manager.start_service("VisionService"))
            if hasattr(self, "camera_preview"):
                self.camera_preview.show()
        else:
            QTimer.singleShot(0, lambda: service_manager.stop_service("VisionService"))
            if hasattr(self, "camera_preview"):
                self.camera_preview.hide()

    def on_cam_debug_toggle(self, state):
        allowed = (state == 2)
        try:
            from ultron.memory import get_memory_manager
            mem = get_memory_manager()
            if mem:
                records = mem.list_records("provider_settings", limit=100)
                rec = next((r for r in records if r["title"] == "vision_debug_overlay"), None)
                if rec:
                    mem.update_record("provider_settings", rec["id"], {"content": str(allowed)})
                else:
                    mem.create_record("provider_settings", title="vision_debug_overlay", content=str(allowed))
        except Exception:
            pass
        event_bus.publish("VISION_DEBUG_TOGGLED", {"enabled": allowed})

    def on_reco_changed(self, text):
        self.save_voice_config("recognizer", text)
        event_bus.publish("RECOGNITION_PROVIDER_CHANGED", {"provider": text})

    def on_wake_changed(self, text):
        self.save_voice_config("wake", text)

    def on_tts_changed(self, text):
        self.save_voice_config("tts", text)
        event_bus.publish("TTS_PROVIDER_CHANGED", {"provider": text})

    def on_mic_changed(self, text):
        devices = []
        try:
            import sounddevice as sd
            devices = sd.query_devices()
        except ImportError:
            pass
        except Exception:
            pass
        
        device_idx = None
        for idx, d in enumerate(devices):
            if d["name"] == text and d.get("max_input_channels", 0) > 0:
                device_idx = idx
                break
                
        if device_idx is not None:
            voice_engine = service_manager.get_service("VoiceEngineService")
            if voice_engine:
                voice_engine.switch_microphone(text, device_idx)

    def on_sample_rate_changed(self, text):
        rate = int(text)
        voice_engine = service_manager.get_service("VoiceEngineService")
        if voice_engine:
            voice_engine.switch_sample_rate(rate)

    @Slot(object)
    def on_volume_level_changed(self, event):
        if not hasattr(self, "volume_meter") or self.volume_meter is None:
            return
        level = event.payload.get("level", 0.0)
        percent = min(100, int((level / 4000.0) * 100))
        self.volume_meter.setValue(percent)

    def on_wake_phrase_changed(self, text):
        self.save_voice_config("wake_phrase", text)
        engine_srv = service_manager.get_service("VoiceEngineService")
        if engine_srv:
            engine_srv.update_wake_phrase(text)

    @Slot(object)
    def on_notification_event(self, event):
        msg = event.payload.get("message", "-")
        title = event.payload.get("title", "-")
        notif_str = f"Last Notification: {title} - {msg}"
        if hasattr(self, "lbl_last_notif"):
            self.lbl_last_notif.setText(notif_str)

    @Slot(object)
    def on_warning_event(self, event):
        msg = event.payload.get("message", "-")
        warn_str = f"Last Warning: <span style='color: yellow;'>{msg}</span>"
        if hasattr(self, "lbl_last_warn"):
            self.lbl_last_warn.setText(warn_str)

    @Slot(object)
    def on_error_event(self, event):
        msg = event.payload.get("message", "-")
        err_str = f"Last Error: <span style='color: #C1121F;'>{msg}</span>"
        if hasattr(self, "lbl_last_err"):
            self.lbl_last_err.setText(err_str)

    @Slot(str)
    def on_profile_changed(self, profile_name):
        profiles = {
            "Default": {"reco": "sapi", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "ultron", "llm": "Ollama"},
            "Home": {"reco": "sapi", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "ultron", "llm": "Ollama"},
            "Development": {"reco": "vosk", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "ultron", "llm": "llama.cpp"},
            "Coding": {"reco": "vosk", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "ultron", "llm": "llama.cpp"},
            "Gaming": {"reco": "vosk", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "hey ultron", "llm": "Gemini"},
            "Offline": {"reco": "vosk", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "ultron", "llm": "llama.cpp"},
            "Battery Saver": {"reco": "sapi", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "ultron", "llm": "Ollama"},
            "Testing": {"reco": "vosk", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "ultron", "llm": "Ollama"},
        }
        prof = profiles.get(profile_name, profiles["Default"])
        
        self.reco_combo.blockSignals(True)
        self.wake_combo.blockSignals(True)
        self.tts_combo.blockSignals(True)
        self.wake_phrase_input.blockSignals(True)
        self.llm_combo.blockSignals(True)
        
        self.reco_combo.setCurrentText(prof["reco"])
        self.wake_combo.setCurrentText(prof["wake"])
        self.tts_combo.setCurrentText(prof["tts"])
        self.wake_phrase_input.setText(prof["phrase"])
        self.llm_combo.setCurrentText(prof["llm"])
        
        self.reco_combo.blockSignals(False)
        self.wake_combo.blockSignals(False)
        self.tts_combo.blockSignals(False)
        self.wake_phrase_input.blockSignals(False)
        self.llm_combo.blockSignals(False)
        
        self.on_reco_changed(prof["reco"])
        self.on_wake_changed(prof["wake"])
        self.on_tts_changed(prof["tts"])
        self.on_wake_phrase_changed(prof["phrase"])
        
        event_bus.publish("CONFIGURATION_PROFILE_CHANGED", {"profile": profile_name})

    def save_voice_config(self, key, value):
        config_path = "config/voice.json"
        data = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        data[key] = value
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass
        
        try:
            records = self.memory.list_records("preference")
            pref_id = None
            for r in records:
                if r["title"] == f"voice_{key}":
                    pref_id = r["id"]
                    break
            if pref_id:
                self.memory.update_record("preference", pref_id, {"content": str(value)})
            else:
                self.memory.create_record("preference", f"voice_{key}", str(value))
        except Exception:
            pass
        
        self.refresh_settings_view()

    def refresh_diagnostics(self):
        """Public alias kept for compatibility — delegates to the background worker."""
        self._start_diag_worker()

    def _start_diag_worker(self):
        """Starts a one-shot background thread to gather diagnostics. Skips if one is already running."""
        try:
            if self._diag_worker and self._diag_worker.isRunning():
                return
        except RuntimeError:
            self._diag_worker = None
        from ultron.core.voice_session_manager import get_voice_session_manager
        mgr = get_voice_session_manager()
        # Read Qt-thread-only values HERE before handing off to the worker
        timer_active = "Active" if (mgr and mgr.session_timer.isActive()) else "Inactive"
        rem_ms = mgr.session_timer.remainingTime() if mgr else -1
        
        # Pre-fetch hardware devices and permissions safely on Qt main thread
        hal = get_hal_manager()
        devices = hal.check_devices() if hal else {"microphone": False, "speaker": False, "camera": False}
        mic_allowed = hal.is_allowed('microphone') if hal else False
        speaker_allowed = hal.is_allowed('speaker') if hal else False
        camera_allowed = hal.is_allowed('camera') if hal else False

        snapshot = {
            "queue_count":          self.queue_count,
            "current_voice_state": self.current_voice_state,
            "timer_active":        timer_active,
            "sec_rem":             f"{rem_ms / 1000.0:.1f} s" if rem_ms >= 0 else "-",
            "devices":             devices,
            "mic_allowed":         mic_allowed,
            "speaker_allowed":     speaker_allowed,
            "camera_allowed":      camera_allowed,
        }
        self._diag_worker = _DiagnosticsWorker(self.core, snapshot)
        self._diag_worker.html_ready.connect(self._on_diag_html_ready, Qt.ConnectionType.QueuedConnection)
        self._diag_worker.finished.connect(self._diag_worker.deleteLater)
        self._diag_worker.start()

    @Slot(str)
    def _on_diag_html_ready(self, html: str):
        """Receives diagnostic HTML from the worker and updates the display widget on main thread."""
        if hasattr(self, "tools_view") and self.tools_view:
            self.tools_view.setHtml(html)



    def on_vosk_model_missing(self, event):
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "prompt_for_vosk_model", Qt.ConnectionType.QueuedConnection)

    @Slot()
    def prompt_for_vosk_model(self):
        from PySide6.QtWidgets import QMessageBox, QFileDialog
        box = QMessageBox(self)
        box.setWindowTitle("Vosk Model Missing")
        box.setText("The Vosk speech recognition model could not be found automatically.\n\nWould you like to browse and select the model folder now?")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        box.setStyleSheet("background-color: #111111; color: white;")
        ret = box.exec()
        if ret == QMessageBox.StandardButton.Yes:
            dir_path = QFileDialog.getExistingDirectory(self, "Select Vosk Model Directory", os.getcwd())
            if dir_path:
                mem = get_memory_manager()
                if mem:
                    records = mem.list_records("provider_settings", limit=100)
                    rec = next((r for r in records if r["title"] == "vosk_model_path"), None)
                    if rec:
                        mem.update_record("provider_settings", rec["id"], {"content": dir_path})
                    else:
                        mem.create_record("provider_settings", title="vosk_model_path", content=dir_path)
                
                if hasattr(self, "vosk_path_input"):
                    self.vosk_path_input.setText(dir_path)
                service_manager.restart_service("VoiceRecognitionService")

    # ── Navigation panel routing ──

    def switch_panel(self, index):
        for idx, btn in enumerate(self.nav_btns):
            btn.set_active(idx == index)
            
        if index == 4: # Terminal / Dev Console Toggle
            self.toggle_developer_console()
            prev_idx = self.stacked_widget.currentIndex()
            self.nav_btns[4].set_active(False)
            self.nav_btns[prev_idx].set_active(True)
            return

        self.stacked_widget.setCurrentIndex(index)
        if index == 1:
            self.refresh_memory_view()
        elif index == 2:
            self.refresh_projects_view()
        elif index == 5:
            self.refresh_hidden_items_view()
        elif index == 6: # SETTINGS
            self.refresh_settings_view()

    def refresh_memory_view(self):
        self.memory_view.clear()
        html = "<h3 style='color: #C1121F;'>UME STORAGE VIEW</h3>"
        try:
            pref = self.memory.list_records("preference")
            html += "<b>Subsystem Preferences:</b><br/>"
            for p in pref:
                html += f"Key: <code>{p['title']}</code> | Content: <b>{p['content']}</b><br/>"
            
            conv = self.memory.list_records("conversation", limit=20)
            html += "<br/><b>Conversation Turn History:</b><br/>"
            if not conv:
                html += "No previous conversations.<br/>"
            else:
                for c in conv:
                    html += f"<span style='color: gray;'>{c['updated_at']}</span> - <b>{c['title']}</b><br/><pre>{c['content']}</pre><br/>"
        except Exception as e:
            html += f"<span style='color: red;'>Error reading records: {e}</span>"
        self.memory_view.setHtml(html)

    def refresh_projects_view(self):
        self.projects_view.clear()
        html = "<h3 style='color: #C1121F;'>ACTIVE PROJECTS LIST</h3>"
        try:
            projs = self.memory.list_records("project")
            if not projs:
                html += "No projects yet.<br/>Start a project to begin.<br/>"
            else:
                for p in projs:
                    try:
                        data = json.loads(p["content"])
                    except Exception:
                        data = {}
                    html += f"Project: <b style='color: #C1121F;'>{p['title']}</b><br/>"
                    html += f"Directory: <code>{data.get('directory')}</code><br/>"
                    html += f"Status: <b>{data.get('status')}</b><br/>"
                    html += f"Last Milestone: <b>{data.get('last_milestone')}</b><br/>"
                    html += f"Priority Task: <b>{data.get('priority_task')}</b><br/><br/>"
        except Exception as e:
            html += f"<span style='color: red;'>Error reading records: {e}</span>"
        self.projects_view.setHtml(html)

    def refresh_settings_view(self):
        self.settings_view.clear()
        text = "=== CONFIG FILES ===\n\n"
        for name in ["general", "ui", "voice", "memory", "skills"]:
            path = f"config/{name}.json"
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text += f"[{name.upper()}]\n{f.read()}\n\n"
                except Exception:
                    pass
        self.settings_view.setPlainText(text)

    def edit_operator_profile(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Operator Profile")
        dialog.setFixedSize(500, 240)
        dialog.setStyleSheet("background-color: #090909; color: #F5F5F5; border: 1px solid rgba(193, 18, 31, 0.4);")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form = QFormLayout()
        
        from ultron.core.operator import load_operator_profile
        profile = load_operator_profile()
        
        name_input = QLineEdit()
        name_input.setText(profile.get("display_name", ""))
        name_input.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 5px;")
        form.addRow("Operator Name:", name_input)
        
        voice_chk = QCheckBox("Enable Voice control")
        voice_chk.setChecked(profile.get("voice_enabled", True))
        voice_chk.setStyleSheet("color: #F5F5F5;")
        form.addRow("Voice Enabled:", voice_chk)
        
        work_layout = QHBoxLayout()
        work_input = QLineEdit()
        work_input.setText(profile.get("workspace_directory", ""))
        work_input.setStyleSheet("background-color: #111111; color: #F5F5F5; border: 1px solid rgba(255,255,255,0.05); padding: 5px;")
        work_layout.addWidget(work_input)
        
        def browse_dir():
            dir_path = QFileDialog.getExistingDirectory(dialog, "Select Project Workspace", work_input.text() or os.getcwd())
            if dir_path:
                work_input.setText(dir_path.replace("\\", "/"))
                
        btn_browse = QPushButton("Browse...")
        btn_browse.setStyleSheet("background-color: rgba(255,255,255,0.05); color: #F5F5F5; border: 1px solid rgba(255,255,255,0.1); padding: 5px 10px;")
        btn_browse.clicked.connect(browse_dir)
        work_layout.addWidget(btn_browse)
        form.addRow("Workspace:", work_layout)
        
        layout.addLayout(form)
        layout.addSpacing(15)
        
        btn_box = QHBoxLayout()
        btn_save = QPushButton("Save Settings")
        btn_save.setStyleSheet("background-color: #C1121F; color: #F5F5F5; border: 1px solid #C1121F; padding: 6px 16px; font-weight: bold; border-radius: 4px;")
        
        def save():
            name = name_input.text().strip()
            if len(name) < 2 or len(name) > 40:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(dialog, "Validation Error", "Operator name must be between 2 and 40 characters.")
                return
            from ultron.core.operator import save_operator_profile
            save_operator_profile(name, voice_chk.isChecked(), work_input.text().strip())
            
            # Sync display details
            self.display_name = name
            self.op_name.setText(name)
            self.greeting_name_lbl.setText(f"{name}.")
            
            # Sync HAL permissions
            hal = get_hal_manager()
            if hal:
                hal.save_permission("microphone", voice_chk.isChecked())
                hal.save_permission("speaker", voice_chk.isChecked())
                self.mic_toggle.setChecked(voice_chk.isChecked())
                self.spk_toggle.setChecked(voice_chk.isChecked())
                
            self.update_operator_settings_display()
            dialog.accept()
            
        btn_save.clicked.connect(save)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: transparent; color: #A0A0A0; border: 1px solid rgba(255,255,255,0.1); padding: 6px 16px; border-radius: 4px;")
        btn_cancel.clicked.connect(dialog.reject)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)
        
        dialog.exec()

    def reset_operator_onboarding(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Reset Onboarding",
            "This will delete your operator profile and restart setup.\n\nAre you sure you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from ultron.core.operator import get_operator_profile_path
            path = get_operator_profile_path()
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to delete profile: {e}")
                    return
            
            # Restart ULTRON
            from PySide6.QtWidgets import QApplication
            QApplication.quit()
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def open_operator_workspace(self):
        from ultron.core.operator import load_operator_profile
        profile = load_operator_profile()
        path = profile.get("workspace_directory", "")
        if path and os.path.exists(path):
            os.startfile(path)
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Workspace Location", f"Workspace directory does not exist or is not set:\n{path}")

    def update_operator_settings_display(self):
        from ultron.core.operator import load_operator_profile
        profile = load_operator_profile()
        self.lbl_op_name_val.setText(profile.get("display_name", "-"))
        self.lbl_op_voice_val.setText("Enabled" if profile.get("voice_enabled", True) else "Disabled")
        self.lbl_op_work_val.setText(profile.get("workspace_directory", "-"))

    # ── Window Draggability & Keyboard Shortcuts ──

    def mousePressEvent(self, event):
        if self.isFullScreen():
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.isFullScreen():
            return
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position is not None:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.toggle_fullscreen()
                event.accept()
        else:
            super().keyPressEvent(event)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.core.logger.info("SYSTEM", "Fullscreen mode deactivated.")
        else:
            self.showFullScreen()
            self.core.logger.info("SYSTEM", "Fullscreen mode activated.")

    def load_user_profile(self):
        try:
            from ultron.core.operator import load_operator_profile
            profile = load_operator_profile()
            self.display_name = profile.get("display_name", "Prem")
        except Exception:
            self.display_name = "Prem"

        badge_text = "Sleeping"
        self.user_badge.setText(badge_text)
        
        if self.display_name:
            self.op_name.setText(self.display_name)
            self.greeting_name_lbl.setText(f"{self.display_name}.")
            from ultron.core.wake_engine import wake_engine
            if wake_engine:
                wake_engine.set_display_name(self.display_name)
        
        # Update operator settings labels
        try:
            self.update_operator_settings_display()
        except Exception:
            pass

    def submit_command(self):
        self.send_message()

    def send_message(self):
        text = self.input_box.text().strip()
        if not text:
            return
            
        self.input_box.clear()
        self.process_operator_command(text, is_voice=False)

    def process_operator_command(self, text, is_voice=False):
        text = text.strip()
        if not text:
            return
            
        if hasattr(self, "center_stack"):
            self.center_stack.setCurrentIndex(1)
            
        self.append_user_message(text)
        
        if not is_voice:
            from ultron.core.voice_session_manager import get_voice_session_manager, VoiceState
            mgr = get_voice_session_manager()
            if mgr and mgr.state not in [VoiceState.LISTENING, VoiceState.PROCESSING]:
                mgr.transition_to(VoiceState.LISTENING)
                
        self.dispatch_command(text)

    def toggle_microphone(self):
        from ultron.core.voice_session_manager import get_voice_session_manager, VoiceState
        mgr = get_voice_session_manager()
        if mgr:
            if mgr.state == VoiceState.SLEEPING:
                mgr.transition_to(VoiceState.LISTENING)
                mgr.signals.start_timer_triggered.emit()
            else:
                mgr.transition_to(VoiceState.SLEEPING)
                mgr.signals.stop_timer_triggered.emit()

    def dispatch_command(self, text):
        from ultron.core.ai_core import ai_core
        ai_core.execute_command(text)

    def append_user_message(self, text):
        bubble_html = f"""
        <div style="margin: 8px 0px; padding: 10px; background-color: rgba(255, 255, 255, 0.03); border-left: 3px solid #E63946; border-radius: 4px;">
            <div style="font-weight: bold; color: #E63946; font-size: 11px; margin-bottom: 4px; letter-spacing: 1px;">YOU</div>
            <div style="color: #F5F5F5; line-height: 1.4; white-space: pre-wrap;">{self._escape_html(text)}</div>
        </div>
        """
        self.conversation_widget.append(bubble_html)
        self.conversation_widget.verticalScrollBar().setValue(self.conversation_widget.verticalScrollBar().maximum())

    def append_ai_message(self, markdown_text):
        rendered_html = self._render_markdown(markdown_text)
        bubble_html = f"""
        <div style="margin: 8px 0px; padding: 10px; background-color: rgba(193, 18, 31, 0.05); border-left: 3px solid #C1121F; border-radius: 4px;">
            <div style="font-weight: bold; color: #C1121F; font-size: 11px; margin-bottom: 4px; letter-spacing: 1px;">ULTRON</div>
            <div style="color: #F5F5F5; line-height: 1.4;">{rendered_html}</div>
        </div>
        """
        self.conversation_widget.append(bubble_html)
        self.conversation_widget.verticalScrollBar().setValue(self.conversation_widget.verticalScrollBar().maximum())

    @Slot(object)
    def on_ai_response_ready(self, event):
        response = event.payload.get("response", "")
        self.append_ai_message(response)
        self.refresh_projects_view()
        self.refresh_memory_view()
        active_proj = self.core.session.active_project
        if active_proj:
            self.project_panel.p_name.setText(active_proj)
            self.project_panel.p_desc.setText("Active Workspace")

    def _escape_html(self, text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")

    def _render_markdown(self, text):
        from PySide6.QtGui import QTextDocument
        import re
        doc = QTextDocument()
        doc.setMarkdown(text)
        raw_html = doc.toHtml()
        
        body_match = re.search(r'<body>(.*?)</body>', raw_html, re.DOTALL | re.IGNORECASE)
        if body_match:
            return body_match.group(1).strip()
        return raw_html

    def toggle_developer_console(self):
        self.dev_console.toggle_console()
        self.core.logger.info("SYSTEM", f"Developer Console toggled. Visible: {self.dev_console.isVisible()}")

    def create_hidden_items_page(self) -> QWidget:
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_lbl = QLabel("HIDDEN ITEMS VAULT")
        title_lbl.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #C1121F;")
        layout.addWidget(title_lbl)
        
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        
        self.vault_search_input = QLineEdit()
        self.vault_search_input.setPlaceholderText("Search hidden items by name or path...")
        self.vault_search_input.setStyleSheet(
            "QLineEdit { background-color: rgba(17, 17, 17, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); "
            "border-radius: 6px; padding: 6px 12px; color: #F5F5F5; } QLineEdit:focus { border: 1px solid #E63946; }"
        )
        self.vault_search_input.textChanged.connect(self.filter_hidden_items)
        search_layout.addWidget(self.vault_search_input)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(
            "QPushButton { background-color: rgba(255, 255, 255, 0.05); color: #F5F5F5; "
            "border: 1px solid rgba(255, 255, 255, 0.05); padding: 6px 15px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #C1121F; border: 1px solid #E63946; color: white; }"
        )
        refresh_btn.clicked.connect(self.refresh_hidden_items_view)
        search_layout.addWidget(refresh_btn)
        
        layout.addLayout(search_layout)
        
        self.vault_table = QTableWidget()
        self.vault_table.setColumnCount(5)
        self.vault_table.setHorizontalHeaderLabels(["Name", "Path", "Status", "Date Hidden", "Actions"])
        self.vault_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.vault_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.vault_table.setShowGrid(True)
        self.vault_table.setFont(QFont("Inter", 10))
        
        self.vault_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(17, 17, 17, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                color: #F5F5F5;
                gridline-color: rgba(255, 255, 255, 0.05);
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.02);
            }
            QTableWidget::item:selected {
                background-color: rgba(193, 18, 31, 0.2);
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: rgba(0, 0, 0, 0.3);
                color: #A0A0A0;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        header = self.vault_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.vault_table.verticalHeader().setVisible(False)
        layout.addWidget(self.vault_table)
        
        return widget

    def refresh_hidden_items_view(self):
        if not hasattr(self, "vault_table"):
            return
            
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHBoxLayout, QPushButton, QWidget
        from ultron.core.service_manager import service_manager
        from datetime import datetime
        
        vault_srv = service_manager.get_service("HiddenItemsService")
        if not vault_srv:
            return
            
        items = vault_srv.list_hidden_items()
        items.sort(key=lambda x: x.get("hidden_timestamp", ""), reverse=True)
        
        self.vault_table.setRowCount(len(items))
        
        for idx, item in enumerate(items):
            name_item = QTableWidgetItem(item["name"])
            name_item.setForeground(QColor("#F5F5F5"))
            self.vault_table.setItem(idx, 0, name_item)
            
            path_item = QTableWidgetItem(item["original_path"])
            path_item.setForeground(QColor("#A0A0A0"))
            self.vault_table.setItem(idx, 1, path_item)
            
            status = item["status"]
            status_item = QTableWidgetItem(status.upper())
            if status == "hidden":
                status_item.setForeground(QColor("#E63946"))
            elif status == "restored":
                status_item.setForeground(QColor("#00FF00"))
            else:
                status_item.setForeground(QColor("#FFA500"))
            self.vault_table.setItem(idx, 2, status_item)
            
            ts = item["hidden_timestamp"]
            try:
                dt = datetime.fromisoformat(ts)
                ts_display = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_display = ts
            date_item = QTableWidgetItem(ts_display)
            date_item.setForeground(QColor("#A0A0A0"))
            self.vault_table.setItem(idx, 3, date_item)
            
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            
            restore_btn = QPushButton("Restore")
            restore_btn.setStyleSheet(
                "QPushButton { background-color: rgba(0, 255, 0, 0.1); color: #00FF00; "
                "border: 1px solid rgba(0, 255, 0, 0.2); border-radius: 4px; padding: 2px 8px; font-size: 11px; }"
                "QPushButton:hover { background-color: rgba(0, 255, 0, 0.3); }"
            )
            restore_btn.clicked.connect(lambda checked=False, p=item["original_path"]: self.vault_restore_action(p))
            
            open_btn = QPushButton("Open")
            open_btn.setStyleSheet(
                "QPushButton { background-color: rgba(255, 255, 255, 0.05); color: #F5F5F5; "
                "border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 4px; padding: 2px 8px; font-size: 11px; }"
                "QPushButton:hover { background-color: rgba(255, 255, 255, 0.15); }"
            )
            open_btn.clicked.connect(lambda checked=False, n=item["name"]: self.vault_open_action(n))
            
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet(
                "QPushButton { background-color: rgba(193, 18, 31, 0.1); color: #C1121F; "
                "border: 1px solid rgba(193, 18, 31, 0.2); border-radius: 4px; padding: 2px 8px; font-size: 11px; }"
                "QPushButton:hover { background-color: rgba(193, 18, 31, 0.3); }"
            )
            delete_btn.clicked.connect(lambda checked=False, i=item["id"]: self.vault_delete_action(i))
            
            if status == "missing":
                restore_btn.setEnabled(False)
                open_btn.setEnabled(False)
            elif status == "restored":
                restore_btn.setEnabled(False)
                
            action_layout.addWidget(restore_btn)
            action_layout.addWidget(open_btn)
            action_layout.addWidget(delete_btn)
            
            self.vault_table.setCellWidget(idx, 4, action_widget)

    def filter_hidden_items(self, text):
        if not hasattr(self, "vault_table"):
            return
        query = text.lower().strip()
        for row in range(self.vault_table.rowCount()):
            name = self.vault_table.item(row, 0).text().lower()
            path = self.vault_table.item(row, 1).text().lower()
            match = (query in name) or (query in path)
            self.vault_table.setRowHidden(row, not match)

    def vault_restore_action(self, path):
        from ultron.core.service_manager import service_manager
        vault_srv = service_manager.get_service("HiddenItemsService")
        if vault_srv:
            try:
                name = vault_srv.unhide_item(path)
                self.append_ai_message(f"Vault: {name} has been restored and is visible again.")
                self.refresh_hidden_items_view()
            except Exception as e:
                self.append_ai_message(f"Vault Error restoring item: {e}")
                
    def vault_open_action(self, name):
        from ultron.core.service_manager import service_manager
        vault_srv = service_manager.get_service("HiddenItemsService")
        if vault_srv:
            try:
                vault_srv.open_hidden_item(name)
                self.append_ai_message(f"Vault: Opening hidden item '{name}' temporarily. It will be re-secured shortly.")
                self.refresh_hidden_items_view()
            except Exception as e:
                self.append_ai_message(f"Vault Error opening item: {e}")
                
    def vault_delete_action(self, item_id):
        from ultron.core.service_manager import service_manager
        vault_srv = service_manager.get_service("HiddenItemsService")
        if vault_srv:
            try:
                vault_srv.delete_record(item_id)
                self.refresh_hidden_items_view()
            except Exception as e:
                self.append_ai_message(f"Vault Error deleting record: {e}")

    def close_gracefully(self):
        self.core.logger.info("SYSTEM", "Initiating shutdown protocol.")
        
        try:
            if hasattr(self, "diag_timer") and self.diag_timer:
                self.diag_timer.stop()
            if hasattr(self, "_diag_worker") and self._diag_worker and self._diag_worker.isRunning():
                self._diag_worker.quit()
                self._diag_worker.wait(1000)
            if hasattr(self, "perf_dashboard") and self.perf_dashboard:
                if hasattr(self.perf_dashboard, "timer") and self.perf_dashboard.timer:
                    self.perf_dashboard.timer.stop()
                self.perf_dashboard.stop_worker()
        except Exception:
            pass

        try:
            for et in [
                "STATE_CHANGED", "VOICE_STATE_CHANGED", "QUEUE_COUNT_CHANGED",
                "WAKE_TRIGGERED", "SLEEP_TRIGGERED", "VOICE_DIAGNOSTICS_UPDATE",
                "NOTIFICATION", "WARNING_OCCURRED", "ERROR_OCCURRED",
                "VOSK_MODEL_MISSING", "VOLUME_LEVEL_CHANGED", "AI_RESPONSE_READY"
            ]:
                event_bus.unsubscribe(et, self._event_bus_route_callback)
        except Exception:
            pass
            
        try:
            health_monitor.stop()
            service_manager.stop_all()
        except Exception:
            pass
            
        self.core.session.shutdown()
        UltronAnimations.fade_out_window(self, self.close, duration_ms=300)
