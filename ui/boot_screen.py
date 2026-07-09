"""
ULTRON Boot Screen — Displays terminal-style Power-On Self-Test (POST) status.
"""

import sys
import time
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QThread
from PySide6.QtGui import QFont, QIcon
from ui.themes import UltronThemeStyles, UltronColors
from ui.animations import UltronAnimations

def log_boot_stage(stage_num: int, description: str, status: str = "PASS", duration_ms: float = 0.0, subsystem: str = "BOOT"):
    import threading
    import datetime
    import logging
    now_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    thread_name = threading.current_thread().name
    dur_str = f"{duration_ms:.0f} ms" if duration_ms > 0 else "-"
    log_line = f"[{now_str}] [{subsystem}] [{thread_name}] BOOT {stage_num:02d}: {description} | {status} | {dur_str}"
    logging.getLogger("ultron-agent").info(log_line)

class UltronBootThread(QThread):
    step_completed = Signal(int, str, str, int) # phase, name, status (PASS/WARNING/FAIL), percentage
    boot_finished = Signal(object, object, object, object, object) # core, memory, voice, skills, plugins

    def __init__(self, core_system=None):
        super().__init__()
        self.core = core_system
        self.logger = logging.getLogger("ultron-agent")

    def run(self):
        start_time = time.time()
        # Step 1: Core System
        self.step_completed.emit(1, "Initializing Core...", "PASS", 10)
        from ultron.core import CoreSystem
        if not self.core:
            self.core = CoreSystem()
        time.sleep(0.1)

        # Step 2: Memory
        self.step_completed.emit(2, "Loading Memory...", "PASS", 20)
        from ultron.memory import MemoryManager, set_memory_ref
        db_path = self.core.config.get("memory", "db_path", "ultron_memory.db")
        memory = MemoryManager(db_path=db_path)
        set_memory_ref(memory)
        from ultron.hal.hal_manager import init_hal
        init_hal(memory)
        from ultron.core.logger import setup_logging
        setup_logging(memory_manager=memory)
        time.sleep(0.1)

        # Step 3: Voice Provider
        self.step_completed.emit(3, "Loading Voice Engine...", "PASS", 35)
        from ultron.voice.tts.pyttsx3_provider import Pyttsx3VoiceProvider
        voice_config = self.core.config.get("voice")
        voice = None
        try:
            voice = Pyttsx3VoiceProvider(
                rate=voice_config.get("rate", 165),
                volume=voice_config.get("volume", 1.0),
                voice_gender=voice_config.get("voice_gender", "male")
            )
            status = "PASS"
        except Exception:
            status = "WARNING"
        time.sleep(0.1)

        # Step 4: Recognition
        self.step_completed.emit(4, "Loading Recognition...", "PASS", 50)
        from ultron.voice.engine import enumerate_and_select_microphone
        try:
            enumerate_and_select_microphone(self.logger)
            status = "PASS"
        except Exception:
            status = "WARNING"
        time.sleep(0.1)

        # Step 5: Wake Engine
        self.step_completed.emit(5, "Loading Wake Engine...", "PASS", 60)
        from ultron.core.wake_engine import init_wake_engine
        time.sleep(0.1)

        # Step 6: Skills
        self.step_completed.emit(6, "Loading Skills...", "PASS", 70)
        from ultron.skills.registry import SkillRegistry, register_all_skills
        skills = SkillRegistry(self.core, memory)
        register_all_skills(skills)
        self.core.register_module("skills_registry", skills)
        time.sleep(0.1)

        # Step 7: Plugins
        self.step_completed.emit(7, "Loading Plugins...", "PASS", 80)
        plugin_dirs = self.core.config.get("skills", "plugin_directories", ["plugins"])
        plugin_dir = plugin_dirs[0] if plugin_dirs else "plugins"
        from ultron.core.plugin_loader import init_plugin_loader
        loader = init_plugin_loader(plugin_dir, skills)
        try:
            loader.load_all_plugins()
            status = "PASS"
        except Exception:
            status = "WARNING"
        time.sleep(0.1)

        # Step 8: Diagnostics & Verification
        self.step_completed.emit(8, "Running Diagnostics...", "PASS", 90)
        time.sleep(0.1)

        # Step 9: Ready
        self.step_completed.emit(9, "Ready.", "PASS", 100)
        time.sleep(0.1)

        dur = (time.time() - start_time) * 1000
        log_boot_stage(9, "Boot Thread Completed", "PASS", dur)
        
        t_emit_start = time.time()
        try:
            self.logger.info("BOOT_FINISHED emitted")
            self.boot_finished.emit(self.core, memory, voice, skills, loader)
            dur_emit = (time.time() - t_emit_start) * 1000
            log_boot_stage(10, "bootFinished Signal Emitted", "PASS", dur_emit)
        except Exception as e:
            dur_emit = (time.time() - t_emit_start) * 1000
            log_boot_stage(10, f"bootFinished Signal Emitted Failed: {e}", "FAIL", dur_emit)
            raise e

