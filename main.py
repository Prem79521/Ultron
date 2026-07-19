"""
ULTRON Cognitive Operating System — Core bootstrap and service manager runtime.
"""

import sys
import os
import time
import datetime
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Start time for boot tracing
boot_start_time = time.time()
current_boot_stage = "BOOT 01: QApplication created"

def get_boot_log_str(phase: int, message: str) -> str:
    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    elapsed = time.time() - boot_start_time
    return f"BOOT {phase:02d} [{now}] (elapsed: {elapsed:.3f}s): {message}"

def log_boot(phase: int, message: str):
    global current_boot_stage
    current_boot_stage = f"BOOT {phase:02d}: {message}"
    logger = logging.getLogger("ultron-agent")
    logger.info(get_boot_log_str(phase, message))

def log_boot_stage(stage_num: int, description: str, status: str = "PASS", duration_ms: float = 0.0, subsystem: str = "BOOT"):
    import threading
    import datetime
    now_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    thread_name = threading.current_thread().name
    dur_str = f"{duration_ms:.0f} ms" if duration_ms > 0 else "-"
    log_line = f"[{now_str}] [{subsystem}] [{thread_name}] BOOT {stage_num:02d}: {description} | {status} | {dur_str}"
    logging.getLogger("ultron-agent").info(log_line)

# Initialize QApplication immediately if not already created (BOOT 01)
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)
logging.basicConfig(level=logging.INFO)
log_boot(1, "QApplication created")

from ultron.core import CoreSystem
from ultron.core.service_manager import service_manager
from ultron.core.event_bus import event_bus
from ultron.memory import MemoryManager
from ultron.api.memory_api import set_memory_ref
from ultron.hal.hal_manager import init_hal
from ultron.voice.tts.pyttsx3_provider import Pyttsx3VoiceProvider
from ultron.core.ai_core import init_ai_core, get_ai_core
from ultron.core.wake_engine import init_wake_engine
from ultron.voice.engine import enumerate_and_select_microphone
from ultron.core.health_monitor import health_monitor
from ui.application import UltronUIApplication

_main_window_ref = None

def handle_voice_command(text: str):
    """Voice command router mapping callbacks to wake checks or queue execution."""
    text = text.strip()
    if not text:
        return
        
    logging.getLogger("ultron-agent").info(f"VOICE CAPTURED: '{text}'")
    
    from ultron.core.voice_session_manager import get_voice_session_manager, VoiceState
    from ultron.core.ai_core import get_ai_core
    from ultron.core.service_manager import service_manager
    
    # Do not execute the wake word itself as a command
    engine_srv = service_manager.get_service("VoiceEngineService")
    wake_phrase = engine_srv.wake_phrase.lower().strip() if (engine_srv and engine_srv.wake_phrase) else "ultron"
    if text.lower().strip() == wake_phrase:
        logging.getLogger("ultron-agent").info(f"handle_voice_command: Skipping command execution for wake phrase '{text}'.")
        return
        
    mgr = get_voice_session_manager()
    is_sleeping = (mgr.state == VoiceState.SLEEPING) if mgr else True
    is_listening = (mgr.state == VoiceState.LISTENING) if mgr else False
    
    logger = logging.getLogger("ultron-agent")
    logger.info(
        f"Speech Path:\n"
        f"Speech: '{text}'\n"
        f"↓\n"
        f"Wake Detector: {'Active' if is_sleeping else 'Inactive'}\n"
        f"↓\n"
        f"Wake Matched?: {'Pending' if is_sleeping else 'N/A'}\n"
        f"↓\n"
        f"Listening?: {mgr.state.name if mgr else 'SLEEPING'}\n"
        f"↓\n"
        f"AI Core?: {'Routed' if is_listening else 'Ignored (Not Listening)'}\n"
        f"↓\n"
        f"Executed?: {'Yes' if is_listening else 'No'}"
    )
    
    # AI Core must reject commands when VOICE_STATE != LISTENING
    if is_listening:
        global _main_window_ref
        if _main_window_ref:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: _main_window_ref.process_operator_command(text, is_voice=True))
        else:
            ai = get_ai_core()
            if ai:
                ai.execute_command(text)

