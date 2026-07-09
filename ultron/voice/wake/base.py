from typing import Callable
from ultron.core.service_manager import UltronService

class WakeWordProvider(UltronService):
    """Abstract interface for wake word detection engines."""
    def __init__(self, name: str = "WakeWordProvider"):
        super().__init__(name)
        self.callback = None
        self.wake_phrase = "arise"

    def initialize(self) -> bool:
        """Initializes the wake word detection engine."""
        return True

    def set_callback(self, callback: Callable[[], None]):
        """Sets the callback to trigger when the wake word is detected."""
        self.callback = callback

    def set_wake_phrase(self, phrase: str):
        """Sets the phrase or word to listen for."""
        self.wake_phrase = phrase.lower().strip()

    def configure(self, config: dict):
        """Configures provider parameters."""
        if "wake_phrase" in config:
            self.set_wake_phrase(config["wake_phrase"])

    def emit(self, text: str):
        """Helper to process speech and check wake matches."""
        self.process_speech(text)

    def process_speech(self, text: str, confidence: float = 1.0):
        """Processes recognized speech text to check for the wake phrase with confidence score."""
        raise NotImplementedError

    def start(self) -> bool:
        self.active = True
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def health(self) -> str:
        return "Running" if self.active else "Offline"

    def status(self) -> str:
        return "Running" if self.active else "Offline"
