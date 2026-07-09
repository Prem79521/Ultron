"""
ULTRON Hardware Permissions Dialogue — Prompts for device access consent on first-run.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QCheckBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from ui.themes import UltronThemeStyles, UltronColors

class UltronPermissionDialog(QDialog):
    """Dialogue checklist enabling custom selection of camera, microphone, and speaker."""
    def __init__(self, detected_devices: dict, parent=None):
        super().__init__(parent)
        self.detected = detected_devices
        # Result outputs
        self.granted = {"microphone": False, "speaker": False, "camera": False}
        self._init_ui()

    def _init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.resize(380, 320)
        self.setStyleSheet(UltronThemeStyles.get_application_stylesheet())
        self.setWindowIcon(QIcon("assets/icons/ultron.ico"))

        if self.parentWidget():
            parent_geom = self.parentWidget().geometry()
            self.move(parent_geom.x() + (parent_geom.width() - self.width()) // 2,
                      parent_geom.y() + (parent_geom.height() - self.height()) // 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)

        # Header Title
        title_lbl = QLabel("HARDWARE CONCENT DECLARATION")
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: rgb(220, 20, 20); letter-spacing: 1px;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)
        
        info_lbl = QLabel("Please configure which local hardware resources ULTRON is permitted to access.")
        info_lbl.setFont(QFont("Segoe UI", 9))
        info_lbl.setStyleSheet("color: rgb(130, 130, 130);")
        info_lbl.setWordWrap(True)
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_lbl)
        layout.addSpacing(15)

        # Checkboxes for Microphone, Speaker, Camera
        self.mic_cb = QCheckBox("Permit Microphone Access")
        self.mic_cb.setFont(QFont("Segoe UI", 10))
        self.mic_cb.setStyleSheet("color: rgb(220, 220, 220); padding: 5px;")
        self.mic_cb.setChecked(self.detected.get("microphone", False))
        layout.addWidget(self.mic_cb)

        self.spk_cb = QCheckBox("Permit Speaker Access (TTS)")
        self.spk_cb.setFont(QFont("Segoe UI", 10))
        self.spk_cb.setStyleSheet("color: rgb(220, 220, 220); padding: 5px;")
        self.spk_cb.setChecked(self.detected.get("speaker", False))
        layout.addWidget(self.spk_cb)

        self.cam_cb = QCheckBox("Permit Camera Access (Vision)")
        self.cam_cb.setFont(QFont("Segoe UI", 10))
        self.cam_cb.setStyleSheet("color: rgb(220, 220, 220); padding: 5px;")
        self.cam_cb.setChecked(self.detected.get("camera", False))
        layout.addWidget(self.cam_cb)

        layout.addSpacing(20)

        # Confirm Button
        confirm_btn = QPushButton("CONFIRM HARDWARE POLICY")
        confirm_btn.setObjectName("ActionButton")
        confirm_btn.setFixedHeight(38)
        confirm_btn.clicked.connect(self.on_confirm)
        layout.addWidget(confirm_btn)

    def on_confirm(self):
        self.granted["microphone"] = self.mic_cb.isChecked()
        self.granted["speaker"] = self.spk_cb.isChecked()
        self.granted["camera"] = self.cam_cb.isChecked()
        self.accept()
