"""
ULTRON Wake Engine — Listens for wake phrase activation.
"""

import logging
from ultron.core.service_manager import UltronService

class UltronWakeEngine(UltronService):
    """Wake service coordinating wake word detector interfaces with strict public API control."""
    def __init__(self, voice_provider):
        super().__init__("WakeService")
        self.voice = voice_provider
        self.logger = logging.getLogger("ultron-agent")
        self.display_name = "Prem"

    def start(self) -> bool:
        self.active = True
        return True

    def stop(self) -> bool:
        super().stop()
        return True

    def set_display_name(self, name: str):
        self.display_name = name

    def sleep(self):
        """Transitions the system to sleeping state."""
        from ultron.core.voice_session_manager import get_voice_session_manager
        mgr = get_voice_session_manager()
        if mgr:
            mgr.deactivate()

    def wake(self):
        """Triggers the wake pipeline by publishing WAKE_DETECTED."""
        from ultron.core.event_bus import event_bus
        import time
        event_bus.publish("WAKE_DETECTED", {"timestamp": time.time()})

    def is_awake(self) -> bool:
        """Checks if the system is currently awake (i.e. not Sleeping, Booting, or Initializing)."""
        from ultron.core.voice_session_manager import get_voice_session_manager, VoiceState
        mgr = get_voice_session_manager()
        if mgr:
            return mgr.state not in [VoiceState.SLEEPING, VoiceState.BOOTING, VoiceState.INITIALIZING]
        return False

    def current_state(self) -> str:
        """Returns the current state name from the authoritative session manager."""
        from ultron.core.voice_session_manager import get_voice_session_manager
        mgr = get_voice_session_manager()
        if mgr:
            return mgr.state.name
        return "SLEEPING"

    def activate(self):
        """Deprecated API compatibility wrapper."""
        self.logger.warning("Deprecated API called: wake_engine.activate(). Redirecting...")
        self.wake()

    def deactivate(self):
        """Deprecated API compatibility wrapper."""
        self.logger.warning("Deprecated API called: wake_engine.deactivate(). Redirecting...")
        self.sleep()

# Global instance initialized at runtime
wake_engine = None

def init_wake_engine(voice_provider) -> UltronWakeEngine:
    global wake_engine
    wake_engine = UltronWakeEngine(voice_provider)
    return wake_engine

def get_wake_engine() -> UltronWakeEngine:
    global wake_engine
    return wake_engine
