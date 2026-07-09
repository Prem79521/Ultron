from typing import Callable
from ultron.core.service_manager import UltronService

class VoiceRecognitionProvider(UltronService):
    """Abstract interface for speech-to-text recognition engines."""
    def __init__(self, name: str = "VoiceRecognitionProvider"):
        super().__init__(name)
        self.callback = None

    def initialize(self) -> bool:
        """Initializes the recognition engine resources."""
        return True

    def set_callback(self, callback: Callable[[str, float], None]):
        """Sets the callback to receive recognized phrases and their confidence."""
        self.callback = callback

    def configure(self, config: dict):
        """Configures the provider parameters."""
        pass

    def emit(self, text: str, confidence: float = 1.0):
        """Emits recognized text to the callback."""
        if self.callback:
            self.callback(text, confidence)

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
