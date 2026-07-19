"""
ULTRON Voice Session Manager — The central authority managing the conversational lifecycle.
"""

import logging
import time
import threading
from enum import Enum
from PySide6.QtCore import QObject, Signal, Slot, QTimer, Qt
from ultron.core.event_bus import event_bus
from ultron.core.service_manager import UltronService

class VoiceState(Enum):
    SLEEPING = "SLEEPING"
    WAKING = "WAKING"
    GREETING = "GREETING"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    RESPONDING = "RESPONDING"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"

class VoiceSessionManagerSignals(QObject):
    transition_triggered = Signal(object, dict) # target_state (VoiceState), extra
    start_timer_triggered = Signal()
    stop_timer_triggered = Signal()

class UltronVoiceSessionManager(UltronService):
    """Authoritative state controller managing voice conversation sessions and timers thread-safely."""
    def __init__(self, voice_provider):
        super().__init__("VoiceSessionManager")
        self.voice = voice_provider
        self.logger = logging.getLogger("ultron-agent")
        try:
            from ultron.core.operator import load_operator_profile
            self.display_name = load_operator_profile().get("display_name", "Prem")
        except Exception:
            self.display_name = "Prem"
        self.session_timeout = 10
        
        self._creation_thread_id = threading.get_ident()
        self._state = VoiceState.SLEEPING
        
        # Telemetry metrics
        self.last_wake_time = 0.0
        self.last_command = "-"
        self.last_response = "-"
        self.convo_id = "convo_" + str(int(time.time()))
        
        self.wake_count = 0
        self.commands_processed = 0
        self.responses_spoken = 0
        
        self.recognition_latencies = []
        self.response_latencies = []
        self.ai_durations = []
        self.pending_confirmation = None
        
        # Thread-safe Qt signal bridge
        self.signals = VoiceSessionManagerSignals()
        self.signals.transition_triggered.connect(self._do_transition, Qt.ConnectionType.QueuedConnection)
        self.signals.start_timer_triggered.connect(self._do_start_timer, Qt.ConnectionType.QueuedConnection)
        self.signals.stop_timer_triggered.connect(self._do_stop_timer, Qt.ConnectionType.QueuedConnection)
        
        # 10s Timeout Timer
        self.session_timer = QTimer()
        self.session_timer.setSingleShot(True)
        self.session_timer.timeout.connect(self._on_timeout_expired)
        
        self._subscribe_events()

    @property
    def voice_provider(self):
        """Dynamically resolve active SpeechService provider from manager."""
        from ultron.core.service_manager import service_manager
        tts_service = service_manager.get_service("SpeechService")
        if tts_service:
            return tts_service
        return self.voice

    def _subscribe_events(self):
        self.subscribe_event("WAKE_DETECTED", self.on_wake_detected)
        self.subscribe_event("COMMAND_RECEIVED", self.on_command_received)
        self.subscribe_event("COMMAND_COMPLETED", self.on_command_completed)
        self.subscribe_event("VoiceStarted", self.on_voice_started)
        self.subscribe_event("VoiceStopped", self.on_voice_stopped)
        self.subscribe_event("RECOGNITION_TELEMETRY", self.on_recognition_telemetry)

    @property
    def state(self) -> VoiceState:
        return self._state

    def transition_to(self, target_state: VoiceState, extra=None):
        if threading.get_ident() == self._creation_thread_id:
            self._do_transition(target_state, extra or {})
        else:
            self.signals.transition_triggered.emit(target_state, extra or {})

    def activate(self):
        """Public activation path."""
        if self._state == VoiceState.SLEEPING:
            self.on_wake_detected(None)

    def deactivate(self):
        """Public deactivation path."""
        self.transition_to(VoiceState.SLEEPING)
        self.signals.stop_timer_triggered.emit()

    @Slot(object, dict)
    def _do_transition(self, target_state: VoiceState, extra):
        old_state = self._state
        if old_state == target_state:
            return
            
        self._state = target_state
        
        # Phase 6 transition audit print
        transition_msg = (
            f"Current State: {old_state.name}\n"
            f"Incoming Event: STATE_TRANSITION\n"
            f"Next State: {target_state.name}"
        )
        print(transition_msg)
        self.logger.info(transition_msg)
        
        # Log transition formatted specifically for Step 8 visualization
        self.logger.info(
            f"VOICE SESSION TRANSITION:\n"
            f"{old_state.name}\n"
            f"↓\n"
            f"{target_state.name}"
        )
        
        # Publish voice state change to event bus
        event_bus.publish("VOICE_STATE_CHANGED", {
            "state": target_state.name,
            "old_state": old_state.name,
            "extra": extra
        })
        
        # Keep old STATE_CHANGED event published for visual component backwards-compatibility
        visual_map = {
            VoiceState.SLEEPING: "Sleeping",
            VoiceState.WAKING: "Speaking",
            VoiceState.GREETING: "Speaking",
            VoiceState.LISTENING: "Listening",
            VoiceState.PROCESSING: "Thinking",
            VoiceState.RESPONDING: "Speaking",
            VoiceState.TIMEOUT: "Speaking",
            VoiceState.ERROR: "Error"
        }
        event_bus.publish("STATE_CHANGED", {
            "state": visual_map.get(target_state, "Sleeping"),
            "old_state": visual_map.get(old_state, "Sleeping")
        })

    def start(self) -> bool:
        self.active = True
        return True

    def stop(self) -> bool:
        super().stop()
        if threading.get_ident() == self._creation_thread_id:
            self.session_timer.stop()
        else:
            self.signals.stop_timer_triggered.emit()
        return True

    def set_display_name(self, name: str):
        self.display_name = name

    def on_wake_detected(self, event):
        if self._state == VoiceState.SLEEPING:
            self.wake_count += 1
            self.last_wake_time = time.time()
            self.convo_id = "convo_" + str(int(time.time()))
            
            # Phase 6 transition audit print for wake detected
            wake_transition_msg = (
                f"Current State: SLEEPING\n"
                f"Incoming Event: WAKE_DETECTED\n"
                f"Next State: WAKING"
            )
            print(wake_transition_msg)
            self.logger.info(wake_transition_msg)
            
            from ultron.voice.pipeline_tracker import trace_pipeline
            trace_pipeline("VoiceSessionManager", "Transitioning state to WAKING")
            
            self.transition_to(VoiceState.WAKING)
            
            # Speak greeting
            dialogue = f"Yes, {self.display_name}."
            voice = self.voice_provider
            if voice:
                voice.speak(dialogue)
            event_bus.publish("WAKE_TRIGGERED", {"message": dialogue})

    def on_command_received(self, event):
        cmd = event.payload.get("command", "")
        self.last_command = cmd
        self.commands_processed += 1
        if self._state == VoiceState.LISTENING:
            self._command_start_time = time.time()
            self.signals.stop_timer_triggered.emit()
            
            from ultron.voice.pipeline_tracker import trace_pipeline
            trace_pipeline("VoiceSessionManager", f"Transitioning state to PROCESSING for command '{cmd}'")
            
            self.transition_to(VoiceState.PROCESSING)

    def on_command_completed(self, event):
        # Calculate response latency
        if hasattr(self, "_command_start_time"):
            dur = time.time() - self._command_start_time
            self.response_latencies.append(dur)
            self.ai_durations.append(dur) # AI latency
            if len(self.response_latencies) > 20:
                self.response_latencies.pop(0)
            if len(self.ai_durations) > 20:
                self.ai_durations.pop(0)
                
        # Store response if available in result
        result = event.payload.get("result", {})
        if isinstance(result, dict) and "response" in result:
            self.last_response = result["response"]
            
        if self._state == VoiceState.PROCESSING:
            # Command execution completed.
            # We delay slightly (50ms) to check if speaking was started.
            # If speaking hasn't started after command execution, return to Listening.
            QTimer.singleShot(100, self._check_post_command_state)

    def _check_post_command_state(self):
        # If we are still in PROCESSING state (meaning no speech started), return to LISTENING
        if self._state == VoiceState.PROCESSING:
            self.transition_to(VoiceState.LISTENING)
            self.signals.start_timer_triggered.emit()

    def on_voice_started(self, event):
        if self._state == VoiceState.WAKING:
            self.transition_to(VoiceState.GREETING)
        elif self._state == VoiceState.PROCESSING:
            self.transition_to(VoiceState.RESPONDING)

    def on_voice_stopped(self, event):
        if self._state == VoiceState.GREETING:
            self.transition_to(VoiceState.LISTENING)
            self.signals.start_timer_triggered.emit()
        elif self._state == VoiceState.RESPONDING:
            self.responses_spoken += 1
            self.transition_to(VoiceState.LISTENING)
            self.signals.start_timer_triggered.emit()
        elif self._state == VoiceState.TIMEOUT:
            self.transition_to(VoiceState.SLEEPING)

    def on_recognition_telemetry(self, event):
        # Capture recognition duration/latency
        latency = event.payload.get("latency", 0.0)
        if latency > 0:
            self.recognition_latencies.append(latency)
            if len(self.recognition_latencies) > 20:
                self.recognition_latencies.pop(0)

    @property
    def avg_recognition_latency(self) -> float:
        if not self.recognition_latencies:
            return 0.0
        return sum(self.recognition_latencies) / len(self.recognition_latencies)

    @property
    def avg_response_latency(self) -> float:
        if not self.response_latencies:
            return 0.0
        return sum(self.response_latencies) / len(self.response_latencies)

    @property
    def avg_ai_time(self) -> float:
        if not self.ai_durations:
            return 0.0
        return sum(self.ai_durations) / len(self.ai_durations)

    @Slot()
    def _do_start_timer(self):
        self.session_timer.stop()
        self.session_timer.start(self.session_timeout * 1000)
        self.logger.info("Voice session timer started.")

    @Slot()
    def _do_stop_timer(self):
        self.session_timer.stop()
        self.logger.info("Voice session timer stopped.")

    @Slot()
    def session_timer_stop_slot(self):
        self.session_timer.stop()

    def _on_timeout_expired(self):
        if self._state == VoiceState.LISTENING:
            self.transition_to(VoiceState.TIMEOUT)
            standby_msg = "Standing by."
            voice = self.voice_provider
            if voice:
                voice.speak(standby_msg)
            event_bus.publish("SLEEP_TRIGGERED", {"message": standby_msg})

    def transition_to_error(self, err_msg: str):
        self.transition_to(VoiceState.ERROR, {"error": err_msg})

# Global singleton
voice_session_manager = None

def init_voice_session_manager(voice_provider) -> UltronVoiceSessionManager:
    global voice_session_manager
    voice_session_manager = UltronVoiceSessionManager(voice_provider)
    return voice_session_manager

def get_voice_session_manager() -> UltronVoiceSessionManager:
    global voice_session_manager
    return voice_session_manager
