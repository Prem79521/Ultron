"""
ULTRON Animations — Helper utilities for window fades, sliding widgets, and graphical transitions.
"""

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QObject

class UltronAnimations:
    @staticmethod
    def fade_in_window(window: QObject, duration_ms: int = 500):
        """Fades in the window transparency using property animation."""
        if not hasattr(window, "setWindowOpacity"):
            return
        window.setWindowOpacity(0.0)
        anim = QPropertyAnimation(window, b"windowOpacity", window)
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(0.98)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()
        # Prevent GC cleanup of animation during execution
        window._fade_in_anim = anim

    @staticmethod
    def fade_out_window(window: QObject, finished_callback, duration_ms: int = 400):
        """Fades out window opacity before closing."""
        if not hasattr(window, "setWindowOpacity"):
            finished_callback()
            return
        anim = QPropertyAnimation(window, b"windowOpacity", window)
        anim.setDuration(duration_ms)
        anim.setStartValue(window.windowOpacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(finished_callback)
        anim.start()
        window._fade_out_anim = anim
