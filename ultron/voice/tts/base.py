from ultron.core.service_manager import UltronService

class TextToSpeechProvider(UltronService):
    """Abstract interface for text-to-speech engines."""
    def __init__(self, name: str = "SpeechService"):
        super().__init__(name)

    def initialize(self) -> bool:
        """Initializes the TTS engine resources."""
        return True

    def speak(self, text: str):
        """Synthesizes text into spoken audio."""
        raise NotImplementedError

    def configure(self, config: dict):
        """Configures provider parameters."""
        pass

    def emit(self, text: str):
        """Emits or speaks the text."""
        self.speak(text)

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
