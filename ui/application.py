"""
ULTRON UI Application — Presentation bootstrap manager running PySide6 QApplication loop.
"""

import sys
import time
import logging
import threading
import datetime
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer, QThread, Signal, Slot
from ui.boot_screen import UltronBootScreen, log_boot_stage
from ui.main_window import UltronMainWindow


class ServiceStartupThread(QThread):
    """
    Runs service_manager.start_all() on a worker thread so the Qt Main Thread
    is never blocked by model loading (e.g. vosk.Model()).

    Emits per-service timing and a startup_complete signal when done.
    """
    service_timed = Signal(str, float)   # (service_name, duration_ms)
    startup_complete = Signal()

    def run(self):
        from ultron.core.service_manager import service_manager
        from ultron.core.event_bus import event_bus
        logger = logging.getLogger("ultron-agent")

        # --- Topological ordering (mirrors service_manager.start_all) ---
        visited, temp_mark, order = set(), set(), []

        def visit(name):
            if name in temp_mark or name in visited:
                return
            temp_mark.add(name)
            srv = service_manager.get_service(name)
            if srv:
                for dep in srv.dependencies:
                    visit(dep)
            temp_mark.discard(name)
            visited.add(name)
            order.append(name)

        for name in list(service_manager._services.keys()):
            visit(name)

        logger.info(f"[ServiceStartupThread] Resolved service order: {order}")
        print(f"[BOOT] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [thread={threading.current_thread().name}] ServiceStartupThread: starting {len(order)} services")

        # --- Timed startup per service ---
        for name in order:
            t0 = time.time()
            try:
                service_manager.start_service(name)
            except Exception as e:
                logger.error(f"[ServiceStartupThread] {name} failed to start: {e}", exc_info=True)
            dur = (time.time() - t0) * 1000
            self.service_timed.emit(name, dur)
            level = "WARNING" if dur > 100 else "INFO"
            msg = f"[ServiceStartupThread] {name}: {dur:.0f} ms{' <- SLOW (>100ms)' if dur > 100 else ''}"
            getattr(logger, level.lower())(msg)
            print(f"[BOOT] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}")

        # --- Post-startup: BOOT_COMPLETED + subscriber log ---
        t_pub = time.time()
        try:
            event_bus.publish("BOOT_COMPLETED", {"status": "SUCCESS"})
            log_boot_stage(15, "BOOT_COMPLETED Published", "PASS", (time.time() - t_pub) * 1000)
        except Exception as e:
            log_boot_stage(15, f"BOOT_COMPLETED Publish Failed: {e}", "FAIL", 0.0)

        try:
            event_bus.log_subscribers()
        except Exception:
            pass

        print(f"[BOOT] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [thread={threading.current_thread().name}] ServiceStartupThread: all services started")
        self.startup_complete.emit()


