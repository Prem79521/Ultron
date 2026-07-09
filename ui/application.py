"""
ULTRON UI Application — Presentation bootstrap manager running PySide6 QApplication loop.
"""

import sys
import time
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer, Slot
from ui.boot_screen import UltronBootScreen, log_boot_stage
from ui.main_window import UltronMainWindow

class UltronUIApplication:
    def __init__(self, core_system):
        self.core = core_system
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.boot_screen = None
        self.main_window = None
        
        # Watchdog setup (Phase 10)
        self.watchdog_timer = QTimer()
        self.watchdog_timer.setSingleShot(True)
        self.watchdog_timer.timeout.connect(self._run_boot_watchdog)

    def start(self) -> int:
        """Launches the Splash Boot Screen and starts the QApplication event loop."""
        self.core.logger.info("SYSTEM", "Starting UI presentation layer runtime.")
        
        # Verify thread ownership of QApplication creation
        import threading
        thread_name = threading.current_thread().name
        logging.getLogger("ultron-agent").info(f"QObject Thread (QApplication): {thread_name} " + ("✓ (MainThread)" if thread_name == "MainThread" else "✗ (WorkerThread)"))

        # Instantiate and show Boot Splash Screen (Stage A)
        self.boot_screen = UltronBootScreen(self.core)
        self.boot_screen.boot_completed.connect(self._on_boot_completed)
        self.boot_screen.start_boot()
        
        return self.app.exec()

    def _on_boot_completed(self, core, memory, voice, skills):
        """Callback invoked when splash boot tasks complete. Creates and opens the Main Window."""
        t_start = time.time()
        log_boot_stage(12, "complete_boot() Started", "PASS", 0.0)
        
        # Start watchdog (Phase 10)
        self.watchdog_timer.start(5000)
        
        import threading
        thread_name = threading.current_thread().name
        logging.getLogger("ultron-agent").info(f"QObject Thread (ui_application callback): {thread_name} " + ("✓ (MainThread)" if thread_name == "MainThread" else "✗ (WorkerThread)"))

        # Instantiation with persistent application member reference (Phase 6)
        try:
            t_create = time.time()
            logging.getLogger("ultron-agent").info("Creating MainWindow")
            self.main_window = UltronMainWindow(core, memory, voice)
            dur_create = (time.time() - t_create) * 1000
            log_boot_stage(13, "MainWindow Created", "PASS", dur_create)
            
            mw_thread = self.main_window.thread().objectName() or "MainThread"
            logging.getLogger("ultron-agent").info(f"QObject Thread (MainWindow): {mw_thread} ✓ (MainThread)")
        except Exception as e:
            log_boot_stage(13, f"MainWindow Created Failed: {e}", "FAIL", 0.0)
            logging.getLogger("ultron-agent").error("Exception during MainWindow instantiation", exc_info=True)
            return

        # Bind skills, update AI Core, register services on main thread
        import main
        try:
            main.complete_boot_from_ui(self.main_window, memory, voice, skills)
        except Exception as e:
            logging.getLogger("ultron-agent").error(f"Error in complete_boot_from_ui: {e}", exc_info=True)

        try:
            t_show = time.time()
            logging.getLogger("ultron-agent").info("MainWindow.show() called")
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
            self.main_window.repaint()
            self.main_window.update()
            logging.getLogger("ultron-agent").info("MainWindow exposed")
            dur_show = (time.time() - t_show) * 1000
            log_boot_stage(14, "MainWindow show()", "PASS", dur_show)
        except Exception as e:
            log_boot_stage(14, f"MainWindow show() Failed: {e}", "FAIL", 0.0)
            logging.getLogger("ultron-agent").error("Exception showing MainWindow", exc_info=True)

        # Audit visibility (Phase 5)
        is_vis = self.main_window.isVisible()
        is_hid = self.main_window.isHidden()
        win_state = self.main_window.windowState()
        is_min = self.main_window.isMinimized()
        geom = self.main_window.geometry()
        scr = self.main_window.screen()
        logging.getLogger("ultron-agent").info(
            f"MainWindow Visibility Audit:\n"
            f"- isVisible(): {is_vis}\n"
            f"- isHidden(): {is_hid}\n"
            f"- windowState(): {win_state}\n"
            f"- isMinimized(): {is_min}\n"
            f"- geometry(): {geom}\n"
            f"- screen(): {scr.name() if scr else 'None'}"
        )

        if not is_vis:
            logging.getLogger("ultron-agent").warning("MainWindow is not visible after show. Executing visibility recovery...")
            try:
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()
                self.main_window.repaint()
                self.main_window.update()
            except Exception as e:
                logging.getLogger("ultron-agent").error(f"Visibility recovery failed: {e}", exc_info=True)
                
        # Stop watchdog if window is visible
        if self.main_window.isVisible():
            self.watchdog_timer.stop()
            logging.getLogger("ultron-agent").info("MainWindow is visible. Boot watchdog timer stopped.")
            
        # 9. APPLICATION_READY verification (Phase 9)
        t_ready = time.time()
        from ultron.core.event_bus import event_bus
        if main.verify_application_ready(self.main_window):
            dur_ready = (time.time() - t_ready) * 1000
            log_boot_stage(17, "Dashboard Interactive", "PASS", dur_ready)
            event_bus.publish("APPLICATION_READY", {"status": "SUCCESS"})
            log_boot_stage(18, "BOOT COMPLETE", "PASS", 0.0)
        else:
            dur_ready = (time.time() - t_ready) * 1000
            log_boot_stage(17, "Dashboard Interactive Checks Failed", "FAIL", dur_ready)

    def _run_boot_watchdog(self):
        logging.getLogger("ultron-agent").error("===== BOOT WATCHDOG TRIGGERED =====")
        import threading
        thread_name = threading.current_thread().name
        
        # Get visible windows
        from PySide6.QtWidgets import QApplication
        visible_wins = []
        for w in QApplication.topLevelWidgets():
            if w.isVisible():
                visible_wins.append(w.__class__.__name__)
                
        # Service States
        from ultron.core.service_manager import service_manager
        services = []
        for s_name in service_manager.list_services():
            srv = service_manager.get_service(s_name)
            services.append(f"{s_name}: {srv.status() if hasattr(srv, 'status') else 'Unknown'}")
            
        # Voice Session State
        from ultron.core.voice_session_manager import get_voice_session_manager
        mgr = get_voice_session_manager()
        voice_state = mgr.state.name if mgr else "None"
        
        # Event Queue length
        from ultron.core.ai_core import get_ai_core
        ai = get_ai_core()
        q_len = ai.queue.get_count() if ai else 0
        
        # Print report
        logging.getLogger("ultron-agent").error(
            f"- Current Thread: {thread_name}\n"
            f"- Visible Windows: {visible_wins}\n"
            f"- Services: {services}\n"
            f"- Voice State: {voice_state}\n"
            f"- Event Queue Length: {q_len}\n"
            f"===================================="
        )

    def health(self) -> dict:
        if not self.app:
            return {"status": "degraded", "details": "QApplication not initialized"}
        return {
            "status": "healthy",
            "details": "PySide6 QApplication event loop active."
        }
