"""
ULTRON Developer Console — Overlay debugger panel displaying real-time pipeline events.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont
from ultron.core import event_bus

class UltronDeveloperConsole(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ConsoleCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setVisible(False)  # Hidden by default
        self._init_ui()
        
        # Subscribe to logging events from the bus
        event_bus.subscribe("PipelineLogEmitted", self.on_log_emitted)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header bar
        header_layout = QHBoxLayout()
        title = QLabel("COGNITIVE DEBUG CONSOLE")
        title.setStyleSheet("font-weight: bold; color: rgb(220, 20, 20); font-size: 11px; letter-spacing: 1px;")
        header_layout.addWidget(title)
        
        shortcut_lbl = QLabel("[Ctrl+Shift+D to hide]")
        shortcut_lbl.setStyleSheet("color: rgb(100, 100, 100); font-size: 10px;")
        header_layout.addWidget(shortcut_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(header_layout)
        
        # Output terminal area
        self.terminal_output = QTextEdit()
        self.terminal_output.setObjectName("ConsoleOutput")
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setFont(QFont("Consolas", 10))
        self.terminal_output.setPlaceholderText("Awaiting pipeline events...")
        layout.addWidget(self.terminal_output)

    @Slot(object)
    def on_log_emitted(self, event):
        """Appends log entries to the terminal text box in real-time."""
        log_entry = event.payload
        if not log_entry:
            return
            
        color_map = {
            "SYSTEM": "rgb(200, 200, 200)",
            "PERCEPTION": "rgb(0, 191, 255)",
            "CONTEXT": "rgb(238, 130, 238)",
            "MEMORY": "rgb(60, 179, 113)",
            "PLANNER": "rgb(255, 165, 0)",
            "REASONING": "rgb(255, 215, 0)",
            "EXECUTION": "rgb(220, 20, 20)",
            "REFLECTION": "rgb(186, 85, 211)",
            "VOICE": "rgb(240, 128, 128)"
        }
        
        category = log_entry.get("category", "SYSTEM")
        color = color_map.get(category, "rgb(200, 200, 200)")
        
        log_html = (
            f"<span style='color: rgb(110, 110, 110);'>{log_entry.get('timestamp')[11:19]}</span> "
            f"[<span style='color: {color}; font-weight: bold;'>{category}</span>] "
            f"<span style='color: rgb(220, 220, 220);'>{log_entry.get('message')}</span>"
        )
        
        from PySide6.QtCore import QTimer
        def safe_append():
            self.terminal_output.append(log_html)
            scrollbar = self.terminal_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        QTimer.singleShot(0, safe_append)


    def toggle_console(self):
        self.setVisible(not self.isVisible())
        if self.isVisible():
            self.terminal_output.append("<span style='color: rgb(220, 20, 20); font-weight: bold;'>[Console Connected]</span>")
