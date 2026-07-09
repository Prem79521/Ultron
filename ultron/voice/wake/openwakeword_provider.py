from ultron.voice.wake.base import WakeWordProvider
import logging

class OpenWakeWordProvider(WakeWordProvider):
    """Placeholder provider for future OpenWakeWord offline wake engine."""
    def __init__(self):
        super().__init__("OpenWakeWordProvider")
        self.active = False
        self.logger = logging.getLogger("ultron-agent")

    def process_speech(self, text: str, confidence: float = 1.0):
        pass

    def start(self) -> bool:
        self.active = True
        self.logger.info("OpenWakeWord Provider initialized (Stub).")
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def health(self) -> str:
        return "Offline" if not self.active else "Running"
