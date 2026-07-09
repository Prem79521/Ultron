from ultron.voice.tts.base import TextToSpeechProvider
import logging

class FutureVoiceProvider(TextToSpeechProvider):
    """Placeholder provider for future custom TTS engines."""
    def __init__(self):
        super().__init__("FutureVoiceProvider")
        self.active = False
        self.logger = logging.getLogger("ultron-agent")

    def speak(self, text: str):
        pass

    def start(self) -> bool:
        self.active = True
        self.logger.info("Future TTS Provider initialized (Stub).")
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def health(self) -> str:
        return "Offline" if not self.active else "Running"
