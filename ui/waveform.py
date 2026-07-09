"""
ULTRON Waveform Visualizer — Custom painted glowing scarlet waveform reflecting runtime states.
"""

import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtCore import QTimer, Qt, Slot

class UltronWaveform(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0.0
        self.amplitude = 2.0
        self.frequency = 0.05
        self.target_amplitude = 2.0
        self.target_frequency = 0.05
        self.state = "idle"  # idle, listening, thinking, speaking
        
        # Setup animation refresh timer (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_wave)
        self.timer.start(16)

    def set_state(self, state: str):
        self.state = state.lower()
        if self.state == "speaking":
            self.target_amplitude = 25.0
            self.target_frequency = 0.15
        elif self.state == "thinking":
            self.target_amplitude = 8.0
            self.target_frequency = 0.08
        elif self.state == "listening":
            self.target_amplitude = 12.0
            self.target_frequency = 0.18
        elif self.state == "executing":
            self.target_amplitude = 18.0
            self.target_frequency = 0.22
        else:  # idle / booting
            self.target_amplitude = 2.0
            self.target_frequency = 0.04


    @Slot()
    def animate_wave(self):
        # Smoothly interpolate amplitude and frequency values
        self.amplitude += (self.target_amplitude - self.amplitude) * 0.1
        self.frequency += (self.target_frequency - self.frequency) * 0.1
        
        # Advance phase
        self.phase += self.frequency
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        mid_y = height / 2
        
        # Draw central waveform background line
        painter.setPen(QPen(QColor(40, 20, 20), 1, Qt.PenStyle.SolidLine))
        painter.drawLine(0, mid_y, width, mid_y)
        
        # Draw glowing path
        # Multi-pass painting creates a soft neon glow
        glow_colors = [
            QColor(220, 20, 20, 40),  # Outer soft glow
            QColor(220, 20, 20, 90),  # Inner glow
            QColor(255, 255, 255, 220) # Core bright line
        ]
        pen_widths = [8, 4, 1.5]
        
        for color, thickness in zip(glow_colors, pen_widths):
            painter.setPen(QPen(color, thickness, Qt.PenStyle.SolidLine))
            
            # Construct sine wave path
            points = []
            for x in range(0, width, 2):
                # Apply envelope constraint so wave tapers off at the edges
                envelope = math.sin((x / width) * math.pi)
                
                # Composite wave function
                y = mid_y + (self.amplitude * envelope * math.sin(x * 0.02 + self.phase))
                
                # Add complex harmonic jitter when thinking or listening
                if self.state in ["thinking", "listening"]:
                    y += (self.amplitude * 0.2 * envelope * math.sin(x * 0.08 - self.phase * 2))
                    
                points.append((x, y))
                
            # Draw point-to-point lines
            for i in range(len(points) - 1):
                p1 = points[i]
                p2 = points[i+1]
                painter.drawLine(p1[0], p1[1], p2[0], p2[1])
