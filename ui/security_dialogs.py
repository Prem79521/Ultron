"""
ULTRON Custom Security Dialogue — Prompts for operator confirmation on sensitive actions.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon
from ui.themes import UltronThemeStyles, UltronColors

class UltronSecurityDialog(QDialog):
    """Frameless custom styled confirmation panel for file deletion or script running."""
    def __init__(self, action_type: str, description: str, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.description = description
        self.approved = False
        self._init_ui()

    def _init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.resize(400, 200)
        self.setStyleSheet(UltronThemeStyles.get_application_stylesheet())
        self.setWindowIcon(QIcon("assets/icons/ultron.ico"))

        # Center on parent or screen
        if self.parentWidget():
            parent_geom = self.parentWidget().geometry()
            self.move(parent_geom.x() + (parent_geom.width() - self.width()) // 2,
                      parent_geom.y() + (parent_geom.height() - self.height()) // 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Warning
        header = QLabel("SECURITY CLEARANCE REQUESTED")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: rgb(220, 20, 20); letter-spacing: 1px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Action type
        act_lbl = QLabel(f"ACTION: {self.action_type.upper()}")
        act_lbl.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        act_lbl.setStyleSheet("color: rgb(200, 200, 200);")
        act_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(act_lbl)

        # Description
        desc_lbl = QLabel(self.description)
        desc_lbl.setFont(QFont("Segoe UI", 9))
        desc_lbl.setStyleSheet("color: rgb(150, 150, 150);")
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_lbl)

        layout.addSpacing(15)

        # Choice buttons
        btn_layout = QHBoxLayout()
        
        allow_btn = QPushButton("ALLOW ACTION")
        allow_btn.setObjectName("ActionButton")
        allow_btn.setFixedHeight(35)
        allow_btn.clicked.connect(self.on_allow)
        btn_layout.addWidget(allow_btn)

        deny_btn = QPushButton("DENY ACTION")
        deny_btn.setObjectName("ActionButton")
        # Change deny style slightly
        deny_btn.setStyleSheet("background-color: rgb(40, 0, 0); color: rgb(200, 50, 50); border: 1px solid rgb(220, 20, 20);")
        deny_btn.setFixedHeight(35)
        deny_btn.clicked.connect(self.on_deny)
        btn_layout.addWidget(deny_btn)

        layout.addLayout(btn_layout)

    def on_allow(self):
        self.approved = True
        self.accept()

    def on_deny(self):
        self.approved = False
        self.reject()
