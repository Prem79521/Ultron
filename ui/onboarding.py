import os
import sys
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QRadioButton, QButtonGroup, QFileDialog
)
from PySide6.QtCore import Qt, QPoint, QVariantAnimation, QEasingCurve, Slot, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from ultron.core.operator import save_operator_profile, load_operator_profile

class UltronCheckmark(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 120)
        self.anim_val = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(1200)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self.on_anim_val)
        
    def start(self):
        self.anim.start()
        
    def on_anim_val(self, val):
        self.anim_val = val
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(15, 15, -15, -15)
        center = rect.center()
        r = min(rect.width(), rect.height()) / 2
        
        # 1. Pulsing glowing red circle background
        glow_opacity = int(45 * self.anim_val)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(193, 18, 31, glow_opacity))
        painter.drawEllipse(center, r * (0.85 + 0.15 * self.anim_val), r * (0.85 + 0.15 * self.anim_val))
        
        # 2. Circle outline drawing animation
        pen = QPen(QColor("#C1121F"), 3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, 90 * 16, int(-360 * 16 * self.anim_val))
        
        # 3. Animate drawing the checkmark path
        if self.anim_val > 0.4:
            check_val = (self.anim_val - 0.4) / 0.6
            pen.setWidth(4)
            pen.setColor(QColor("#F5F5F5"))
            painter.setPen(pen)
            
            p1 = QPointF(center.x() - 18, center.y())
            p2 = QPointF(center.x() - 6, center.y() + 12)
            p3 = QPointF(center.x() + 20, center.y() - 14)
            
            # Animate first line segment (p1 to p2)
            if check_val <= 0.4:
                seg_val = check_val / 0.4
                mid_p = p1 + (p2 - p1) * seg_val
                painter.drawLine(p1, mid_p)
            else:
                # First segment complete, draw second segment (p2 to p3)
                painter.drawLine(p1, p2)
                seg_val = (check_val - 0.4) / 0.6
                end_p = p2 + (p3 - p2) * seg_val
                painter.drawLine(p2, end_p)