def verify_runtime_status(main_window, session_mgr, wake):
    failures = []
    
    # 1. SQLite
    from ultron.memory import get_memory_manager
    mem = get_memory_manager()
    if not mem:
        failures.append("SQLite")
        
    # 2. Plugins
    from ultron.core.plugin_loader import get_plugin_loader
    p_loader = get_plugin_loader()
    if not p_loader or not p_loader.available():
        failures.append("Plugins")
        
    # 3. Voice Provider
    if not session_mgr or not session_mgr.voice:
        failures.append("Voice Provider")
        
    # 4. Recognition Provider
    reco_service = service_manager.get_service("VoiceRecognitionService")
    if not reco_service or reco_service.health() == "Offline":
        failures.append("Recognition Provider")
        
    # 5. Wake Provider
    if not wake or not wake.active:
        failures.append("Wake Provider")
        
    # 6. AI Core
    from ultron.core.ai_core import get_ai_core
    ai = get_ai_core()
    if not ai or not ai.queue.worker_thread or not ai.queue.worker_thread.is_alive():
        failures.append("AI Core")
        
    # 7. EventBus
    from ultron.core.event_bus import event_bus
    if not event_bus or event_bus.health().get("status") != "healthy":
        failures.append("EventBus")
        
    # 8. Skills
    skills = main_window.core.get_module("skills_registry")
    if not skills or skills.health().get("status") != "healthy":
        failures.append("Skills")
        
    # 9. Notification Center
    notif = service_manager.get_service("NotificationService")
    if not notif:
        failures.append("Notification Center")
        
    # 10. Health Monitor
    health = service_manager.get_service("HealthMonitorService")
    if not health:
        failures.append("Health Monitor")
        
    # Print status
    logger = logging.getLogger("ultron-agent")
    logger.info("==========================================")
    if not failures:
        logger.info("ULTRON Cognitive OS Runtime Validation: PASS")
    else:
        logger.error("ULTRON Cognitive OS Runtime Validation: FAIL")
        for fail in failures:
            logger.error(f"  - Failed Subsystem: {fail}")
    logger.info("==========================================")

    # Phase 8 Startup Verification
    pipeline_failures = []
    
    # 1. Microphone check
    mic_status = "OPEN"
    try:
        engine_srv = service_manager.get_service("VoiceEngineService")
        if engine_srv:
            if not engine_srv.active_recognizer:
                raise Exception("No active speech recognition provider resolved")
        else:
            raise Exception("VoiceEngineService not found")
    except Exception as e:
        mic_status = "CLOSED"
        pipeline_failures.append(("Microphone", str(e), "Check if default microphone is connected in Windows Sound Settings."))
        
    # 2. Recognition Thread check
    reco_thread_status = "RUNNING"
    try:
        reco_service = service_manager.get_service("VoiceRecognitionService")
        if not reco_service or not reco_service.active:
            raise Exception("VoiceRecognitionService is not running or active")
        engine_srv = service_manager.get_service("VoiceEngineService")
        active_rec = engine_srv.active_recognizer if engine_srv else None
        if not active_rec or not active_rec.thread or not active_rec.thread.is_alive():
            raise Exception("Recognizer thread is not alive")
    except Exception as e:
        reco_thread_status = "OFFLINE"
        pipeline_failures.append(("Recognition Thread", str(e), "Check if speech recognition dependencies or SAPI/Vosk model are installed correctly."))
        
    # 3. Audio Callback check
    callback_status = "ACTIVE"
    try:
        engine_srv = service_manager.get_service("VoiceEngineService")
        active_rec = engine_srv.active_recognizer if engine_srv else None
        if not active_rec or not active_rec.active:
            raise Exception("Audio stream / message loop is inactive")
    except Exception as e:
        callback_status = "INACTIVE"
        pipeline_failures.append(("Audio Callback", str(e), "Check if microphone stream or COM message pump failed to initialize."))
        
    # 4. Recognition check
    recognition_status = "ACTIVE"
    try:
        reco_service = service_manager.get_service("VoiceRecognitionService")
        if not reco_service:
            raise Exception("Recognition service is not registered in service manager")
    except Exception as e:
        recognition_status = "INACTIVE"
        pipeline_failures.append(("Recognition", str(e), "Check if VoiceRecognitionService is declared in service_manager."))
        
    # 5. Wake Detector check
    wake_status = "ACTIVE"
    try:
        wake_detector = service_manager.get_service("WakeDetectorService")
        if not wake_detector or not wake_detector.active:
            raise Exception("WakeDetectorService is not active")
    except Exception as e:
        wake_status = "INACTIVE"
        pipeline_failures.append(("Wake Detector", str(e), "Check if WakeDetectorService is registered or wake engine is configured correctly."))
        
    # 6. Voice Session check
    session_status = "CONNECTED"
    try:
        from ultron.core.voice_session_manager import get_voice_session_manager
        mgr = get_voice_session_manager()
        if not mgr:
            raise Exception("VoiceSessionManager is not initialized")
    except Exception as e:
        session_status = "DISCONNECTED"
        pipeline_failures.append(("Voice Session", str(e), "Check if VoiceSessionManager singleton is instantiated in main initialization sequence."))
        
    # 7. EventBus check
    eb_status = "CONNECTED"
    try:
        from ultron.core.event_bus import event_bus
        if not event_bus or event_bus.health().get("status") != "healthy":
            raise Exception("EventBus is unhealthy or not registered")
    except Exception as e:
        eb_status = "DISCONNECTED"
        pipeline_failures.append(("EventBus", str(e), "Check if global EventBus instance exists or has initialization issues."))

    # Overall calculation
    overall_status = "PASS" if not pipeline_failures else "FAIL"
    
    if overall_status == "PASS":
        status_msg = (
            "VOICE PIPELINE STATUS\n"
            f"Microphone: {mic_status}\n"
            f"Recognition Thread: {reco_thread_status}\n"
            f"Audio Callback: {callback_status}\n"
            f"Recognition: {recognition_status}\n"
            f"Wake Detector: {wake_status}\n"
            f"Voice Session: {session_status}\n"
            f"EventBus: {eb_status}\n"
            f"Overall: {overall_status}"
        )
        print(status_msg)
        logger.info(status_msg)
    else:
        # If any check fails, print the failure diagnostics block
        fail_stage, reason, suggested_fix = pipeline_failures[0]
        failed_msg = (
            "VOICE PIPELINE FAILED\n"
            f"Failure Stage: {fail_stage}\n"
            f"Reason: {reason}\n"
            f"Suggested Fix: {suggested_fix}"
        )
        print(failed_msg)
        logger.error(failed_msg)

