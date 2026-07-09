"""
ULTRON Global State Manager — Coordinates Cognitive OS lifecycle states.
"""

from typing import Set

class StateManager:
    ALLOWED_STATES: Set[str] = {
        "Sleeping",
        "Listening",
        "Thinking",
        "Executing",
        "Speaking",
        "Error",
        "Shutdown",
        "Standby",
        "Processing",
        "Responding"
    }

    def __init__(self):
        pass

    @property
    def state(self) -> str:
        """Mirror current state from the authoritative VoiceSessionManager."""
        from ultron.core.voice_session_manager import get_voice_session_manager, VoiceState
        mgr = get_voice_session_manager()
        if mgr:
            # Map state enum to titlecase visual state
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
            return visual_map.get(mgr.state, "Sleeping")
        return "Sleeping"

    def set_state(self, state: str):
        """Ignore direct modifications from outside components."""
        pass

# Singleton Global instance
state_manager = StateManager()
