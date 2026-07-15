"""
ULTRON Waveform Visualizer — Premium custom painted HUD with concentric circles, particle drift, and multi-layered glowing waveforms.
"""

import math
import random
import time
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QConicalGradient, QRadialGradient
from PySide6.QtCore import QTimer, Qt, Slot

class UltronWaveform(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0.0
        self.amplitude = 4.0
        self.frequency = 0.03
        self.target_amplitude = 4.0
        self.target_frequency = 0.03
        self.state = "sleeping"  # sleeping, listening, thinking, speaking
        
        # Particle field for background stars
        self.particles = []
        for _ in range(25):
            self.particles.append({
                "x": random.uniform(0.0, 1.0),
                "y": random.uniform(0.0, 1.0),
                "speed": random.uniform(0.0005, 0.0015),
                "size": random.uniform(1.0, 2.0),
                "brightness": random.uniform(30, 120)
            })

        self.scan_pos = 0.0
        self.scan_dir = 1.0

        # Setup animation refresh timer (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_wave)
        self.timer.start(16)

    def set_state(self, state: str):
        self.state = state.lower()
        if self.state == "speaking":
            self.target_amplitude = 40.0
            self.target_frequency = 0.16
        elif self.state == "thinking":
            self.target_amplitude = 8.0
            self.target_frequency = 0.06
        elif self.state == "listening":
            self.target_amplitude = 24.0
            self.target_frequency = 0.18
        elif self.state == "executing":
            self.target_amplitude = 18.0
            self.target_frequency = 0.14
        else:  # sleeping / idle
            self.target_amplitude = 4.0
            self.target_frequency = 0.02

    @Slot()
    def animate_wave(self):
        # Smooth interpolation using 200ms factor (~0.12 step)
        self.amplitude += (self.target_amplitude - self.amplitude) * 0.12
        self.frequency += (self.target_frequency - self.frequency) * 0.12
        self.phase += self.frequency

        # Update particles
        for p in self.particles:
            p["x"] -= p["speed"]
            if p["x"] < 0:
                p["x"] = 1.0
                p["y"] = random.uniform(0.0, 1.0)
            p["brightness"] = 60 + 50 * math.sin(time.time() * 3 + p["x"] * 10)

        # Update scan line
        self.scan_pos += 0.004 * self.scan_dir
        if self.scan_pos > 1.0:
            self.scan_pos = 1.0
            self.scan_dir = -1.0
        elif self.scan_pos < 0.0:
            self.scan_pos = 0.0
            self.scan_dir = 1.0

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        mid_x = width / 2
        mid_y = height / 2

        # ── 1. DRAW BACKGROUND CONCENTRIC CIRCLES (Radar Background reduced by 60%) ──
        painter.setBrush(Qt.BrushStyle.NoBrush)
        max_r = min(width, height) / 2
        circle_opacity = 8 # reduced by 60% from 20
        for r_factor in [0.35, 0.55, 0.75, 0.95]:
            r = max_r * r_factor
            painter.setPen(QPen(QColor(193, 18, 31, circle_opacity), 1, Qt.PenStyle.SolidLine))
            painter.drawEllipse(mid_x - r, mid_y - r, r * 2, r * 2)

        # ── 2. DRAW PARTICLE FIELD / STARS ──
        for p in self.particles:
            px = p["x"] * width
            py = p["y"] * height
            color = QColor(245, 245, 245, int(p["brightness"] * 0.6))
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(px - p["size"]/2, py - p["size"]/2, p["size"], p["size"])

        # ── 3. DRAW LIGHT SCANNING EFFECT ──
        scan_y = self.scan_pos * height
        scan_gradient = QRadialGradient(mid_x, scan_y, width * 0.4)
        scan_gradient.setColorAt(0.0, QColor(193, 18, 31, 15))
        scan_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(scan_gradient))
        painter.drawRect(0, 0, width, height)

        # ── 4. DRAW CENTRAL WAVELINE BACKGROUND ──
        painter.setPen(QPen(QColor(139, 0, 0, 20), 1, Qt.PenStyle.SolidLine))
        painter.drawLine(0, mid_y, width, mid_y)

        # ── 5. DRAW MULTI-LAYERED SINE WAVEFORMS WITH GLOW ──
        # Dynamic styling according to AI state:
        # Sleeping: Dim waveform, Status = Sleeping
        # Listening: Bright waveform, Radar pulses
        # Thinking: Thought stream animates, Wave slows
        # Speaking: Wave amplitude increases
        if self.state == "sleeping":
            wave_alpha_base = 60
            glow_opacity = 20
        elif self.state == "thinking":
            wave_alpha_base = 140
            glow_opacity = 40
        else: # listening / speaking
            wave_alpha_base = 220
            glow_opacity = 80

        wave_layers = [
            # Main wave
            {"amp_mult": 1.0, "freq_mult": 0.02, "phase_mult": 1.0, "color": QColor(230, 57, 70, wave_alpha_base), "width": 2.0},
            # Secondary wave (Scarlet Red)
            {"amp_mult": 0.5, "freq_mult": 0.035, "phase_mult": -1.3, "color": QColor(193, 18, 31, int(wave_alpha_base * 0.7)), "width": 1.5},
            # Core line (bright white)
            {"amp_mult": 0.25, "freq_mult": 0.05, "phase_mult": 1.8, "color": QColor(245, 245, 245, int(wave_alpha_base * 0.9)), "width": 1.0}
        ]

        # Draw soft outer glow first for each layer if state isn't sleeping
        if self.state != "sleeping":
            for layer in wave_layers:
                painter.setPen(QPen(QColor(230, 57, 70, glow_opacity), layer["width"] * 3.5, Qt.PenStyle.SolidLine))
                points = []
                for x in range(0, width + 5, 5):
                    envelope = math.sin((x / width) * math.pi)
                    y = mid_y + (self.amplitude * layer["amp_mult"] * envelope * math.sin(x * layer["freq_mult"] + self.phase * layer["phase_mult"]))
                    if self.state in ["thinking", "listening", "speaking"]:
                        y += (self.amplitude * 0.2 * envelope * math.cos(x * 0.08 - self.phase * 2.0))
                    points.append((x, y))
                for i in range(len(points) - 1):
                    painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

        # Draw actual sharp curves
        for layer in wave_layers:
            points = []
            for x in range(0, width + 4, 4):
                envelope = math.sin((x / width) * math.pi)
                y = mid_y + (self.amplitude * layer["amp_mult"] * envelope * math.sin(x * layer["freq_mult"] + self.phase * layer["phase_mult"]))
                if self.state in ["thinking", "listening", "speaking"]:
                    y += (self.amplitude * 0.2 * envelope * math.cos(x * 0.08 - self.phase * 2.0))
                points.append((x, y))
            
            painter.setPen(QPen(layer["color"], layer["width"], Qt.PenStyle.SolidLine))
            for i in range(len(points) - 1):
                p1 = points[i]
                p2 = points[i+1]
                painter.drawLine(p1[0], p1[1], p2[0], p2[1])