def complete_boot_from_ui(main_window, memory, voice, skills):
    """Callback triggered on the main thread after boot screen POST completes."""
    global _main_window_ref
    _main_window_ref = main_window
    import threading
    import logging
    logger = logging.getLogger("ultron-agent")
    logger.info(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] complete_boot_from_ui begins.")
    
    try:
        log_boot(4, "EventBus initialized")
    except Exception as e:
        logger.error(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] Error log_boot(4): {e}", exc_info=True)
    
    # 1. Initialize Voice Session Manager (state starts as BOOTING)
    try:
        from ultron.core.voice_session_manager import init_voice_session_manager, VoiceState
        session_mgr = init_voice_session_manager(voice)
        session_mgr._state = VoiceState.SLEEPING
        service_manager.register_service("VoiceSessionManager", session_mgr)
        log_boot(5, "VoiceSessionManager initialized")
    except Exception as e:
        logger.error(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] Error initializing VoiceSessionManager: {e}", exc_info=True)
    
    # 2. Initialize Wake Engine
    try:
        wake = init_wake_engine(voice)
        service_manager.register_service("WakeService", wake)
        log_boot(6, "WakeEngine initialized")
    except Exception as e:
        logger.error(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] Error initializing WakeEngine: {e}", exc_info=True)
    
    # 3. Initialize Recognition and Wake Detector Services
    try:
        from ultron.voice.engine import VoiceEngineService
        from ultron.voice.wake_detector import WakeDetectorService
        from ultron.voice.recognizer import RecognitionService
        
        voice_engine_srv = VoiceEngineService()
        try:
            voice_engine_srv.resolve_providers()
            # Bind newly created voice provider
            if voice_engine_srv.active_tts and voice:
                voice_engine_srv.active_tts = voice
        except Exception as e:
            logger.error(f"VoiceEngine resolution warning: {e}", exc_info=True)
            
        service_manager.register_service("VoiceEngineService", voice_engine_srv)
        
        listener = RecognitionService(handle_voice_command)
        service_manager.register_service("VoiceRecognitionService", listener)
        
        wake_detector_srv = WakeDetectorService()
        service_manager.register_service("WakeDetectorService", wake_detector_srv)
        
        log_boot(7, "Recognition initialized")
    except Exception as e:
        logger.error(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] Error initializing Recognition services: {e}", exc_info=True)
    
    # Background subsystem registrations
    try:
        from ultron.vision.camera_manager import CameraService
        from ultron.vision.vision_provider import VisionService
        from ultron.vision.gesture_service import GestureService
        from ultron.core.graphics_service import GraphicsService
        from ultron.llm.llm_manager import LlmService
        
        camera_srv = CameraService()
        vision_srv = VisionService()
        gesture_srv = GestureService()
        graphics_srv = GraphicsService()
        llm_srv = LlmService()
        
        service_manager.register_service("CameraService", camera_srv)
        service_manager.register_service("VisionService", vision_srv)
        service_manager.register_service("GestureService", gesture_srv)
        service_manager.register_service("GraphicsService", graphics_srv)
        service_manager.register_service("LlmService", llm_srv)
        
        from ultron.core.notification_center import notification_center
        service_manager.register_service("NotificationService", notification_center)
        service_manager.register_service("HealthMonitorService", health_monitor)
        
        # Register HiddenItemsService
        try:
            from ultron.services.hidden_items_service import HiddenItemsService
            vault_srv = HiddenItemsService(db_path=memory.db_path)
            service_manager.register_service("HiddenItemsService", vault_srv)
        except Exception as e:
            logger.error(f"Failed to register HiddenItemsService: {e}", exc_info=True)
        
        # Register first-class MCP Service
        try:
            from mcp.service import McpService
            mcp_srv = McpService()
            service_manager.register_service("McpService", mcp_srv)
        except Exception as e:
            logger.error(f"Failed to register McpService: {e}", exc_info=True)
        
        log_boot(8, "Plugins initialized")
    except Exception as e:
        logger.error(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] Error initializing plugins/vision services: {e}", exc_info=True)
    
    # Transition: Publish initial SLEEPING state (Phase 2 & 10)
    try:
        event_bus.publish("VOICE_STATE_CHANGED", {
            "state": VoiceState.SLEEPING.name,
            "old_state": VoiceState.SLEEPING.name,
            "extra": {}
        })
    except Exception as e:
        logger.error(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] Error transitioning voice states: {e}", exc_info=True)
    
    # Bind components to MainWindow
    try:
        main_window.bind_providers(memory, voice)
        main_window.skills = skills
    except Exception as e:
        logger.error(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] Error binding MainWindow providers: {e}", exc_info=True)
    
    # Update AI Core
    try:
        ai = get_ai_core()
        if ai:
            ai.memory = memory
            ai.skills = skills
    except Exception as e:
        logger.error(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] Error updating AI Core references: {e}", exc_info=True)
        
    # Expose SpeechService (fast — just dict assignment)
    try:
        if voice:
            service_manager.register_service("SpeechService", voice)
    except Exception as e:
        logger.error(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] Error exposing SpeechService: {e}", exc_info=True)

    # Phase 9 Memory Verification
    try:
        projs = memory.list_records("project", limit=100)
        convs = memory.list_records("conversation", limit=100)
        facts = memory.list_records("preference", limit=100)
        
        if len(projs) == 0 and len(convs) == 0 and len(facts) == 0:
            print("Memory initialized.\n0 Projects\n0 Conversations\n0 Facts\nOperator profile ready.")
            logger.info("Memory initialized.\n0 Projects\n0 Conversations\n0 Facts\nOperator profile ready.")
    except Exception as e:
        logger.error(f"[BOOT TRACK] Error validating memory: {e}")

    # NOTE: service_manager.start_all() is intentionally NOT called here.
    # It runs in ServiceStartupThread (ui/application.py) AFTER MainWindow.show()
    # so the Qt Main Thread is never blocked by model loading.
    logger.info(f"[BOOT TRACK] [Thread: {threading.current_thread().name}] complete_boot_from_ui: service registration complete — start_all deferred to background thread.")