class OperatorOnboardingWizard(QDialog):
    onboarding_complete = Signal()
    
    def __init__(self, core_system, memory_manager, voice_provider, skills_registry, parent=None):
        super().__init__(parent)
        self.core = core_system
        self.memory = memory_manager
        self.voice = voice_provider
        self.skills = skills_registry
        
        # Window attributes
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(800, 520)
        self._drag_pos = None
        
        # Form values variables
        self.display_name = ""
        self.voice_enabled = True
        self.workspace_directory = os.path.join(os.path.expanduser("~"), "Documents", "ULTRON Projects").replace("\\", "/")
        
        self.init_ui()
        
    def init_ui(self):
        # Outer layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main container with rounded corners (holds everything)
        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: #090909;
                border: 1px solid rgba(193, 18, 31, 0.4);
                border-radius: 18px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. Custom Sleek Titlebar
        titlebar = QHBoxLayout()
        titlebar.setContentsMargins(10, 5, 10, 5)
        
        title_lbl = QLabel("ULTRON // COGNITIVE OS PERSONALIZATION")
        title_lbl.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: rgba(193, 18, 31, 0.9); letter-spacing: 2px;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #A0A0A0;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #C1121F;
                background-color: rgba(193, 18, 31, 0.1);
                border-radius: 14px;
            }
        """)
        close_btn.clicked.connect(sys.exit) # Closing exits the app entirely
        
        titlebar.addWidget(title_lbl)
        titlebar.addStretch()
        titlebar.addWidget(close_btn)
        container_layout.addLayout(titlebar)
        
        # Divider line
        div = QWidget()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.05);")
        container_layout.addWidget(div)
        container_layout.addSpacing(15)
        
        # 2. QStackedWidget for wizard pages
        self.stack = QStackedWidget()
        self.create_pages()
        container_layout.addWidget(self.stack)
        
        # Divider line
        div2 = QWidget()
        div2.setFixedHeight(1)
        div2.setStyleSheet("background-color: rgba(255, 255, 255, 0.05);")
        container_layout.addWidget(div2)
        container_layout.addSpacing(15)
        
        # 3. Bottom Navigation layout
        bottom_nav = QHBoxLayout()
        bottom_nav.setContentsMargins(10, 0, 10, 10)
        
        self.back_btn = QPushButton("← Back")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #A0A0A0;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #F5F5F5;
                background-color: rgba(255,255,255,0.05);
            }
        """)
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.hide() # Hidden on page 1
        
        # Page indicator dots
        self.dots_layout = QHBoxLayout()
        self.dots_layout.setSpacing(8)
        self.dots = []
        for i in range(5):
            dot = QWidget()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet("background-color: #444444; border-radius: 4px;")
            self.dots_layout.addWidget(dot)
            self.dots.append(dot)
        self.update_dots(0)
        
        self.next_btn = QPushButton("Begin →")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #C1121F;
                color: #F5F5F5;
                border: 1px solid #C1121F;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E63946;
                border-color: #E63946;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
                border-color: #333333;
            }
        """)
        self.next_btn.clicked.connect(self.go_next)
        
        bottom_nav.addWidget(self.back_btn)
        bottom_nav.addStretch()
        bottom_nav.addLayout(self.dots_layout)
        bottom_nav.addStretch()
        bottom_nav.addWidget(self.next_btn)
        container_layout.addLayout(bottom_nav)
        
        outer_layout.addWidget(self.container)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw translucent shadow glow around window
        shadow_rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setBrush(QColor("#090909"))
        painter.setPen(QPen(QColor("rgba(193, 18, 31, 0.45)"), 1.5))
        painter.drawRoundedRect(shadow_rect, 18, 18)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def update_dots(self, active_index):
        for idx, dot in enumerate(self.dots):
            if idx == active_index:
                dot.setStyleSheet("background-color: #C1121F; border-radius: 4px;")
            else:
                dot.setStyleSheet("background-color: #444444; border-radius: 4px;")

    def create_pages(self):
        # PAGE 1: Welcome
        p1 = QWidget()
        p1_layout = QVBoxLayout(p1)
        p1_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo = QLabel("◉")
        logo.setFont(QFont("Inter", 64))
        logo.setStyleSheet("color: #C1121F; padding-bottom: 10px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("WELCOME TO ULTRON")
        title.setFont(QFont("Inter", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #F5F5F5; letter-spacing: 2px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sub = QLabel("Before we begin, let's personalize your Cognitive Operating System.")
        sub.setFont(QFont("Inter", 12))
        sub.setStyleSheet("color: #A0A0A0; margin-top: 10px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        p1_layout.addWidget(logo)
        p1_layout.addWidget(title)
        p1_layout.addWidget(sub)
        self.stack.addWidget(p1)
        
        # PAGE 2: Operator Identity
        p2 = QWidget()
        p2_layout = QVBoxLayout(p2)
        p2_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p2_layout.setSpacing(15)
        
        title2 = QLabel("Operator Identification")
        title2.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title2.setStyleSheet("color: #C1121F;")
        title2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        prompt = QLabel("What should I call you?")
        prompt.setFont(QFont("Inter", 12))
        prompt.setStyleSheet("color: #F5F5F5;")
        prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your preferred name...")
        self.name_input.setFont(QFont("Inter", 14))
        self.name_input.setFixedWidth(400)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #111111;
                color: #F5F5F5;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
            }
            QLineEdit:focus {
                border: 1.5px solid #C1121F;
                background-color: #151515;
            }
        """)
        self.name_input.textChanged.connect(self.validate_name)
        
        p2_layout.addWidget(title2)
        p2_layout.addWidget(prompt)
        p2_layout.addWidget(self.name_input)
        self.stack.addWidget(p2)
        
        # PAGE 3: Voice Configuration
        p3 = QWidget()
        p3_layout = QVBoxLayout(p3)
        p3_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p3_layout.setSpacing(15)
        
        title3 = QLabel("Voice Interaction")
        title3.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title3.setStyleSheet("color: #C1121F;")
        title3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        quest = QLabel("Would you like voice control enabled?")
        quest.setFont(QFont("Inter", 12))
        quest.setStyleSheet("color: #F5F5F5;")
        quest.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        radio_box = QWidget()
        radio_layout = QVBoxLayout(radio_box)
        radio_layout.setSpacing(10)
        
        self.r_enable = QRadioButton("Enable Voice")
        self.r_enable.setFont(QFont("Inter", 11))
        self.r_enable.setStyleSheet("color: #F5F5F5; spacing: 8px;")
        self.r_enable.setChecked(True)
        
        self.r_disable = QRadioButton("Disable Voice")
        self.r_disable.setFont(QFont("Inter", 11))
        self.r_disable.setStyleSheet("color: #F5F5F5; spacing: 8px;")
        
        self.bg_voice = QButtonGroup(self)
        self.bg_voice.addButton(self.r_enable)
        self.bg_voice.addButton(self.r_disable)
        
        radio_layout.addWidget(self.r_enable)
        radio_layout.addWidget(self.r_disable)
        
        desc = QLabel("Voice can be enabled or changed later in Settings.")
        desc.setFont(QFont("Inter", 10))
        desc.setStyleSheet("color: #808080;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        p3_layout.addWidget(title3)
        p3_layout.addWidget(quest)
        p3_layout.addWidget(radio_box)
        p3_layout.addWidget(desc)
        self.stack.addWidget(p3)
        
        # PAGE 4: Workspace Location
        p4 = QWidget()
        p4_layout = QVBoxLayout(p4)
        p4_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p4_layout.setSpacing(15)
        
        title4 = QLabel("Workspace Location")
        title4.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title4.setStyleSheet("color: #C1121F;")
        title4.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        explanation = QLabel("Choose where ULTRON should create and manage your projects.")
        explanation.setFont(QFont("Inter", 12))
        explanation.setStyleSheet("color: #A0A0A0;")
        explanation.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        browser_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(self.workspace_directory)
        self.path_input.setFont(QFont("Inter", 11))
        self.path_input.setFixedWidth(380)
        self.path_input.setStyleSheet("""
            QLineEdit {
                background-color: #111111;
                color: #F5F5F5;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #F5F5F5;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        browse_btn.clicked.connect(self.browse_workspace)
        
        browser_layout.addWidget(self.path_input)
        browser_layout.addWidget(browse_btn)
        
        change_later = QLabel("This can be changed later.")
        change_later.setFont(QFont("Inter", 10))
        change_later.setStyleSheet("color: #808080;")
        change_later.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        p4_layout.addWidget(title4)
        p4_layout.addWidget(explanation)
        p4_layout.addLayout(browser_layout)
        p4_layout.addWidget(change_later)
        self.stack.addWidget(p4)
        
        # PAGE 5: Finish
        p5 = QWidget()
        p5_layout = QVBoxLayout(p5)
        p5_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p5_layout.setSpacing(15)
        
        title5 = QLabel("Setup Complete")
        title5.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        title5.setStyleSheet("color: #C1121F;")
        title5.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.welcome_lbl = QLabel("Welcome.")
        self.welcome_lbl.setFont(QFont("Inter", 14))
        self.welcome_lbl.setStyleSheet("color: #F5F5F5;")
        self.welcome_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ready_lbl = QLabel("Your Cognitive Operating System is now ready.")
        ready_lbl.setFont(QFont("Inter", 11))
        ready_lbl.setStyleSheet("color: #A0A0A0;")
        ready_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.checkmark = UltronCheckmark(self)
        
        launch_btn = QPushButton("Launch ULTRON")
        launch_btn.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        launch_btn.setFixedWidth(240)
        launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #C1121F;
                color: #F5F5F5;
                border: 1px solid #C1121F;
                border-radius: 8px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #E63946;
                border-color: #E63946;
            }
        """)
        launch_btn.clicked.connect(self.finish_onboarding)
        
        p5_layout.addWidget(title5)
        p5_layout.addWidget(self.welcome_lbl)
        p5_layout.addWidget(ready_lbl)
        p5_layout.addWidget(self.checkmark)
        p5_layout.addWidget(launch_btn)
        self.stack.addWidget(p5)

    def validate_name(self):
        name = self.name_input.text().strip()
        is_valid = len(name) >= 2 and len(name) <= 40
        self.next_btn.setEnabled(is_valid)

    def browse_workspace(self):
        curr = self.path_input.text() or os.path.expanduser("~")
        dir_path = QFileDialog.getExistingDirectory(self, "Select Project Workspace Location", curr)
        if dir_path:
            self.workspace_directory = dir_path.replace("\\", "/")
            self.path_input.setText(self.workspace_directory)

    def go_back(self):
        curr = self.stack.currentIndex()
        if curr > 0:
            self.stack.setCurrentIndex(curr - 1)
            self.update_dots(curr - 1)
            
            # Button modifications
            if curr - 1 == 0:
                self.back_btn.hide()
                self.next_btn.setText("Begin →")
            else:
                self.back_btn.show()
                self.next_btn.setText("Next →")
                self.next_btn.show()
            self.next_btn.setEnabled(True)

    def go_next(self):
        curr = self.stack.currentIndex()
        if curr == 0:
            self.stack.setCurrentIndex(1)
            self.update_dots(1)
            self.back_btn.show()
            self.next_btn.setText("Next →")
            self.validate_name()
        elif curr == 1:
            self.display_name = self.name_input.text().strip()
            self.stack.setCurrentIndex(2)
            self.update_dots(2)
        elif curr == 2:
            self.voice_enabled = self.r_enable.isChecked()
            self.stack.setCurrentIndex(3)
            self.update_dots(3)
        elif curr == 3:
            self.workspace_directory = self.path_input.text().strip().replace("\\", "/")
            self.welcome_lbl.setText(f"Welcome, {self.display_name}.")
            self.stack.setCurrentIndex(4)
            self.update_dots(4)
            self.back_btn.hide()
            self.next_btn.hide()
            self.checkmark.start()

    def finish_onboarding(self):
        save_operator_profile(self.display_name, self.voice_enabled, self.workspace_directory)
        self.onboarding_complete.emit()
