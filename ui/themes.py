"""
ULTRON Themes — Premium Dark (Matte Black & Dark Graphite) with Scarlet Red accent lighting.
"""

from PySide6.QtGui import QColor

class UltronColors:
    # Color palette
    BG_MATTE_BLACK = QColor(10, 10, 10)
    PANEL_DARK_GRAPHITE = QColor(25, 25, 25)
    ACCENT_SCARLET_RED = QColor(220, 20, 20)
    ACCENT_DARK_CRIMSON = QColor(140, 10, 10)
    
    TEXT_WHITE = QColor(240, 240, 240)
    TEXT_GRAY = QColor(130, 130, 130)

class UltronThemeStyles:
    @staticmethod
    def get_application_stylesheet() -> str:
        return """
            QWidget {
                background-color: rgb(10, 10, 10);
                color: rgb(240, 240, 240);
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            
            QFrame#MainPanel {
                background-color: rgb(25, 25, 25);
                border: 1px solid rgb(50, 50, 50);
                border-radius: 6px;
            }
            
            QFrame#ConsoleCard {
                background-color: rgb(18, 18, 18);
                border: 1px solid rgb(40, 40, 40);
                border-radius: 4px;
            }
            
            QTextEdit#ConsoleOutput {
                background-color: transparent;
                border: none;
                color: rgb(180, 180, 180);
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
            
            QLineEdit#CommandInput {
                background-color: rgb(20, 20, 20);
                border: 1px solid rgb(60, 60, 60);
                border-radius: 4px;
                padding: 6px 12px;
                color: rgb(255, 255, 255);
                font-size: 14px;
            }
            
            QLineEdit#CommandInput:focus {
                border: 1px solid rgb(220, 20, 20);
            }
            
            QPushButton#ActionButton {
                background-color: rgb(35, 35, 35);
                border: 1px solid rgb(65, 65, 65);
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                color: rgb(245, 245, 245);
            }
            
            QPushButton#ActionButton:hover {
                background-color: rgb(220, 20, 20);
                border: 1px solid rgb(220, 20, 20);
                color: rgb(255, 255, 255);
            }
            
            QPushButton#ActionButton:pressed {
                background-color: rgb(140, 10, 10);
            }
            
            QLabel#TitleLabel {
                font-size: 20px;
                font-weight: bold;
                color: rgb(220, 20, 20);
                letter-spacing: 2px;
            }
            
            QLabel#StatusLabel {
                font-size: 12px;
                color: rgb(130, 130, 130);
            }
            
            QProgressBar {
                background-color: rgb(20, 20, 20);
                border: 1px solid rgb(45, 45, 45);
                border-radius: 3px;
                text-align: center;
                color: transparent;
            }
            
            QProgressBar::chunk {
                background-color: rgb(220, 20, 20);
                border-radius: 2px;
            }
            
            QScrollBar:vertical {
                border: none;
                background: rgb(15, 15, 15);
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgb(45, 45, 45);
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgb(220, 20, 20);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """
