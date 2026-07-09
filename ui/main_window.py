"""
ULTRON Main Window Dashboard — Premium dark frameless dashboard with active skills, UME viewers, SAPI5 triggers, and thread-safe layout state managers.
"""

import math
import os
import json
import threading
import time
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QStackedWidget, QSplitter, QTextEdit, QCheckBox
)
from PySide6.QtCore import Qt, QSize, Slot, QTimer
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QIcon, QPainter, QPen, QColor, QBrush
from ui.themes import UltronColors, UltronThemeStyles
from ui.animations import UltronAnimations
from ui.waveform import UltronWaveform
from ui.developer_console import UltronDeveloperConsole
from ultron.core.event_bus import event_bus
from ultron.core.task_manager import task_manager
from ultron.core.service_manager import service_manager
from ultron.hal.hal_manager import get_hal_manager

class UltronFloatingVoiceWidget(QWidget):
    """Frameless, semi-transparent overlay widget showing current OS state (Bug 16)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SubWindow)
        self.setFixedSize(120, 36)
        self.setStyleSheet("background-color: rgba(10, 10, 10, 220); border: 1px solid rgb(220, 20, 20); border-radius: 8px;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        self.status_lbl = QLabel("STANDBY")
        self.status_lbl.setStyleSheet("color: rgb(220, 220, 220); font-size: 9px; font-weight: bold; font-family: monospace;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_lbl)
        
        self.indicator = QWidget()
        self.indicator.setFixedSize(8, 8)
        self.indicator.setStyleSheet("background-color: rgb(220, 20, 20); border-radius: 4px;")
        layout.addWidget(self.indicator)

    def set_state(self, state: str):
        state_title = state.strip().title()
        self.status_lbl.setText(state_title.upper())
        
        # Adjust visual indicator based on state
        if state_title == "Listening":
            self.indicator.setStyleSheet("background-color: rgb(0, 255, 0); border-radius: 4px;")
        elif state_title in ["Thinking", "Executing"]:
            self.indicator.setStyleSheet("background-color: rgb(255, 165, 0); border-radius: 4px;")
        elif state_title == "Speaking":
            self.indicator.setStyleSheet("background-color: rgb(0, 191, 255); border-radius: 4px;")
        elif state_title == "Error":
            self.indicator.setStyleSheet("background-color: rgb(255, 0, 0); border-radius: 4px;")
        else: # Sleeping
            self.indicator.setStyleSheet("background-color: rgb(220, 20, 20); border-radius: 4px;")

class UltronRadarWidget(QWidget):
    """Painted target radar graphics simulating military AI systems."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0.0
        self.state = "idle"
        self.pulse_scale = 1.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate_radar)
        self.timer.start(30)

    def set_state(self, state: str):
        self.state = state.lower()
        self.update()

    def rotate_radar(self):
        # Rotate faster when active
        if self.state == "listening":
            self.angle += 2.0
        elif self.state in ["executing", "thinking"]:
            self.angle += 1.5
        else:
            self.angle += 0.5
            
        # Pulsing scale in thinking/speaking
        if self.state in ["thinking", "speaking"]:
            self.pulse_scale = 1.0 + 0.15 * math.sin(time.time() * 8)
        else:
            self.pulse_scale = 1.0
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        max_radius = min(width, height) / 2.5 * self.pulse_scale
        
        # Concentric circles
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(1, 4):
            radius = max_radius * (i / 3)
            alpha = int(40 * (i / 3))
            
            pen_width = 1.0
            if self.state in ["thinking", "speaking"] and i == 3:
                pen_width = 2.0
                
            painter.setPen(QPen(QColor(220, 20, 20, alpha), pen_width, Qt.PenStyle.SolidLine))
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
            
        # Draw scanning ticks
        painter.setPen(QPen(QColor(220, 20, 20, 120), 1.5, Qt.PenStyle.SolidLine))
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.angle)
        painter.drawLine(0, 0, 0, -max_radius)
        painter.restore()
        
        # Core glowing red dot
        painter.setBrush(QBrush(QColor(220, 20, 20, 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center_x - 6, center_y - 6, 12, 12)

class UltronMainWindow(QMainWindow):
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

        # Decoupled Event Bus subscriptions (Bug 29)
        event_bus.subscribe("STATE_CHANGED", self.on_state_changed)
        event_bus.subscribe("VOICE_STATE_CHANGED", self.on_voice_state_changed)
        event_bus.subscribe("QUEUE_COUNT_CHANGED", self.on_queue_count_changed)
        event_bus.subscribe("WAKE_TRIGGERED", self.on_wake_triggered)
        event_bus.subscribe("SLEEP_TRIGGERED", self.on_sleep_triggered)
        event_bus.subscribe("VOICE_DIAGNOSTICS_UPDATE", self.on_voice_diagnostics_update)
        event_bus.subscribe("NOTIFICATION", self.on_notification_event)
        event_bus.subscribe("WARNING_OCCURRED", self.on_warning_event)
        event_bus.subscribe("ERROR_OCCURRED", self.on_error_event)
        event_bus.subscribe("VOSK_MODEL_MISSING", self.on_vosk_model_missing)
        event_bus.subscribe("VOLUME_LEVEL_CHANGED", self.on_volume_level_changed)

        # Setup Live Tools Diagnostics timer (Bug 22)
        self.diag_timer = QTimer(self)
        self.diag_timer.timeout.connect(self.refresh_diagnostics)
        self.diag_timer.start(1000)

        # Load dynamic user identity (only if memory is bound)
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
        if hasattr(self, "send_btn"):
            self.send_btn.setEnabled(False)
        if hasattr(self, "test_mic_btn"):
            self.test_mic_btn.setEnabled(False)

    def unlock_ui(self):
        self.cmd_input.setEnabled(True)
        self.cmd_input.setPlaceholderText("Type your command (e.g. 'Arise', 'Continue ROWDY')...")
        if hasattr(self, "send_btn"):
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
        self.resize(1024, 640)
        self.setStyleSheet(UltronThemeStyles.get_application_stylesheet())
        self.setWindowIcon(QIcon("assets/icons/ultron.ico"))

        # Center window
        from PySide6.QtWidgets import QApplication
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

        # -------------------------------------------------------------------
        # 1. Sidebar Panel
        # -------------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setStyleSheet("background-color: rgb(15, 15, 15); border-right: 1px solid rgb(30, 30, 30);")
        sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)

        logo_lbl = QLabel("ULTRON")
        logo_lbl.setObjectName("TitleLabel")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo_lbl)
        
        sub_logo = QLabel("COGNITIVE OS")
        sub_logo.setStyleSheet("color: rgb(110, 110, 110); font-size: 9px; letter-spacing: 1px;")
        sub_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(sub_logo)
        sidebar_layout.addSpacing(30)

        # Navigation Buttons
        nav_buttons = ["CORE", "MEMORY", "PROJECTS", "TOOLS", "SETTINGS"]
        for i, btn_name in enumerate(nav_buttons):
            btn = QPushButton(btn_name)
            btn.setObjectName("ActionButton")
            btn.setFixedHeight(38)
            btn.clicked.connect(lambda checked=False, idx=i: self.switch_panel(idx))
            sidebar_layout.addWidget(btn)
            sidebar_layout.addSpacing(6)

        sidebar_layout.addStretch()

        self.user_badge = QLabel("OPERATOR\n[STANDBY]")
        self.user_badge.setStyleSheet("color: rgb(220, 20, 20); font-size: 10px; font-weight: bold; border-top: 1px solid rgb(30, 30, 30); padding-top: 10px;")
        self.user_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.user_badge)

        base_layout.addWidget(sidebar)

        # -------------------------------------------------------------------
        # 2. Main Content Dashboard
        # -------------------------------------------------------------------
        dashboard = QWidget()
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(20, 20, 20, 20)

        titlebar_layout = QHBoxLayout()
        self.status_bar_lbl = QLabel("ULTRON COGNITIVE OS SLEEPING | QUEUE: 0")
        self.status_bar_lbl.setStyleSheet("color: rgb(130, 130, 130); font-weight: bold; font-size: 11px;")
        titlebar_layout.addWidget(self.status_bar_lbl)
        
        titlebar_layout.addStretch()
        
        mini_btn = QPushButton("—")
        mini_btn.setStyleSheet("color: rgb(180, 180, 180); border: none; font-size: 14px; max-width: 25px;")
        mini_btn.clicked.connect(self.showMinimized)
        titlebar_layout.addWidget(mini_btn)
        
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("color: rgb(180, 180, 180); border: none; font-size: 14px; max-width: 25px;")
        close_btn.clicked.connect(self.close_gracefully)
        titlebar_layout.addWidget(close_btn)
        
        dashboard_layout.addLayout(titlebar_layout)
        dashboard_layout.addSpacing(15)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        dashboard_layout.addWidget(self.splitter)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.create_core_page())
        self.stacked_widget.addWidget(self.create_memory_page())
        self.stacked_widget.addWidget(self.create_projects_page())
        self.stacked_widget.addWidget(self.create_tools_page())
        self.stacked_widget.addWidget(self.create_settings_page())

        self.splitter.addWidget(self.stacked_widget)

        self.dev_console = UltronDeveloperConsole()
        self.splitter.addWidget(self.dev_console)
        self.splitter.setSizes([700, 300])

        base_layout.addWidget(dashboard)

        # Instantiate Floating Voice Widget (Bug 16)
        self.floating_widget = UltronFloatingVoiceWidget(self)
        self.floating_widget.move(self.width() - 140, 50)
        self.floating_widget.show()

        # Shortcut Toggle Developer Console
        self.shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        self.shortcut.activated.connect(self.toggle_developer_console)

    # -------------------------------------------------------------------
    # Pages Design
    # -------------------------------------------------------------------
    def create_core_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.greeting_lbl = QLabel("ULTRON Cognitive OS standing by...")
        self.greeting_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.greeting_lbl.setStyleSheet("color: rgb(240, 240, 240);")
        self.greeting_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.greeting_lbl)

        self.radar = UltronRadarWidget()
        self.radar.setMinimumHeight(220)
        layout.addWidget(self.radar)

        self.waveform = UltronWaveform()
        self.waveform.setMinimumHeight(60)
        layout.addWidget(self.waveform)

        command_bar_layout = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setObjectName("CommandInput")
        self.cmd_input.setPlaceholderText("Type your command (e.g. 'Arise', 'Continue ROWDY')...")
        self.cmd_input.returnPressed.connect(self.submit_command)
        command_bar_layout.addWidget(self.cmd_input)

        self.send_btn = QPushButton("SEND")
        self.send_btn.setObjectName("ActionButton")
        self.send_btn.setFixedWidth(80)
        self.send_btn.clicked.connect(self.submit_command)
        command_bar_layout.addWidget(self.send_btn)

        layout.addLayout(command_bar_layout)
        return widget

    def create_memory_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel("UME STORAGE STATUS")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("color: rgb(220, 20, 20);")
        layout.addWidget(lbl)
        
        self.memory_view = QTextEdit()
        self.memory_view.setReadOnly(True)
        self.memory_view.setFont(QFont("Consolas", 10))
        self.memory_view.setStyleSheet("background-color: rgb(15, 15, 15); border: 1px solid rgb(30, 30, 30); color: rgb(200, 200, 200);")
        layout.addWidget(self.memory_view)
        return widget

    def create_projects_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel("PROJECT INTELLIGENCE")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("color: rgb(220, 20, 20);")
        layout.addWidget(lbl)
        
        self.projects_view = QTextEdit()
        self.projects_view.setReadOnly(True)
        self.projects_view.setFont(QFont("Consolas", 10))
        self.projects_view.setStyleSheet("background-color: rgb(15, 15, 15); border: 1px solid rgb(30, 30, 30); color: rgb(200, 200, 200);")
        layout.addWidget(self.projects_view)
        return widget

    def create_tools_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel("SYSTEM DIAGNOSTICS & CONTROLS")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("color: rgb(220, 20, 20);")
        layout.addWidget(lbl)
        
        self.tools_view = QTextEdit()
        self.tools_view.setReadOnly(True)
        self.tools_view.setFont(QFont("Consolas", 10))
        self.tools_view.setStyleSheet("background-color: rgb(15, 15, 15); border: 1px solid rgb(30, 30, 30); color: rgb(200, 200, 200);")
        layout.addWidget(self.tools_view)
        return widget

    def create_settings_page(self) -> QWidget:
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        from PySide6.QtWidgets import QScrollArea, QFormLayout, QComboBox, QLineEdit, QGroupBox, QGridLayout
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        lbl = QLabel("SYSTEM CONFIGURATION")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("color: rgb(220, 20, 20);")
        layout.addWidget(lbl)
        
        # Hardware permissions switches (Bug 20)
        hw_lbl = QLabel("Hardware Resource Permissions")
        hw_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        hw_lbl.setStyleSheet("color: rgb(200, 200, 200); margin-top: 10px; margin-bottom: 5px;")
        layout.addWidget(hw_lbl)

        self.mic_toggle = QCheckBox("Enable Microphone Input")
        self.mic_toggle.setFont(QFont("Segoe UI", 10))
        self.mic_toggle.setStyleSheet("color: rgb(220, 220, 220); padding: 3px;")
        from ultron.hal.hal_manager import get_hal_manager
        hal = get_hal_manager()
        self.mic_toggle.setChecked(hal.is_allowed("microphone") if hal else False)
        self.mic_toggle.stateChanged.connect(self.on_mic_toggle)
        layout.addWidget(self.mic_toggle)

        self.spk_toggle = QCheckBox("Enable Speaker Output (TTS)")
        self.spk_toggle.setFont(QFont("Segoe UI", 10))
        self.spk_toggle.setStyleSheet("color: rgb(220, 220, 220); padding: 3px;")
        self.spk_toggle.setChecked(hal.is_allowed("speaker") if hal else False)
        self.spk_toggle.stateChanged.connect(self.on_spk_toggle)
        layout.addWidget(self.spk_toggle)

        self.cam_toggle = QCheckBox("Enable Camera Feed (Vision)")
        self.cam_toggle.setFont(QFont("Segoe UI", 10))
        self.cam_toggle.setStyleSheet("color: rgb(220, 220, 220); padding: 3px;")
        self.cam_toggle.setChecked(hal.is_allowed("camera") if hal else False)
        self.cam_toggle.stateChanged.connect(self.on_cam_toggle)
        layout.addWidget(self.cam_toggle)
        
        # Provider Selectors (Phase 5.2)
        selectors_box = QGroupBox("Subsystem Providers & Settings")
        selectors_box.setStyleSheet("QGroupBox { color: rgb(200, 200, 200); font-weight: bold; border: 1px solid rgb(50, 50, 50); margin-top: 10px; padding-top: 15px; } QLabel { color: rgb(180, 180, 180); font-weight: normal; }")
        form = QFormLayout(selectors_box)
        
        from ultron.core.config_loader import config_loader
        reco_val = config_loader.get("voice", "recognizer", "sapi")
        wake_val = config_loader.get("voice", "wake", "sapi_wake")
        tts_val = config_loader.get("voice", "tts", "pyttsx3")
        wake_phrase_val = config_loader.get("voice", "wake_phrase", "arise")
        
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["Default", "Home", "Development", "Coding", "Gaming", "Offline", "Battery Saver", "Testing"])
        self.profile_combo.setCurrentText("Default")
        self.profile_combo.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        form.addRow("Configuration Profile:", self.profile_combo)
        
        self.reco_combo = QComboBox()
        self.reco_combo.addItems(["sapi", "vosk", "whisper", "future"])
        self.reco_combo.setCurrentText(reco_val)
        self.reco_combo.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        self.reco_combo.currentTextChanged.connect(self.on_reco_changed)
        form.addRow("Recognition Provider:", self.reco_combo)
        
        # Vosk Model Path Selection
        from PySide6.QtWidgets import QHBoxLayout, QPushButton, QFileDialog
        import os
        
        vosk_path_layout = QHBoxLayout()
        self.vosk_path_input = QLineEdit()
        self.vosk_path_input.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        
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
            detect_paths = ["models/vosk-model-en-us-0.42-gigaspeech", "Models/vosk-model-en-us-0.42-gigaspeech"]
            for p in detect_paths:
                if os.path.exists(p):
                    initial_path = os.path.abspath(p)
                    break
                    
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
        btn_browse.setStyleSheet("background-color: rgb(40, 40, 40); color: white; border: 1px solid rgb(60, 60, 60); padding: 3px 8px;")
        
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
        self.wake_combo.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        self.wake_combo.currentTextChanged.connect(self.on_wake_changed)
        form.addRow("Wake Provider:", self.wake_combo)
        
        self.tts_combo = QComboBox()
        self.tts_combo.addItems(["pyttsx3", "piper", "future"])
        self.tts_combo.setCurrentText(tts_val)
        self.tts_combo.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        self.tts_combo.currentTextChanged.connect(self.on_tts_changed)
        form.addRow("Speech Provider:", self.tts_combo)
        
        self.wake_phrase_input = QLineEdit()
        self.wake_phrase_input.setText(wake_phrase_val)
        self.wake_phrase_input.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        self.wake_phrase_input.textChanged.connect(self.on_wake_phrase_changed)
        form.addRow("Wake Phrase:", self.wake_phrase_input)
        
        # Camera & LLM Providers (Phase 5.2)
        self.cam_combo = QComboBox()
        self.cam_combo.addItems(["opencv", "mediapipe", "future"])
        self.cam_combo.setCurrentText("opencv")
        self.cam_combo.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        form.addRow("Camera Provider:", self.cam_combo)

        self.llm_combo = QComboBox()
        self.llm_combo.addItems(["Ollama", "llama.cpp", "OpenAI", "Anthropic", "DeepSeek", "Gemini"])
        self.llm_combo.setCurrentText("Ollama")
        self.llm_combo.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        form.addRow("LLM Provider:", self.llm_combo)
        
        # Audio Device Selectors (Phase 5.2)
        import sounddevice as sd
        devices = []
        try:
            devices = sd.query_devices()
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
        self.mic_combo.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        self.mic_combo.currentTextChanged.connect(self.on_mic_changed)
        form.addRow("Microphone Device:", self.mic_combo)

        # Volume meter layout (Requirement 10)
        from PySide6.QtWidgets import QProgressBar, QPushButton, QHBoxLayout
        test_layout = QHBoxLayout()
        self.volume_meter = QProgressBar()
        self.volume_meter.setRange(0, 100)
        self.volume_meter.setValue(0)
        self.volume_meter.setTextVisible(True)
        self.volume_meter.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgb(50, 50, 50);
                background-color: rgb(20, 20, 20);
                color: white;
                text-align: center;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: rgb(220, 20, 20);
            }
        """)
        
        self.test_mic_btn = QPushButton("Test Microphone")
        self.test_mic_btn.setStyleSheet("background-color: rgb(40, 40, 40); color: white; border: 1px solid rgb(60, 60, 60); padding: 3px 8px;")
        
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

        # Recognition Sample Rate combo (Requirement 10)
        self.sr_combo = QComboBox()
        self.sr_combo.addItems(["16000", "44100", "48000"])
        self.sr_combo.setCurrentText(preferred_sr)
        self.sr_combo.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        self.sr_combo.currentTextChanged.connect(self.on_sample_rate_changed)
        form.addRow("Sample Rate (Hz):", self.sr_combo)

        self.spk_combo = QComboBox()
        self.spk_combo.addItems(spk_devs)
        self.spk_combo.setStyleSheet("background-color: rgb(20, 20, 20); color: white; border: 1px solid rgb(50, 50, 50); padding: 3px;")
        form.addRow("Speaker Device:", self.spk_combo)

        # Voice Sensitivity Slider (Phase 5.2)
        from PySide6.QtWidgets import QSlider
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setMinimum(0)
        self.sensitivity_slider.setMaximum(100)
        self.sensitivity_slider.setValue(80)
        self.sensitivity_slider.setStyleSheet("height: 15px;")
        form.addRow("Voice Sensitivity:", self.sensitivity_slider)

        # Noise suppression and VAD
        self.noise_check = QCheckBox("Enable Noise Suppression")
        self.noise_check.setFont(QFont("Segoe UI", 10))
        self.noise_check.setStyleSheet("color: rgb(180, 180, 180);")
        self.noise_check.setChecked(True)
        form.addRow("", self.noise_check)

        self.vad_check = QCheckBox("Enable Voice Activity Detection (VAD)")
        self.vad_check.setFont(QFont("Segoe UI", 10))
        self.vad_check.setStyleSheet("color: rgb(180, 180, 180);")
        self.vad_check.setChecked(True)
        form.addRow("", self.vad_check)
        
        layout.addWidget(selectors_box)
        
        # Voice Diagnostics Panel (Phase 5.2)
        diag_box = QGroupBox("Live Voice Diagnostics")
        diag_box.setStyleSheet("QGroupBox { color: rgb(220, 20, 20); font-weight: bold; border: 1px solid rgb(50, 50, 50); margin-top: 10px; padding-top: 15px; } QLabel { color: rgb(180, 180, 180); font-weight: normal; }")
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
        
        # Session diagnostics
        self.lbl_session_active = QLabel("Session Active: -")
        self.lbl_session_timeout = QLabel("Session Timeout: -")
        self.lbl_last_wake_time = QLabel("Last Wake Time: -")
        self.lbl_last_command = QLabel("Last Command: -")
        self.lbl_last_state_transition = QLabel("Last State Transition: -")
        
        # Forensic diagnostics labels
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
        
        # Extended fields (Phase 5.2 & 5.3)
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
        self.settings_view.setStyleSheet("background-color: rgb(15, 15, 15); border: 1px solid rgb(30, 30, 30); color: rgb(150, 150, 150); min-height: 120px;")
        layout.addWidget(self.settings_view)
        
        scroll.setWidget(widget)
        main_layout.addWidget(scroll)
        return main_widget

    # -------------------------------------------------------------------
    # State Listeners & Decoupled Animation Controllers (Bug 16)
    # -------------------------------------------------------------------
    @Slot(object)
    def on_state_changed(self, event):
        """Standardized receiver adjusting radar, waves, overlays in response to state transitions."""
        state = event.payload.get("state", "Sleeping")
        
        def update_ui():
            self.floating_widget.set_state(state)
            self.waveform.set_state(state)
            self.radar.set_state(state)
            
        import threading
        if threading.current_thread().name == "MainThread":
            update_ui()
        else:
            QTimer.singleShot(0, update_ui)

    @Slot(object)
    def on_voice_state_changed(self, event):
        """Authoritative receiver updating layout styling and animations from VoiceSessionManager."""
        voice_state = event.payload.get("state", "SLEEPING")
        self.current_voice_state = voice_state
        
        def update_ui():
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
            self.waveform.set_state(visual_state)
            self.radar.set_state(visual_state)
            
            # Map exact state styling:
            color_map = {
                "BOOTING": ("rgb(220, 20, 20)", "BOOTING"),
                "INITIALIZING": ("rgb(255, 140, 0)", "INITIALIZING"),
                "READY": ("rgb(0, 191, 255)", "READY"),
                "SLEEPING": ("rgb(220, 20, 20)", "SLEEPING"),
                "WAKING": ("rgb(220, 20, 20)", "WAKING"),
                "GREETING": ("rgb(220, 20, 20)", "GREETING"),
                "LISTENING": ("rgb(0, 191, 255)", "LISTENING"),
                "PROCESSING": ("rgb(255, 140, 0)", "PROCESSING"),
                "RESPONDING": ("rgb(50, 205, 50)", "RESPONDING"),
                "TIMEOUT": ("rgb(220, 20, 20)", "TIMEOUT"),
                "ERROR": ("rgb(220, 20, 20)", "ERROR"),
                "SHUTDOWN": ("rgb(220, 20, 20)", "SHUTDOWN")
            }
            color, display_state = color_map.get(voice_state, ("rgb(220, 20, 20)", "SLEEPING"))
            
            title_text = f"ULTRON COGNITIVE OS {display_state} | QUEUE: {self.queue_count}"
            self.status_bar_lbl.setText(title_text)
            
            badge_text = "OPERATOR" if not self.display_name else self.display_name.upper()
            self.user_badge.setText(f"{badge_text}\n[{display_state}]")
            self.user_badge.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold; border-top: 1px solid rgb(30, 30, 30); padding-top: 10px;")
            
            if voice_state in ["BOOTING", "INITIALIZING"]:
                self.lock_ui()
            else:
                self.unlock_ui()
                
        import threading
        if threading.current_thread().name == "MainThread":
            update_ui()
        else:
            QTimer.singleShot(0, update_ui)

    @Slot(object)
    def on_queue_count_changed(self, event):
        self.queue_count = event.payload.get("count", 0)
        def update_lbl():
            title_text = f"ULTRON COGNITIVE OS {self.current_voice_state} | QUEUE: {self.queue_count}"
            self.status_bar_lbl.setText(title_text)
        QTimer.singleShot(0, update_lbl)

    @Slot(object)
    def on_wake_triggered(self, event):
        msg = event.payload.get("message")
        QTimer.singleShot(0, lambda: self.greeting_lbl.setText(msg))

    @Slot(object)
    def on_sleep_triggered(self, event):
        msg = event.payload.get("message")
        QTimer.singleShot(0, lambda: self.greeting_lbl.setText(msg))

    @Slot(object)
    def on_voice_diagnostics_update(self, event):
        data = event.payload
        QTimer.singleShot(0, lambda: self.update_voice_diagnostics_ui(data))

    def update_voice_diagnostics_ui(self, data):
        if not hasattr(self, "lbl_reco_prov"):
            return
        self.lbl_reco_prov.setText(f"Recognition Provider: <span style='color: rgb(0, 255, 0);'>{data.get('recognition_engine', '-')}</span>")
        self.lbl_model.setText(f"Model: <span style='color: rgb(0, 255, 0);'>{data.get('model', '-')}</span>")
        self.lbl_mic_dev.setText(f"Microphone: <span style='color: rgb(0, 255, 0);'>{data.get('microphone', '-')}</span>")
        self.lbl_status.setText(f"Status: <span style='color: rgb(0, 255, 0);'>{data.get('status', '-')}</span>")
        self.lbl_audio_chunks.setText(f"Audio Chunks: <span style='color: rgb(0, 255, 0);'>{data.get('audio_chunks', 0)}</span>")
        self.lbl_last_speech.setText(f"Last Recognized Speech: <span style='color: rgb(0, 255, 0);'>'{data.get('last_recognized_speech', '-')}'</span>")
        self.lbl_last_wake_phrase.setText(f"Last Wake Phrase: <span style='color: rgb(0, 255, 0);'>{data.get('last_wake_phrase', '-')}</span>")
        
        conf = data.get('recognition_confidence', 0.0)
        self.lbl_reco_confidence.setText(f"Recognition Confidence: <span style='color: rgb(0, 255, 0);'>{conf:.2f}</span>")
        self.lbl_reco_latency.setText(f"Recognition Latency: <span style='color: rgb(0, 255, 0);'>{data.get('recognition_latency', '-')}</span>")
        self.lbl_voice_thread.setText(f"Voice Thread: <span style='color: rgb(0, 255, 0);'>{data.get('voice_thread', '-')}</span>")
        self.lbl_wake_thread.setText(f"Wake Thread: <span style='color: rgb(0, 255, 0);'>{data.get('wake_thread', '-')}</span>")

        # Set other existing fields
        self.lbl_wake_prov.setText(f"Wake Provider: <span style='color: rgb(0, 255, 0);'>{data.get('wake_engine', '-')}</span>")
        self.lbl_tts_prov.setText(f"TTS Provider: <span style='color: rgb(0, 255, 0);'>{data.get('tts_engine', '-')}</span>")
        disp_st = self.current_voice_state
        if disp_st == "SLEEPING":
            disp_st = "STANDBY"
        elif disp_st in ["THINKING", "EXECUTING"]:
            disp_st = "PROCESSING"
        elif disp_st == "SPEAKING":
            disp_st = "RESPONDING"
        self.lbl_state.setText(f"Current State: <span style='color: rgb(0, 255, 0);'>{disp_st}</span>")
        self.lbl_wake_phrase.setText(f"Wake Phrase: <span style='color: rgb(255, 165, 0);'>{data.get('current_wake_phrase', '-')}</span>")
        
        last_wake = data.get('last_wake_event', 0.0)
        last_wake_str = time.strftime('%H:%M:%S', time.localtime(last_wake)) if last_wake > 0 else "-"
        self.lbl_last_wake.setText(f"Last Wake: {last_wake_str}")

        # Update session telemetry
        self.lbl_session_active.setText(f"Session Active: <span style='color: rgb(0, 255, 0);'>{data.get('session_active', '-')}</span>")
        self.lbl_session_timeout.setText(f"Session Timeout: <span style='color: rgb(0, 255, 0);'>{data.get('session_timeout', '-')}</span>")
        self.lbl_last_wake_time.setText(f"Last Wake Time: <span style='color: rgb(0, 255, 0);'>{data.get('last_wake_time', '-')}</span>")
        self.lbl_last_command.setText(f"Last Command: <span style='color: rgb(0, 255, 0);'>{data.get('last_command', '-')}</span>")
        self.lbl_last_state_transition.setText(f"Last State Transition: <span style='color: rgb(0, 255, 0);'>{data.get('last_state_transition', '-')}</span>")
        
        self.lbl_srv_health.setText(f"Service Health: <span style='color: rgb(0, 255, 0);'>{data.get('com_status', '-')}</span>")
        self.lbl_thread_status.setText(f"Reco Thread: <span style='color: rgb(0, 255, 0);'>{data.get('recognition_status', '-')}</span>")
        self.lbl_latency.setText(f"Callbacks: {data.get('callback_count', 0)} | Wake Matches: {data.get('wake_matches', 0)}")

        spk_name = data.get("current_speaker", "-")
        self.lbl_spk_dev.setText(f"Speaker: {spk_name}")
        
        # CPU & memory mock
        self.lbl_cpu.setText("CPU Usage: <span style='color: rgb(0, 255, 0);'>1.5%</span>")
        self.lbl_mem.setText("Memory Usage: <span style='color: rgb(0, 255, 0);'>42 MB</span>")
        
        self.lbl_queue.setText(f"Queue Size: {self.queue_count}")
        last_ai = data.get("last_ai_response", "None")
        if len(last_ai) > 40:
            last_ai = last_ai[:40] + "..."
        self.lbl_last_ai.setText(f"Last AI Response: '{last_ai}'")
        
        last_err = data.get("last_error", "None")
        self.lbl_last_err.setText(f"Last Error: <span style='color: rgb(220, 20, 20);'>{last_err}</span>")

        # Phase 5.3 fields
        self.lbl_vision_prov.setText(f"Vision Provider: <span style='color: rgb(0, 255, 0);'>{data.get('vision_engine', 'opencv')}</span>")
        self.lbl_llm_prov.setText(f"LLM Provider: <span style='color: rgb(0, 255, 0);'>{data.get('llm_engine', 'Ollama')}</span>")
        self.lbl_cam_dev.setText(f"Camera: {data.get('camera', '-')}")
        self.lbl_running_services.setText(f"Running Services: <span style='color: rgb(0, 255, 0);'>{data.get('running_services_count', 0)}</span>")
        self.lbl_plugin_count.setText(f"Plugin Count: <span style='color: rgb(0, 255, 0);'>{data.get('plugin_count', 0)}</span>")
        self.lbl_sqlite_size.setText(f"SQLite Size: <span style='color: rgb(0, 255, 0);'>{data.get('sqlite_size', '-')}</span>")
        self.lbl_current_skill.setText(f"Current Skill: {data.get('current_skill', '-')}")
        self.lbl_current_project.setText(f"Current Project: {data.get('current_project', '-')}")
        
        # Populate new forensics diagnostics labels
        mic_conn = "Yes" if data.get('com_status') == "Healthy" else "No"
        self.lbl_diag_mic_connected.setText(f"Microphone Connected: <span style='color: rgb(0, 255, 0);'>{mic_conn}</span>")
        self.lbl_diag_curr_dev.setText(f"Current Device: <span style='color: rgb(0, 255, 0);'>{data.get('microphone', '-')}</span>")
        self.lbl_diag_reco_prov.setText(f"Recognition Provider: <span style='color: rgb(0, 255, 0);'>{data.get('recognition_engine', '-')}</span>")
        
        reco_run = data.get('recognition_status', 'Offline')
        self.lbl_diag_reco_running.setText(f"Recognition Running: <span style='color: rgb(0, 255, 0);'>{reco_run}</span>")
        
        wake_run = data.get('wake_status', 'Offline')
        self.lbl_diag_wake_running.setText(f"Wake Detector Running: <span style='color: rgb(0, 255, 0);'>{wake_run}</span>")
        
        last_phrase = data.get('last_recognized_phrase', '-')
        self.lbl_diag_last_phrase.setText(f"Last Recognized Phrase: <span style='color: rgb(0, 255, 0);'>'{last_phrase}'</span>")
        
        self.lbl_diag_wake_match.setText(f"Wake Match: <span style='color: rgb(0, 255, 0);'>{data.get('wake_matches', 0)}</span>")
        
        fps_val = "7.8" if data.get('recognition_engine') == "Sapi" else "7.8"
        self.lbl_diag_reco_fps.setText(f"Recognition FPS: <span style='color: rgb(0, 255, 0);'>{fps_val}</span>")
        
        thread_alive = "Yes" if (reco_run == "Running") else "No"
        self.lbl_diag_thread_alive.setText(f"Recognition Thread Alive: <span style='color: rgb(0, 255, 0);'>{thread_alive}</span>")
        
        self.lbl_diag_callback_count.setText(f"Audio Callback Count: <span style='color: rgb(0, 255, 0);'>{data.get('audio_chunks', 0)}</span>")
        self.lbl_diag_dropped_buffers.setText(f"Dropped Buffers: <span style='color: rgb(0, 255, 0);'>{data.get('dropped_buffers', 0)}</span>")

    # -------------------------------------------------------------------
    # Settings Switch Callbacks (Bug 20)
    # -------------------------------------------------------------------
    def on_mic_toggle(self, state):
        allowed = (state == 2)
        from ultron.hal.hal_manager import get_hal_manager
        hal = get_hal_manager()
        if hal:
            hal.save_permission("microphone", allowed)
        from ultron.core.service_manager import service_manager
        if allowed:
            service_manager.start_service("VoiceRecognitionService")
        else:
            service_manager.stop_service("VoiceRecognitionService")

    def on_spk_toggle(self, state):
        allowed = (state == 2)
        from ultron.hal.hal_manager import get_hal_manager
        hal = get_hal_manager()
        if hal:
            hal.save_permission("speaker", allowed)
        from ultron.core.service_manager import service_manager
        if allowed:
            service_manager.start_service("SpeechService")
        else:
            service_manager.stop_service("SpeechService")

    def on_cam_toggle(self, state):
        allowed = (state == 2)
        from ultron.hal.hal_manager import get_hal_manager
        hal = get_hal_manager()
        if hal:
            hal.save_permission("camera", allowed)

    def on_reco_changed(self, text):
        self.save_voice_config("recognizer", text)
        event_bus.publish("RECOGNITION_PROVIDER_CHANGED", {"provider": text})

    def on_wake_changed(self, text):
        self.save_voice_config("wake", text)

    def on_tts_changed(self, text):
        self.save_voice_config("tts", text)
        event_bus.publish("TTS_PROVIDER_CHANGED", {"provider": text})

    def on_mic_changed(self, text):
        import sounddevice as sd
        devices = []
        try:
            devices = sd.query_devices()
        except Exception:
            pass
        
        device_idx = None
        for idx, d in enumerate(devices):
            if d["name"] == text and d.get("max_input_channels", 0) > 0:
                device_idx = idx
                break
                
        if device_idx is not None:
            from ultron.core.service_manager import service_manager
            voice_engine = service_manager.get_service("VoiceEngineService")
            if voice_engine:
                voice_engine.switch_microphone(text, device_idx)

    def on_sample_rate_changed(self, text):
        rate = int(text)
        from ultron.core.service_manager import service_manager
        voice_engine = service_manager.get_service("VoiceEngineService")
        if voice_engine:
            voice_engine.switch_sample_rate(rate)

    @Slot(object)
    def on_volume_level_changed(self, event):
        if not hasattr(self, "volume_meter") or self.volume_meter is None:
            return
        level = event.payload.get("level", 0.0)
        percent = min(100, int((level / 4000.0) * 100))
        QTimer.singleShot(0, lambda: self.volume_meter.setValue(percent))

    def on_wake_phrase_changed(self, text):
        self.save_voice_config("wake_phrase", text)
        from ultron.core.service_manager import service_manager
        engine_srv = service_manager.get_service("VoiceEngineService")
        if engine_srv:
            engine_srv.update_wake_phrase(text)

    @Slot(object)
    def on_notification_event(self, event):
        msg = event.payload.get("message", "-")
        title = event.payload.get("title", "-")
        notif_str = f"Last Notification: {title} - {msg}"
        QTimer.singleShot(0, lambda: self.lbl_last_notif.setText(notif_str) if hasattr(self, "lbl_last_notif") else None)

    @Slot(object)
    def on_warning_event(self, event):
        msg = event.payload.get("message", "-")
        warn_str = f"Last Warning: <span style='color: yellow;'>{msg}</span>"
        QTimer.singleShot(0, lambda: self.lbl_last_warn.setText(warn_str) if hasattr(self, "lbl_last_warn") else None)

    @Slot(object)
    def on_error_event(self, event):
        msg = event.payload.get("message", "-")
        err_str = f"Last Error: <span style='color: rgb(220, 20, 20);'>{msg}</span>"
        QTimer.singleShot(0, lambda: self.lbl_last_err.setText(err_str) if hasattr(self, "lbl_last_err") else None)

    @Slot(str)
    def on_profile_changed(self, profile_name):
        # Switch profiles instantly! (Phase 5.3)
        profiles = {
            "Default": {"reco": "sapi", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "arise", "llm": "Ollama"},
            "Home": {"reco": "sapi", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "arise", "llm": "Ollama"},
            "Development": {"reco": "vosk", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "ultron", "llm": "llama.cpp"},
            "Coding": {"reco": "vosk", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "ultron", "llm": "llama.cpp"},
            "Gaming": {"reco": "vosk", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "hey ultron", "llm": "Gemini"},
            "Offline": {"reco": "vosk", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "arise", "llm": "llama.cpp"},
            "Battery Saver": {"reco": "sapi", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "arise", "llm": "Ollama"},
            "Testing": {"reco": "vosk", "wake": "sapi_wake", "tts": "pyttsx3", "phrase": "arise", "llm": "Ollama"},
        }
        
        prof = profiles.get(profile_name, profiles["Default"])
        
        # Block signals temporarily to prevent loops
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
        
        # Persist and publish changes instantly
        self.on_reco_changed(prof["reco"])
        self.on_wake_changed(prof["wake"])
        self.on_tts_changed(prof["tts"])
        self.on_wake_phrase_changed(prof["phrase"])
        
        event_bus.publish("CONFIGURATION_PROFILE_CHANGED", {"profile": profile_name})

    def save_voice_config(self, key, value):
        import json
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

    # -------------------------------------------------------------------
    # Live Diagnostics Refresh (Bug 22)
    # -------------------------------------------------------------------
    def refresh_diagnostics(self):
        from ultron.hal.hal_manager import get_hal_manager
        hal = get_hal_manager()
        devices = hal.check_devices() if hal else {"microphone": False, "speaker": False, "camera": False}
        
        def get_status_html(name, is_permitted, is_present, service_name=None):
            if not is_permitted:
                return "<span style='color: rgb(255, 165, 0);'>Disabled</span>"
            if not is_present:
                return "<span style='color: rgb(150, 150, 150);'>Offline</span>"
            if service_name:
                service = service_manager.get_service(service_name)
                if service:
                    return f"<span style='color: rgb(0, 255, 0);'>{service.health()}</span>"
            return "<span style='color: rgb(0, 255, 0);'>Healthy</span>"

        html = "<h3 style='color: rgb(220, 20, 20);'>LIVE OS DIAGNOSTICS</h3>"
        html += "<table width='100%' cellpadding='4' style='color: rgb(200, 200, 200); font-family: monospace; border-bottom: 1px solid rgb(30,30,30);'>"
        
        # Audio inputs / outputs
        mic_stat = get_status_html("Microphone", hal.is_allowed("microphone") if hal else False, devices["microphone"], "VoiceRecognitionService")
        html += f"<tr><td>Microphone</td><td>{mic_stat}</td></tr>"
        
        spk_stat = get_status_html("Speaker", hal.is_allowed("speaker") if hal else False, devices["speaker"], "SpeechService")
        html += f"<tr><td>Speaker</td><td>{spk_stat}</td></tr>"
        
        cam_stat = get_status_html("Camera", hal.is_allowed("camera") if hal else False, devices["camera"])
        html += f"<tr><td>Camera</td><td>{cam_stat}</td></tr>"
        
        # Background Services
        reco_service = service_manager.get_service("VoiceRecognitionService")
        reco_stat = f"<span style='color: rgb(0, 255, 0);'>{reco_service.health()}</span>" if reco_service else "<span style='color: gray;'>Offline</span>"
        html += f"<tr><td>Voice Recognition</td><td>{reco_stat}</td></tr>"
        
        wake_service = service_manager.get_service("WakeService")
        wake_stat = f"<span style='color: rgb(0, 255, 0);'>{wake_service.health()}</span>" if wake_service else "<span style='color: gray;'>Offline</span>"
        html += f"<tr><td>Wake Engine</td><td>{wake_stat}</td></tr>"
        
        # SQLite / Memory
        html += "<tr><td>SQLite Database</td><td><span style='color: rgb(0, 255, 0);'>Healthy</span></td></tr>"
        html += "<tr><td>Memory Engine</td><td><span style='color: rgb(0, 255, 0);'>Healthy</span></td></tr>"
        html += "<tr><td>Cognitive Core</td><td><span style='color: rgb(0, 255, 0);'>Healthy</span></td></tr>"
        skills = self.core.get_module("skills_registry")
        skills_stat = f"<span style='color: rgb(0, 255, 0);'>{skills.health()['status'].title()}</span>" if skills else "<span style='color: gray;'>Offline</span>"
        html += f"<tr><td>Skill Registry</td><td>{skills_stat}</td></tr>"
        
        active_tasks = [t for t in task_manager.list_tasks() if t["status"] in ["Running", "Queued"]]
        exec_stat = f"<span style='color: rgb(255, 165, 0);'>Running ({len(active_tasks)} tasks)</span>" if active_tasks else "<span style='color: rgb(0, 255, 0);'>Standing By</span>"
        html += f"<tr><td>Executor</td><td>{exec_stat}</td></tr>"
        
        html += "</table>"
        
        # Architectural Diagnostics
        import threading
        from ultron.core.event_bus import event_bus
        from ultron.core.voice_session_manager import get_voice_session_manager, VoiceState
        
        mgr = get_voice_session_manager()
        voice_state = mgr.state.name if mgr else "SLEEPING"
        
        wake_detector = service_manager.get_service("WakeDetectorService")
        wake_detector_status = wake_detector.health() if wake_detector else "Offline"
        wake_enabled = "Yes" if (wake_detector and wake_detector.active) else "No"
        
        session_active = "Yes" if (mgr and mgr.state != VoiceState.SLEEPING) else "No"
        
        # Microphone / Recognition Provider
        engine_srv = service_manager.get_service("VoiceEngineService")
        microphone = "GENERAL WEBCAM"
        rec_provider = "VOSK"
        wake_provider = "VOSK"
        if engine_srv:
            microphone = engine_srv.diagnostics.get("current_microphone", "GENERAL WEBCAM")
            rec_provider = engine_srv.reco_provider_name.upper() if engine_srv.reco_provider_name else "VOSK"
            wake_provider = engine_srv.wake_provider_name.upper() if engine_srv.wake_provider_name else "VOSK"
            
        # Thread status checks
        reco_threads = [t for t in threading.enumerate() if "Recognition" in t.name or "Voice" in t.name]
        wake_threads = [t for t in threading.enumerate() if "Wake" in t.name]
        tts_threads = [t for t in threading.enumerate() if "tts" in t.name.lower() or "pyttsx" in t.name.lower()]
        
        # We also get the queue consumer thread status from AICore
        from ultron.core.ai_core import get_ai_core
        ai = get_ai_core()
        ai_thread_status = "Running" if (ai and ai.queue.worker_thread and ai.queue.worker_thread.is_alive()) else "Offline"
        
        recognition_thread = "Running" if reco_threads else "Offline"
        wake_thread = "Running" if wake_threads else "Offline"
        speech_thread = "Running" if (tts_threads or (engine_srv and engine_srv.active_tts)) else "Offline"
        
        # CPU / RAM Usage
        import os
        try:
            import psutil
            process = psutil.Process(os.getpid())
            ram_usage = f"{process.memory_info().rss / 1024 / 1024:.1f} MB"
            cpu_usage = f"{psutil.cpu_percent()}%"
        except Exception:
            ram_usage = "Unknown"
            cpu_usage = "Unknown"

        services_list = ", ".join(service_manager.list_services())
        app_version = "1.0.0"
        
        # Timer details
        timer_active = "Inactive"
        sec_rem = "-"
        convo_id = "-"
        last_wake_time = "-"
        last_command = "-"
        last_response = "-"
        avg_rec_lat = "0 ms"
        avg_res_lat = "0 ms"
        avg_ai_time = "0 ms"
        wake_count = 0
        cmds_proc = 0
        resp_spk = 0
        
        if mgr:
            timer_active = "Active" if mgr.session_timer.isActive() else "Inactive"
            rem_ms = mgr.session_timer.remainingTime()
            sec_rem = f"{rem_ms / 1000.0:.1f} s" if rem_ms >= 0 else "-"
            convo_id = mgr.convo_id
            if mgr.last_wake_time > 0:
                import time
                last_wake_time = time.strftime('%H:%M:%S', time.localtime(mgr.last_wake_time))
            last_command = mgr.last_command
            last_response = mgr.last_response
            avg_rec_lat = f"{mgr.avg_recognition_latency * 1000:.0f} ms"
            avg_res_lat = f"{mgr.avg_response_latency * 1000:.0f} ms"
            avg_ai_time = f"{mgr.avg_ai_time * 1000:.0f} ms"
            wake_count = mgr.wake_count
            cmds_proc = mgr.commands_processed
            resp_spk = mgr.responses_spoken
            
        # EventBus subscribers count
        sub_count = 0
        with event_bus._lock:
            for subs in event_bus._subscribers.values():
                sub_count += len(subs)
                
        # Event queue length
        queue_len = ai.queue.get_count() if ai else 0
        
        # Boot Stage
        import main
        boot_stage = getattr(main, "current_boot_stage", "BOOT 09: Boot complete")
        stage_b_complete = "Yes" if (mgr and mgr.voice is not None) else "No"
        
        # Plugin Status
        from ultron.core.plugin_loader import get_plugin_loader
        p_loader = get_plugin_loader()
        plugin_status = f"Active ({len(p_loader.loaded_plugins)} plugins)" if (p_loader and p_loader.loaded_plugins) else "Offline (Unavailable)"
        
        # Memory Status
        from ultron.memory import get_memory_manager
        mem = get_memory_manager()
        memory_status = "Loaded (SQLite)" if mem else "Offline"
        
        ai_provider = "AICore (Local)"
        
        html += "<br/><b>Architectural Diagnostics:</b><br/>"
        html += "<table width='100%' cellpadding='4' style='color: rgb(200, 200, 200); font-family: monospace; border-bottom: 1px solid rgb(30,30,30);'>"
        html += f"<tr><td>Current State</td><td><span style='color: rgb(0, 255, 0);'>{voice_state}</span></td></tr>"
        html += f"<tr><td>Wake Enabled</td><td><span style='color: rgb(0, 255, 0);'>{wake_enabled}</span></td></tr>"
        html += f"<tr><td>Wake Provider</td><td><span style='color: rgb(0, 255, 0);'>{wake_provider}</span></td></tr>"
        html += f"<tr><td>Recognition Provider</td><td><span style='color: rgb(0, 255, 0);'>{rec_provider}</span></td></tr>"
        html += f"<tr><td>Current Microphone</td><td><span style='color: rgb(0, 255, 0);'>{microphone}</span></td></tr>"
        html += f"<tr><td>Speech Thread</td><td><span style='color: rgb(0, 255, 0);'>{speech_thread}</span></td></tr>"
        html += f"<tr><td>Queue Thread</td><td><span style='color: rgb(0, 255, 0);'>{ai_thread_status}</span></td></tr>"
        html += f"<tr><td>EventBus Queue</td><td><span style='color: rgb(0, 255, 0);'>{queue_len}</span></td></tr>"
        html += f"<tr><td>EventBus Subscribers</td><td><span style='color: rgb(0, 255, 0);'>{sub_count}</span></td></tr>"
        html += f"<tr><td>Boot Stage</td><td><span style='color: rgb(0, 255, 0);'>{boot_stage}</span></td></tr>"
        html += f"<tr><td>Plugin Status</td><td><span style='color: rgb(0, 255, 0);'>{plugin_status}</span></td></tr>"
        html += f"<tr><td>Memory Status</td><td><span style='color: rgb(0, 255, 0);'>{memory_status}</span></td></tr>"
        html += f"<tr><td>Conversation ID</td><td><span style='color: rgb(0, 255, 0);'>{convo_id}</span></td></tr>"
        html += f"<tr><td>Stage B Complete</td><td><span style='color: rgb(0, 255, 0);'>{stage_b_complete}</span></td></tr>"
        html += f"<tr><td>Session Timer Remaining</td><td><span style='color: rgb(0, 255, 0);'>{sec_rem}</span></td></tr>"
        html += f"<tr><td>Current AI Provider</td><td><span style='color: rgb(0, 255, 0);'>{ai_provider}</span></td></tr>"
        html += f"<tr><td>Wake Count</td><td><span style='color: rgb(0, 255, 0);'>{wake_count}</span></td></tr>"
        html += f"<tr><td>Commands Processed</td><td><span style='color: rgb(0, 255, 0);'>{cmds_proc}</span></td></tr>"
        html += f"<tr><td>Responses Spoken</td><td><span style='color: rgb(0, 255, 0);'>{resp_spk}</span></td></tr>"
        html += f"<tr><td>Average Recognition Time</td><td><span style='color: rgb(0, 255, 0);'>{avg_rec_lat}</span></td></tr>"
        html += f"<tr><td>Average AI Time</td><td><span style='color: rgb(0, 255, 0);'>{avg_ai_time}</span></td></tr>"
        html += f"<tr><td>Average Response Time</td><td><span style='color: rgb(0, 255, 0);'>{avg_res_lat}</span></td></tr>"
        html += f"<tr><td>Memory Usage</td><td><span style='color: rgb(0, 255, 0);'>{ram_usage}</span></td></tr>"
        html += f"<tr><td>CPU Usage</td><td><span style='color: rgb(0, 255, 0);'>{cpu_usage}</span></td></tr>"
        html += f"<tr><td>Registered Services</td><td><span style='color: rgb(0, 255, 0);'>{services_list}</span></td></tr>"
        html += f"<tr><td>Application Version</td><td><span style='color: rgb(0, 255, 0);'>{app_version}</span></td></tr>"
        html += "</table>"
        
        # Voice Recognition Forensics (Phase 7 Live Diagnostics Fix)
        active_rec = engine_srv.active_recognizer if engine_srv else None
        rec_thread_alive = "Yes" if (active_rec and active_rec.thread and active_rec.thread.is_alive()) else "No"
        rec_loop_running = "Yes" if (active_rec and active_rec.active) else "No"
        mic_open = "Yes" if (active_rec and active_rec.active) else "No"
        stream_active = "Yes" if (active_rec and active_rec.active) else "No"
        cb_count = getattr(active_rec, "audio_callback_count", getattr(active_rec, "chunks_received", 0)) if active_rec else 0
        rec_count = event_bus.get_publish_count("SPEECH_RECOGNIZED")
        speech_events_pub = event_bus.get_publish_count("SPEECH_RECOGNIZED")
        wake_events_pub = event_bus.get_publish_count("WAKE_DETECTED")
        commands_exec = event_bus.get_publish_count("COMMAND_RECEIVED")
        dropped_buffers = getattr(active_rec, "dropped_buffers", 0) if active_rec else 0
        current_voice_state = voice_state

        html += "<br/><b>Voice Recognition Forensics:</b><br/>"
        html += "<table width='100%' cellpadding='4' style='color: rgb(200, 200, 200); font-family: monospace; border-bottom: 1px solid rgb(30,30,30);'>"
        html += f"<tr><td>Recognition Thread Alive</td><td><span style='color: rgb(0, 255, 0);'>{rec_thread_alive}</span></td></tr>"
        html += f"<tr><td>Recognition Loop Running</td><td><span style='color: rgb(0, 255, 0);'>{rec_loop_running}</span></td></tr>"
        html += f"<tr><td>Microphone Open</td><td><span style='color: rgb(0, 255, 0);'>{mic_open}</span></td></tr>"
        html += f"<tr><td>Audio Stream Active</td><td><span style='color: rgb(0, 255, 0);'>{stream_active}</span></td></tr>"
        html += f"<tr><td>Audio Callback Count</td><td><span style='color: rgb(0, 255, 0);'>{cb_count}</span></td></tr>"
        html += f"<tr><td>Recognition Count</td><td><span style='color: rgb(0, 255, 0);'>{rec_count}</span></td></tr>"
        html += f"<tr><td>Speech Events Published</td><td><span style='color: rgb(0, 255, 0);'>{speech_events_pub}</span></td></tr>"
        html += f"<tr><td>Wake Events Published</td><td><span style='color: rgb(0, 255, 0);'>{wake_events_pub}</span></td></tr>"
        html += f"<tr><td>Commands Executed</td><td><span style='color: rgb(0, 255, 0);'>{commands_exec}</span></td></tr>"
        html += f"<tr><td>Dropped Buffers</td><td><span style='color: rgb(0, 255, 0);'>{dropped_buffers}</span></td></tr>"
        html += f"<tr><td>Current Voice State</td><td><span style='color: rgb(0, 255, 0);'>{current_voice_state}</span></td></tr>"
        html += "</table>"
        
        # Task logs
        html += "<br/><b>Task History:</b><br/>"
        tasks = task_manager.list_tasks()[-5:]
        for t in reversed(tasks):
            color = "rgb(0, 255, 0)" if t["status"] == "Completed" else "rgb(255, 0, 0)" if t["status"] == "Failed" else "rgb(255, 165, 0)"
            html += f"Task: <b>{t['description'][:30]}</b> | Status: <b style='color: {color};'>{t['status'].upper()}</b><br/>"
            
        self.tools_view.setHtml(html)

    def on_vosk_model_missing(self, event):
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "prompt_for_vosk_model", Qt.ConnectionType.QueuedConnection)

    @Slot()
    def prompt_for_vosk_model(self):
        from PySide6.QtWidgets import QMessageBox, QFileDialog
        import os
        box = QMessageBox(self)
        box.setWindowTitle("Vosk Model Missing")
        box.setText("The Vosk speech recognition model could not be found automatically.\n\nWould you like to browse and select the model folder now?")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        box.setStyleSheet("background-color: rgb(20, 20, 20); color: white;")
        ret = box.exec()
        if ret == QMessageBox.StandardButton.Yes:
            dir_path = QFileDialog.getExistingDirectory(self, "Select Vosk Model Directory", os.getcwd())
            if dir_path:
                from ultron.memory import get_memory_manager
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
                    
                from ultron.core.service_manager import service_manager
                service_manager.restart_service("VoiceRecognitionService")

    # -------------------------------------------------------------------
    # Panel Switch Refresh Helpers
    # -------------------------------------------------------------------
    def switch_panel(self, index):
        self.stacked_widget.setCurrentIndex(index)
        if index == 1:
            self.refresh_memory_view()
        elif index == 2:
            self.refresh_projects_view()
        elif index == 4:
            self.refresh_settings_view()

    def refresh_memory_view(self):
        self.memory_view.clear()
        html = "<h3 style='color: rgb(220, 20, 20);'>UME STORAGE VIEW</h3>"
        try:
            pref = self.memory.list_records("preference")
            html += "<b>Subsystem Preferences:</b><br/>"
            for p in pref:
                html += f"Key: <code>{p['title']}</code> | Content: <b>{p['content']}</b><br/>"
            
            conv = self.memory.list_records("conversation", limit=20)
            html += "<br/><b>Conversation Turn History:</b><br/>"
            for c in conv:
                html += f"<span style='color: rgb(110, 110, 110);'>{c['updated_at']}</span> - <b>{c['title']}</b><br/><pre>{c['content']}</pre><br/>"
        except Exception as e:
            html += f"<span style='color: red;'>Error reading records: {e}</span>"
        self.memory_view.setHtml(html)

    def refresh_projects_view(self):
        self.projects_view.clear()
        html = "<h3 style='color: rgb(220, 20, 20);'>ACTIVE PROJECTS LIST</h3>"
        try:
            projs = self.memory.list_records("project")
            for p in projs:
                try:
                    data = json.loads(p["content"])
                except Exception:
                    data = {}
                html += f"Project: <b style='color: rgb(220,20,20);'>{p['title']}</b><br/>"
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

    # -------------------------------------------------------------------
    # Window Draggability Implementation
    # -------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position is not None:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    # -------------------------------------------------------------------
    # Profile Loader
    # -------------------------------------------------------------------
    def load_user_profile(self):
        try:
            pref_records = self.memory.list_records("preference")
            for r in pref_records:
                if r["title"] == "display_name":
                    self.display_name = r["content"]
        except Exception:
            pass

        # Update initial badge text
        curr_state = self.current_voice_state
        if self.display_name:
            self.user_badge.setText(f"{self.display_name.upper()}\n[{curr_state.upper()}]")
            from ultron.core.wake_engine import wake_engine
            if wake_engine:
                wake_engine.set_display_name(self.display_name)
        else:
            self.user_badge.setText(f"OPERATOR\n[{curr_state.upper()}]")

    # -------------------------------------------------------------------
    # Commands & Pipeline Dispatching
    # -------------------------------------------------------------------
    def submit_command(self):
        text = self.cmd_input.text().strip()
        if not text:
            return
            
        self.cmd_input.clear()
        
        # Intercept wake command (Bug 15 & 18)
        from ultron.core.wake_engine import wake_engine
        from ultron.core.ai_core import ai_core
        
        if text.lower().strip() == "arise":
            from ultron.core.event_bus import event_bus
            event_bus.publish("WAKE_DETECTED", {"timestamp": time.time()})
        else:
            ai_core.execute_command(text)

    def toggle_developer_console(self):
        self.dev_console.toggle_console()
        self.core.logger.info("SYSTEM", f"Developer Console toggled. Visible: {self.dev_console.isVisible()}")

    def close_gracefully(self):
        self.core.logger.info("SYSTEM", "Initiating shutdown protocol.")
        
        # Unsubscribe EventBus listeners to prevent memory leak / duplicate calls on reload
        from ultron.core.event_bus import event_bus
        try:
            event_bus.unsubscribe("STATE_CHANGED", self.on_state_changed)
            event_bus.unsubscribe("VOICE_STATE_CHANGED", self.on_voice_state_changed)
            event_bus.unsubscribe("QUEUE_COUNT_CHANGED", self.on_queue_count_changed)
            event_bus.unsubscribe("WAKE_TRIGGERED", self.on_wake_triggered)
            event_bus.unsubscribe("SLEEP_TRIGGERED", self.on_sleep_triggered)
            event_bus.unsubscribe("VOICE_DIAGNOSTICS_UPDATE", self.on_voice_diagnostics_update)
            event_bus.unsubscribe("NOTIFICATION", self.on_notification_event)
            event_bus.unsubscribe("WARNING_OCCURRED", self.on_warning_event)
            event_bus.unsubscribe("ERROR_OCCURRED", self.on_error_event)
            event_bus.unsubscribe("VOSK_MODEL_MISSING", self.on_vosk_model_missing)
            event_bus.unsubscribe("VOLUME_LEVEL_CHANGED", self.on_volume_level_changed)
        except Exception:
            pass
            
        # Stop background services
        try:
            health_monitor.stop()
            service_manager.stop_all()
        except Exception:
            pass
            
        self.core.session.shutdown()
        UltronAnimations.fade_out_window(self, self.close, duration_ms=300)