def verify_application_ready(main_window) -> bool:
    logger = logging.getLogger("ultron-agent")

    # 1. Main Window Visible — hard requirement
    if not main_window or not main_window.isVisible():
        logger.warning("[BOOT] UI Readiness: Main Window is NOT visible.")
        return False

    # 2. EventBus Active — hard requirement
    from ultron.core.event_bus import event_bus
    if not event_bus or event_bus.health().get("status") != "healthy":
        logger.warning("[BOOT] UI Readiness: EventBus is NOT active.")
        return False

    # 3. VoiceSessionManager READY/SLEEPING — hard requirement
    from ultron.core.voice_session_manager import get_voice_session_manager, VoiceState
    mgr = get_voice_session_manager()
    if not mgr or mgr.state not in [VoiceState.SLEEPING]:
        logger.warning(f"[BOOT] UI Readiness: VoiceSessionManager NOT ready (State: {mgr.state if mgr else 'None'}).")
        return False

    # 4. Recognition — soft check (Vosk model loads in background thread)
    reco = service_manager.get_service("VoiceRecognitionService")
    if not reco or not reco.is_active():
        logger.warning("[BOOT] UI Readiness: Recognition Service not yet active (may still be initializing).")
        # Do not return False — voice loads async

    # 5. Wake — soft check (starts after recognition engine starts)
    wake = service_manager.get_service("WakeService")
    if not wake or not wake.is_active():
        logger.warning("[BOOT] UI Readiness: Wake Service not yet active (may still be initializing).")
        # Do not return False — starts async

    # 6. Input Enabled
    if not main_window.cmd_input.isEnabled():
        logger.warning("[BOOT] UI Readiness: Command Input is disabled.")
        return False

    return True

def main():
    # Group Windows Taskbar icon using explicit AppUserModelID
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("company.ultron.cognitiveos.1.0.0")
    except Exception:
        pass

    # 1. Initialize core system Stage A
    core = CoreSystem()
    
    # Initialize AI Core without memory/skills initially
    init_ai_core(core, None, None)

    # 2. Start Desktop Runtime UI (Splash screen -> MainWindow)
    ui_app = UltronUIApplication(core)
    log_boot(2, "MainWindow created")
    
    log_boot(3, "MainWindow shown")
    
    # Start event loop
    sys.exit(ui_app.start())

if __name__ == "__main__":
    main()
