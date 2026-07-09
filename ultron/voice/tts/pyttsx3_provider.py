from ultron.voice.tts.base import TextToSpeechProvider
import threading
import logging
from ultron.core import event_bus

class Pyttsx3VoiceProvider(TextToSpeechProvider):
    """Local, offline TTS engine using pyttsx3 and native OS audio frameworks."""
    def __init__(self, rate: int = 165, volume: float = 1.0, voice_gender: str = "male"):
        super().__init__("SpeechService")
        self.rate = rate
        self.volume = volume
        self.voice_gender = voice_gender
        self.lock = threading.Lock()
        self.active = False
        self._init_engine_test()

    def _init_engine_test(self):
        """Pre-check the engine to verify availability of OS audio drivers."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            del engine
        except Exception as e:
            logging.getLogger("ultron-agent").error(f"TTS init test failed: {e}")

    def start(self) -> bool:
        self.active = True
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def speak(self, text: str):
        """Asynchronously triggers voice synthesis on an isolated worker thread."""
        from ultron.hal.hal_manager import get_hal_manager
        hal = get_hal_manager()
        if hal and not hal.is_allowed("speaker"):
            logging.getLogger("ultron-agent").warning("Voice output blocked: Speaker permission is disabled.")
            return
            
        event_bus.publish("AI_RESPONSE_SPOKEN", {"text": text})
            
        def run_thread():
            with self.lock:
                import pyttsx3
                event_bus.publish("VoiceStarted")
                try:
                    engine = pyttsx3.init()
                    engine.setProperty("rate", self.rate)
                    engine.setProperty("volume", self.volume)
                    
                    voices = engine.getProperty("voices")
                    if voices:
                        if self.voice_gender.lower() == "female" and len(voices) > 1:
                            engine.setProperty("voice", voices[1].id)
                        else:
                            engine.setProperty("voice", voices[0].id)
                            
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    logging.getLogger("ultron-agent").error(f"TTS Thread failed: {e}")
                finally:
                    event_bus.publish("VoiceStopped")

        threading.Thread(target=run_thread, daemon=True).start()

    def health(self) -> str:
        if not self.active:
            return "Offline"
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            del engine
            return "Running"
        except Exception:
            return "Error"
