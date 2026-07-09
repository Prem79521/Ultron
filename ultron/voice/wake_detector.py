import logging
import time
from ultron.core.service_manager import UltronService
from ultron.core.event_bus import event_bus
from ultron.core.state_manager import state_manager

class WakeDetectorService(UltronService):
    """
    Decoupled Wake Word Detector Service.
    Subscribes to speech recognition events and processes them using the active WakeWordProvider.
    """
    def __init__(self):
        # Named "WakeDetectorService" for decoupled wake detection
        super().__init__("WakeDetectorService")
        self.logger = logging.getLogger("ultron-agent")
        self.engine_service = None
        
        # Subscribe to speech events
        event_bus.subscribe("SPEECH_RECOGNIZED", self._on_speech_recognized)

    def start(self) -> bool:
        self.active = True
        self.logger.info("Starting Wake Detector Service...")
        
        from ultron.core.service_manager import service_manager
        self.engine_service = service_manager.get_service("VoiceEngineService")
        
        if self.engine_service and self.engine_service.active_wake:
            self.engine_service.active_wake.set_callback(self._on_wake_detected)
            self.engine_service.active_wake.start()
            
        return True

    def stop(self) -> bool:
        self.active = False
        if self.engine_service and self.engine_service.active_wake:
            self.engine_service.active_wake.stop()
        return True

    def health(self) -> str:
        if not self.active:
            return "Offline"
        if self.engine_service and self.engine_service.active_wake:
            return self.engine_service.active_wake.health()
        return "Offline"

    def _on_speech_recognized(self, event):
        if not self.active:
            return
            
        # Only evaluate wake words while Sleeping
        if state_manager.state == "Sleeping":
            text = event.payload.get("text", "")
            confidence = event.payload.get("confidence", 1.0)
            
            from ultron.voice.pipeline_tracker import trace_pipeline
            trace_pipeline("WakeDetector", f"text='{text}'")
            
            import string
            def clean_text(t: str) -> str:
                if not t:
                    return ""
                t = t.lower().strip()
                t = t.translate(str.maketrans("", "", string.punctuation))
                return " ".join(t.split())

            normalized_text = clean_text(text)
            wake_phrases = [clean_text(p) for p in self.engine_service.wake_phrase.split(",") if p.strip()] if self.engine_service else ["arise"]
            
            matched = False
            similarity = 0.0
            for phrase in wake_phrases:
                if phrase in normalized_text:
                    matched = True
                    similarity = 1.0
                    break
                    
            decision = "YES" if matched else "NO"
            matched_str = "YES" if matched else "NO"
            
            wake_msg = (
                f"Incoming Text: {text}\n"
                f"Normalized Text: {normalized_text}\n"
                f"Configured Wake Words: {wake_phrases}\n"
                f"Matched: {matched_str}\n"
                f"Similarity: {similarity:.2f}\n"
                f"Decision: {decision}"
            )
            print(wake_msg)
            self.logger.info(wake_msg)
            
            if text and self.engine_service and self.engine_service.active_wake:
                self.engine_service.active_wake.process_speech(text, confidence)


    def _on_wake_detected(self):
        if not self.active:
            return
            
        from ultron.voice.pipeline_tracker import trace_pipeline
        trace_pipeline("WAKE_DETECTED", "Wake word matched successfully")
        
        self.logger.info("Publishing\nWAKE_DETECTED")
        
        # Publish wake event to Event Bus
        event_bus.publish("WAKE_DETECTED", {"timestamp": time.time()})
        
        # Update diagnostics telemetry
        if self.engine_service:
            self.engine_service.diagnostics["wake_matches"] += 1
            self.engine_service.diagnostics["last_wake_event"] = time.time()
            self.engine_service.publish_diagnostics()
