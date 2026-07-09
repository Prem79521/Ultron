import logging
from ultron.voice.providers.base import VoiceRecognitionProvider

class WhisperVoiceRecognitionProvider(VoiceRecognitionProvider):
    """Placeholder provider for future offline Faster-Whisper / Whisper.cpp local recognition."""
    def __init__(self):
        super().__init__("WhisperVoiceRecognitionProvider")
        self.active = False
        self.logger = logging.getLogger("ultron-agent")

    def start(self) -> bool:
        self.active = True
        self.logger.info("Whisper Voice Recognition Provider initialized (Stub).")
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def health(self) -> str:
        return "Offline" if not self.active else "Running"
