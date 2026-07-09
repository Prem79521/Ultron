from ultron.voice.tts.base import TextToSpeechProvider
import logging

class PiperVoiceProvider(TextToSpeechProvider):
    """Placeholder provider for future Piper local neural TTS synthesis."""
    def __init__(self):
        super().__init__("PiperVoiceProvider")
        self.active = False
        self.logger = logging.getLogger("ultron-agent")

    def speak(self, text: str):
        pass

    def start(self) -> bool:
        self.active = True
        self.logger.info("Piper TTS Provider initialized (Stub).")
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def health(self) -> str:
        return "Offline" if not self.active else "Running"
