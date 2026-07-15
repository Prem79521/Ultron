import logging
import time
from ultron.core.service_manager import UltronService
from ultron.core.event_bus import event_bus

class RecognitionService(UltronService):
    """
    Service running the active VoiceRecognitionProvider continuously.
    Publishes recognized phrases as events on the Event Bus.
    """
    def __init__(self, callback_func=None):
        # Named "VoiceRecognitionService" for legacy compatibility
        super().__init__("VoiceRecognitionService")
        self.callback = callback_func
        self.logger = logging.getLogger("ultron-agent")
        self.engine_service = None

    def start(self) -> bool:
        self.active = True
        self.logger.info("Starting Recognition Service...")
        
        # Resolve engine service dynamically
        from ultron.core.service_manager import service_manager
        self.engine_service = service_manager.get_service("VoiceEngineService")
        
        if self.engine_service and self.engine_service.active_recognizer:
            self.engine_service.active_recognizer.set_callback(self._handle_speech)
            self.engine_service.active_recognizer.start()
            
        return True

    def stop(self) -> bool:
        self.active = False
        if self.engine_service and self.engine_service.active_recognizer:
            self.engine_service.active_recognizer.stop()
        return True

    def health(self) -> str:
        if not self.active:
            return "Offline"
        if self.engine_service and self.engine_service.active_recognizer:
            return self.engine_service.active_recognizer.health()
        return "Offline"

    def _handle_speech(self, text: str, confidence: float):
        import threading, datetime
        print(f"[PIPELINE] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [thread={threading.current_thread().name}] HOP1: _handle_speech fired | obj={id(self)} | text='{text}'")
        if not self.active:
            return
            
        provider_name = "SAPI"
        if self.engine_service and self.engine_service.active_recognizer:
            rec_name = getattr(self.engine_service.active_recognizer, "name", "")
            provider_name = "Vosk" if "vosk" in rec_name.lower() else "SAPI"
            
        rec_msg = (
            f"Recognized:\n"
            f"\"{text}\"\n"
            f"Confidence: {confidence:.2f}\n"
            f"Provider: {provider_name}\n"
            f"Elapsed: 0.25s"
        )
        print(rec_msg)
        self.logger.info(rec_msg)
        
        # Update diagnostics telemetry in VoiceEngine
        if self.engine_service:
            self.engine_service.diagnostics["last_recognized_phrase"] = text
            self.engine_service.diagnostics["last_confidence_score"] = confidence
            self.engine_service.diagnostics["callback_count"] += 1
            self.engine_service.diagnostics["last_recognition_timestamp"] = time.time()
            self.engine_service.publish_diagnostics()
            
        # Record to SQLite Memory Engine (UME) voice_history
        try:
            from ultron.memory import get_memory_manager
            mem = get_memory_manager()
            if mem:
                import json
                mem.create_record(
                    memory_type="voice_history",
                    title=text,
                    content=json.dumps({
                        "recognized_text": text,
                        "provider": self.engine_service.reco_provider_name if self.engine_service else "vosk",
                        "confidence": confidence,
                        "latency": 0.1,
                        "timestamp": time.time()
                    })
                )
        except Exception as e:
            self.logger.error(f"Failed to save voice history to UME: {e}")

        from ultron.voice.pipeline_tracker import trace_pipeline
        trace_pipeline("SPEECH_RECOGNIZED", f"text='{text}', confidence={confidence:.2f}")

        # Publish to Event Bus
        import datetime
        now_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.logger.info(f"[{now_str}] SPEECH_RECOGNIZED published | timestamp={time.time()}")
        event_bus.publish("SPEECH_RECOGNIZED", {"text": text, "confidence": confidence})
        
        self.logger.info(
            f"Published:\n\n"
            f"SPEECH_RECOGNIZED\n\n"
            f"Text:\n\n"
            f"\"{text}\""
        )
        
        # Invoke callback for legacy routing support
        if self.callback:
            try:
                self.callback(text)
            except Exception as e:
                self.logger.error(f"Legacy speech callback failed: {e}")