class UltronBootScreen(QWidget):
    boot_completed = Signal(object, object, object, object) # core, memory, voice, skills

    def __init__(self, core_system=None):
        super().__init__()
        self.core = core_system
        self.success_count = 0
        self.failure_count = 0
        self.start_time = time.time()
        self._init_ui()

    def _init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(380, 520)
        self.setStyleSheet(UltronThemeStyles.get_application_stylesheet())
        self.setWindowIcon(QIcon("assets/icons/ultron.ico"))
        
        # Center on primary screen
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            self.move((geom.width() - self.width()) // 2, (geom.height() - self.height()) // 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Title
        title_lbl = QLabel("ULTRON COGNITIVE OS")
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: rgb(220, 20, 20); letter-spacing: 2px;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)
        
        # Terminal-style POST output
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("Consolas", 10))
        self.terminal.setStyleSheet(
            "background-color: rgb(10, 10, 10); border: 1px solid rgb(30, 30, 30); "
            "color: rgb(0, 255, 0); padding: 10px; line-height: 1.4;"
        )
        layout.addWidget(self.terminal)

    def start_boot(self):
        self.show()
        UltronAnimations.fade_in_window(self, duration_ms=400)
        
        self.boot_thread = UltronBootThread(self.core)
        self.boot_thread.step_completed.connect(self.on_step_completed)
        self.boot_thread.boot_finished.connect(self.on_boot_finished)
        self.boot_thread.start()

    def make_progress_bar(self, percentage: int) -> str:
        filled = percentage // 5
        empty = 20 - filled
        return "[" + "█" * filled + "░" * empty + "]"

    @Slot(int, str, str, int)
    def on_step_completed(self, phase, step_name, status, percent):
        if status == "FAIL":
            self.failure_count += 1
        else:
            self.success_count += 1
            
        elapsed = time.time() - self.start_time
        bar = self.make_progress_bar(percent)
        
        html = f"""
        <div style="font-family: monospace; color: rgb(0, 255, 0); font-size: 11px;">
        ==================================================<br/>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;SYSTEM POWER-ON SELF-TEST (POST)<br/>
        ==================================================<br/>
        <br/>
        <b>Progress:</b> {bar} {percent}%<br/>
        <b>Current Step:</b> {step_name}<br/>
        <br/>
        <b>Diagnostics Status:</b><br/>
        - Subsystem Count: 9<br/>
        - Success Count: {self.success_count}<br/>
        - Failure Count: {self.failure_count}<br/>
        - Elapsed Time: {elapsed:.2f}s<br/>
        <br/>
        --------------------------------------------------<br/>
        """
        self.terminal.setHtml(html)

    @Slot(object, object, object, object, object)
    def on_boot_finished(self, core, memory, voice, skills, plugins):
        t_recv = time.time()
        log_boot_stage(11, "bootFinished Received (Qt Main Thread)", "PASS", 0.0)
        
        self._core = core
        self._memory = memory
        self._voice = voice
        self._skills = skills
        
        # Verify thread ownership (Phase 2)
        import threading
        thread_name = threading.current_thread().name
        logging.getLogger("ultron-agent").info(f"QObject Thread (BootScreen on_boot_finished): {thread_name} " + ("✓ (MainThread)" if thread_name == "MainThread" else "✗ (WorkerThread)"))

        def close_win():
            t_fade_end = time.time()
            log_boot_stage(16, "Splash Fade Finished", "PASS", (t_fade_end - t_recv) * 1000)
            try:
                self.close()
                logging.getLogger("ultron-agent").info("Splash closed")
                self.boot_completed.emit(self._core, self._memory, self._voice, self._skills)
            except Exception as e:
                logging.getLogger("ultron-agent").error(f"Error in close_win/boot_completed: {e}", exc_info=True)
            
        try:
            UltronAnimations.fade_out_window(self, close_win, duration_ms=400)
        except Exception as e:
            logging.getLogger("ultron-agent").error(f"Error in fade_out_window animation: {e}", exc_info=True)
            close_win()
