"""
ULTRON Voice Subsystem — Modular, provider-driven voice architecture.
"""

# Import base interfaces
from ultron.voice.providers.base import VoiceRecognitionProvider
from ultron.voice.wake.base import WakeWordProvider
from ultron.voice.tts.base import TextToSpeechProvider

# Import built-in providers
from ultron.voice.providers.sapi_provider import SapiDictationRecognitionProvider
from ultron.voice.providers.vosk_provider import VoskVoiceRecognitionProvider
from ultron.voice.providers.whisper_provider import WhisperVoiceRecognitionProvider
from ultron.voice.providers.future_provider import FutureVoiceRecognitionProvider

from ultron.voice.wake.sapi_wake_provider import SapiWakeProvider
from ultron.voice.wake.openwakeword_provider import OpenWakeWordProvider
from ultron.voice.wake.future_provider import FutureWakeProvider

from ultron.voice.tts.pyttsx3_provider import Pyttsx3VoiceProvider
from ultron.voice.tts.piper_provider import PiperVoiceProvider
from ultron.voice.tts.future_provider import FutureVoiceProvider

# Import core engine and services
from ultron.voice.engine import (
    VoiceEngineService,
    register_recognizer,
    register_wake_detector,
    register_tts_provider
)
from ultron.voice.recognizer import RecognitionService
from ultron.voice.wake_detector import WakeDetectorService

# Register built-in providers automatically
register_recognizer("sapi", SapiDictationRecognitionProvider)
register_recognizer("vosk", VoskVoiceRecognitionProvider)
register_recognizer("whisper", WhisperVoiceRecognitionProvider)
register_recognizer("future", FutureVoiceRecognitionProvider)

register_wake_detector("sapi_wake", SapiWakeProvider)
register_wake_detector("openwakeword", OpenWakeWordProvider)
register_wake_detector("future", FutureWakeProvider)

register_tts_provider("pyttsx3", Pyttsx3VoiceProvider)
register_tts_provider("piper", PiperVoiceProvider)
register_tts_provider("future", FutureVoiceProvider)

# Map Pyttsx3VoiceProvider for backward-compatibility with main.py boot signature
class Pyttsx3VoiceProviderCompat:
    """Wrapper that routes speak() calls to the active SpeechOutputService."""
    def __init__(self, *args, **kwargs):
        pass

    def speak(self, text: str):
        from ultron.core.service_manager import service_manager
        tts_service = service_manager.get_service("SpeechService")
        if tts_service:
            tts_service.speak(text)
        else:
            # Direct pyttsx3 fallback
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass

    def health(self) -> dict:
        from ultron.core.service_manager import service_manager
        tts_service = service_manager.get_service("SpeechService")
        if tts_service:
            return {"status": "healthy" if tts_service.health() == "Running" else "degraded"}
        return {"status": "degraded"}

# Export classes
SapiSpeechListener = RecognitionService
