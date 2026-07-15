"""
ULTRON Themes — Premium Dark (Matte Black & Dark Graphite) with Scarlet Red accent lighting.
"""

from PySide6.QtGui import QColor

class UltronColors:
    # Color palette matching user request
    BG_MATTE_BLACK = QColor(9, 9, 9)             # #090909
    PANEL_DARK_GRAPHITE = QColor(17, 17, 17)      # #111111
    ACCENT_SCARLET_RED = QColor(193, 18, 31)     # #C1121F
    ACCENT_LIGHT_RED = QColor(230, 57, 70)       # #E63946
    GLOW_RED = QColor(225, 57, 70, 90)           # rgba(225,57,70,0.35)
    
    TEXT_WHITE = QColor(245, 245, 245)           # #F5F5F5
    TEXT_GRAY = QColor(160, 160, 160)            # #A0A0A0

class UltronThemeStyles:
    @staticmethod
    def get_application_stylesheet() -> str:
        return """
            QWidget {
                background-color: #090909;
                color: #F5F5F5;
                font-family: 'Inter', 'SF Pro Display', Arial, sans-serif;
                font-size: 13px;
            }
            
            QFrame#MainPanel {
                background-color: #090909;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
            }
            
            QFrame#GlassPanel {
                background-color: rgba(17, 17, 17, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 10px;
            }
            
            QFrame#ConsoleCard {
                background-color: #111111;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            
            QTextEdit {
                background-color: rgba(17, 17, 17, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                color: #F5F5F5;
            }
            
            QTextEdit#ConsoleOutput {
                background-color: transparent;
                border: none;
                color: #A0A0A0;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            
            QLineEdit#CommandInput {
                background-color: rgba(17, 17, 17, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 20px;
                padding: 6px 14px;
                color: #F5F5F5;
                font-size: 13px;
            }
            
            QLineEdit#CommandInput:focus {
                border: 1px solid #E63946;
            }
            
            QPushButton#ActionButton {
                background-color: rgba(17, 17, 17, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 6px 14px;
                color: #F5F5F5;
            }
            
            QPushButton#ActionButton:hover {
                background-color: #C1121F;
                border: 1px solid #E63946;
                color: #FFFFFF;
            }
            
            QPushButton#ActionButton:pressed {
                background-color: #8B0000;
            }
            
            QLabel#TitleLabel {
                font-size: 18px;
                font-weight: 600;
                color: #C1121F;
                letter-spacing: 1px;
            }
            
            QLabel#StatusLabel {
                font-size: 11px;
                color: #A0A0A0;
            }
            
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 3px;
                text-align: right;
                color: #A0A0A0;
                font-size: 9px;
            }
            
            QProgressBar::chunk {
                background-color: #E63946;
                border-radius: 2px;
            }
            
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.08);
                min-height: 20px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #E63946;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            
            QComboBox {
                background-color: #111111;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 3px 6px;
                color: #F5F5F5;
            }
            QComboBox:on {
                border: 1px solid #E63946;
            }
            QComboBox QAbstractItemView {
                background-color: #111111;
                border: 1px solid rgba(255, 255, 255, 0.05);
                selection-background-color: #C1121F;
                selection-color: #FFFFFF;
            }
        """