class UltronUIApplication:
    def __init__(self, core_system):
        self.core = core_system
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.boot_screen = None
        self.main_window = None
        self._service_thread = None  # kept alive as member so GC doesn't collect it

        # Watchdog setup (Phase 10)
        self.watchdog_timer = QTimer()
        self.watchdog_timer.setSingleShot(True)
        self.watchdog_timer.timeout.connect(self._run_boot_watchdog)

    def start(self) -> int:
        """Launches the Splash Boot Screen and starts the QApplication event loop."""
        self.core.logger.info("SYSTEM", "Starting UI presentation layer runtime.")

        thread_name = threading.current_thread().name
        logging.getLogger("ultron-agent").info(
            f"QObject Thread (QApplication): {thread_name} "
            + ("✓ (MainThread)" if thread_name == "MainThread" else "✗ (WorkerThread)")
        )

        self.boot_screen = UltronBootScreen(self.core)
        self.boot_screen.boot_completed.connect(self._on_boot_completed)
        self.boot_screen.start_boot()

        return self.app.exec()

    @Slot(object, object, object, object)
    def _on_boot_completed(self, core, memory, voice, skills):
        """
        Called on the Qt Main Thread after the splash POST finishes.

        Phase A (Main Thread — fast):
          1. Create MainWindow
          2. Register all services  (complete_boot_from_ui)
          3. MainWindow.show()      ← UI is live HERE

        Phase B (ServiceStartupThread — background):
          4. service_manager.start_all() with per-service timing
          5. BOOT_COMPLETED event
          6. verify_application_ready
        """
        t_start = time.time()
        log_boot_stage(12, "complete_boot() Started", "PASS", 0.0)

        self.watchdog_timer.start(15000)  # generous: Vosk model load can take ~10s

        thread_name = threading.current_thread().name
        logging.getLogger("ultron-agent").info(
            f"QObject Thread (ui_application callback): {thread_name} "
            + ("✓ (MainThread)" if thread_name == "MainThread" else "✗ (WorkerThread)")
        )

        # ── Phase A-1: create MainWindow ──────────────────────────────────────
        try:
            t_create = time.time()
            logging.getLogger("ultron-agent").info("Creating MainWindow")
            self.main_window = UltronMainWindow(core, memory, voice)
            log_boot_stage(13, "MainWindow Created", "PASS", (time.time() - t_create) * 1000)
        except Exception as e:
            log_boot_stage(13, f"MainWindow Created Failed: {e}", "FAIL", 0.0)
            logging.getLogger("ultron-agent").error("Exception during MainWindow instantiation", exc_info=True)
            return

        # ── Phase A-2: register services (fast — object construction only) ────
        import main as _main
        try:
            _main.complete_boot_from_ui(self.main_window, memory, voice, skills)
        except Exception as e:
            logging.getLogger("ultron-agent").error(f"Error in complete_boot_from_ui: {e}", exc_info=True)

        # ── Check profile and either show main window or onboarding wizard ────
        from ultron.core.operator import operator_profile_exists, load_operator_profile
        if operator_profile_exists():
            self._show_main_window(core, memory, voice, skills)
        else:
            self.watchdog_timer.stop() # stop watchdog during onboarding
            from ui.onboarding import OperatorOnboardingWizard
            self.wizard = OperatorOnboardingWizard(core, memory, voice, skills)
            
            def handle_onboarding_done():
                self.wizard.close()
                # Load profile and apply settings
                profile = load_operator_profile()
                self.main_window.display_name = profile.get("display_name")
                self.main_window.op_name.setText(self.main_window.display_name)
                self.main_window.greeting_name_lbl.setText(f"{self.main_window.display_name}.")
                
                # Apply HAL permissions based on voice enabled
                from ultron.hal.hal_manager import get_hal_manager
                hal = get_hal_manager()
                if hal:
                    voice_active = profile.get("voice_enabled", False)
                    hal.save_permission("microphone", voice_active)
                    hal.save_permission("speaker", voice_active)
                    self.main_window.mic_toggle.setChecked(voice_active)
                    self.main_window.spk_toggle.setChecked(voice_active)
                
                # Update main settings display
                try:
                    self.main_window.update_operator_settings_display()
                except Exception as e:
                    logging.getLogger("ultron-agent").error(f"Error updating settings: {e}")
                
                # Resume normal boot
                self.watchdog_timer.start(15000)
                self._show_main_window(core, memory, voice, skills)
                
            self.wizard.onboarding_complete.connect(handle_onboarding_done)
            self.wizard.show()
            self.wizard.raise_()
            self.wizard.activateWindow()

    def _show_main_window(self, core, memory, voice, skills):
        t_start = time.time()
        # ── Phase A-3: show the window — Qt event loop becomes responsive ─────
        try:
            t_show = time.time()
            logging.getLogger("ultron-agent").info("MainWindow.show() called")
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
            self.main_window.repaint()
            self.main_window.update()
            logging.getLogger("ultron-agent").info("MainWindow exposed")
            log_boot_stage(14, "MainWindow show()", "PASS", (time.time() - t_show) * 1000)
        except Exception as e:
            log_boot_stage(14, f"MainWindow show() Failed: {e}", "FAIL", 0.0)
            logging.getLogger("ultron-agent").error("Exception showing MainWindow", exc_info=True)

        # Visibility audit
        is_vis = self.main_window.isVisible()
        logging.getLogger("ultron-agent").info(
            f"MainWindow Visibility Audit:\n"
            f"- isVisible(): {is_vis}\n"
            f"- isHidden(): {self.main_window.isHidden()}\n"
            f"- geometry(): {self.main_window.geometry()}"
        )
        if not is_vis:
            logging.getLogger("ultron-agent").warning("MainWindow not visible after show — attempting recovery")
            try:
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()
            except Exception as e:
                logging.getLogger("ultron-agent").error(f"Visibility recovery failed: {e}", exc_info=True)

        if self.main_window.isVisible():
            self.watchdog_timer.stop()
            logging.getLogger("ultron-agent").info("MainWindow is visible. Boot watchdog stopped.")

        log_boot_stage(14, "UI Responsive", "PASS", (time.time() - t_start) * 1000)
        print(f"[BOOT] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [thread=MainThread] MainWindow visible — spawning ServiceStartupThread")

        # ── Phase B: start services on background thread ──────────────────────
        self._service_thread = ServiceStartupThread()
        self._service_thread.service_timed.connect(self._on_service_timed)
        self._service_thread.startup_complete.connect(self._on_services_started)
        self._service_thread.start()

    @Slot(str, float)
    def _on_service_timed(self, name: str, dur_ms: float):
        """Receives per-service timing from background thread (Qt-safe signal)."""
        logging.getLogger("ultron-agent").info(f"[Startup Timing] {name}: {dur_ms:.0f} ms")

    @Slot()
    def _on_services_started(self):
        """Called on Main Thread after all services have started in the background."""
        logger = logging.getLogger("ultron-agent")
        logger.info("[ServiceStartupThread] All services started — running readiness check")
        print(f"[BOOT] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [thread=MainThread] _on_services_started: verifying readiness")

        import main as _main
        from ultron.core.event_bus import event_bus

        if self.main_window and _main.verify_application_ready(self.main_window):
            log_boot_stage(17, "Dashboard Interactive", "PASS", 0.0)
            event_bus.publish("APPLICATION_READY", {"status": "SUCCESS"})
            log_boot_stage(18, "BOOT COMPLETE", "PASS", 0.0)
        else:
            log_boot_stage(17, "Dashboard Interactive Checks Failed (voice services may still be initializing)", "WARNING", 0.0)
            logger.warning("[BOOT] verify_application_ready returned False — voice may still be loading in background")

        # Run verbose pipeline check
        try:
            from ultron.core.voice_session_manager import get_voice_session_manager
            mgr = get_voice_session_manager()
            _main.verify_runtime_status(self.main_window, mgr, None)
        except Exception as e:
            logger.error(f"verify_runtime_status warning: {e}", exc_info=True)

    def _run_boot_watchdog(self):
        logging.getLogger("ultron-agent").error("===== BOOT WATCHDOG TRIGGERED =====")
        thread_name = threading.current_thread().name
        from PySide6.QtWidgets import QApplication
        visible_wins = [w.__class__.__name__ for w in QApplication.topLevelWidgets() if w.isVisible()]

        from ultron.core.service_manager import service_manager
        services = [
            f"{s}: {service_manager.get_service(s).status() if hasattr(service_manager.get_service(s), 'status') else 'Unknown'}"
            for s in service_manager.list_services()
        ]

        from ultron.core.voice_session_manager import get_voice_session_manager
        mgr = get_voice_session_manager()
        voice_state = mgr.state.name if mgr else "None"

        from ultron.core.ai_core import get_ai_core
        ai = get_ai_core()
        q_len = ai.queue.get_count() if ai else 0

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
        return {"status": "healthy", "details": "PySide6 QApplication event loop active."}
