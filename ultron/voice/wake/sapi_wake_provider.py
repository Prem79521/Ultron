from ultron.voice.wake.base import WakeWordProvider
import logging

class SapiWakeProvider(WakeWordProvider):
    """
    Decoupled Wake Word Detector.
    Scans incoming recognized text for the configured wake phrase.
    """
    def __init__(self):
        super().__init__("SapiWakeProvider")
        self.active = False
        self.logger = logging.getLogger("ultron-agent")

    def process_speech(self, text: str, confidence: float = 1.0):
        import threading, datetime
        print(f"[PIPELINE] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [thread={threading.current_thread().name}] HOP3: SapiWakeProvider.process_speech | active={self.active} | text='{text}'")
        if not self.active:
            return
        
        import string
        def clean_text(t: str) -> str:
            if not t:
                return ""
            t = t.lower().strip()
            t = t.translate(str.maketrans("", "", string.punctuation))
            return " ".join(t.split())

        normalized_text = clean_text(text)
        wake_phrases = [clean_text(p) for p in self.wake_phrase.split(",") if p.strip()]
        
        self.logger.info(f"Wake Detector checking: '{normalized_text}' against configured phrases: {wake_phrases}")
        
        for phrase in wake_phrases:
            if phrase in normalized_text:
                # Log matching exactly as requested by the specification
                self.logger.info(
                    f"Wake Phrase Matched\n\n"
                    f"Phrase:\n{phrase.capitalize()}\n\n"
                    f"Confidence:\n{confidence}\n\n"
                    f"Publishing:\nWAKE_DETECTED"
                )
                import threading, datetime
                print(f"[PIPELINE] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] HOP4: wake callback firing | callback={self.callback}")
                if self.callback:
                    self.callback()
                break

    def start(self) -> bool:
        self.active = True
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def health(self) -> str:
        return "Running" if self.active else "Offline"
