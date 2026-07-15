import logging
import time
from ultron.core.service_manager import UltronService
from ultron.core.event_bus import event_bus
from ultron.core.config_loader import config_loader

def save_preferred_mic(device_name: str, device_index: int, sample_rate: int = 16000):
    logger = logging.getLogger("ultron-agent")
    try:
        from ultron.memory import get_memory_manager
        mem = get_memory_manager()
        if mem:
            records = mem.list_records("voice_settings")
            
            # Update or create preferred_microphone_name
            name_rec = next((r for r in records if r["title"] == "preferred_microphone_name"), None)
            if name_rec:
                mem.update_record("voice_settings", name_rec["id"], {"content": device_name})
            else:
                mem.create_record("voice_settings", title="preferred_microphone_name", content=device_name)
                
            # Update or create preferred_microphone_index
            idx_rec = next((r for r in records if r["title"] == "preferred_microphone_index"), None)
            if idx_rec:
                mem.update_record("voice_settings", idx_rec["id"], {"content": str(device_index)})
            else:
                mem.create_record("voice_settings", title="preferred_microphone_index", content=str(device_index))

            # Update or create recognition_sample_rate
            sr_rec = next((r for r in records if r["title"] == "recognition_sample_rate"), None)
            if sr_rec:
                mem.update_record("voice_settings", sr_rec["id"], {"content": str(sample_rate)})
            else:
                mem.create_record("voice_settings", title="recognition_sample_rate", content=str(sample_rate))
                
            logger.info(f"Saved preferred microphone to SQLite: {device_name} (Index: {device_index}, Rate: {sample_rate})")
    except Exception as e:
        logger.error(f"Failed to save preferred mic to database: {e}")

def enumerate_and_select_microphone(logger=None):
    if logger is None:
        logger = logging.getLogger("ultron-agent")
    import sounddevice as sd
    devices = []
    try:
        devices = sd.query_devices()
    except Exception as e:
        logger.error(f"Failed to query audio devices: {e}")
        return None, None
        
    mics = []
    default_idx = None
    default_name = None
    
    try:
        default_input = sd.default.device[0]
    except Exception:
        default_input = -1
        
    for idx, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            mics.append((idx, d["name"]))
            if idx == default_input:
                default_idx = idx
                default_name = d["name"]
                
    # Log every detected microphone
    logger.info("Detected microphones:\n" + "\n".join([f"[{idx}] {name}" for idx, name in mics]))
    
    # Identify default Windows microphone
    if default_name is None and len(mics) > 0:
        default_idx, default_name = mics[0]
    logger.info(f"Default Windows microphone: {default_name}")
    
    preferred_name = None
    preferred_idx = None
    
    # 1. Load from SQLite
    try:
        from ultron.memory import get_memory_manager
        mem = get_memory_manager()
        if mem:
            records = mem.list_records("voice_settings")
            for r in records:
                if r["title"] == "preferred_microphone_name":
                    preferred_name = r["content"]
                elif r["title"] == "preferred_microphone_index":
                    preferred_idx = int(r["content"])
    except Exception as e:
        logger.error(f"Failed to load preferred mic: {e}")
        
    # Check if preferred exists in current list
    found_preferred = False
    if preferred_name:
        for idx, name in mics:
            if name == preferred_name:
                preferred_idx = idx
                found_preferred = True
                break
                
    if not found_preferred:
        # Check if Microphone (GENERAL WEBCAM) is present
        webcam_idx = None
        webcam_name = None
        for idx, name in mics:
            if "general webcam" in name.lower():
                webcam_idx = idx
                webcam_name = name
                break
                
        if webcam_name:
            preferred_idx = webcam_idx
            preferred_name = webcam_name
            logger.info(f"Forcing preferred microphone: {preferred_name} (Index: {preferred_idx})")
            save_preferred_mic(preferred_name, preferred_idx)
        else:
            # Fall back to default
            preferred_idx = default_idx
            preferred_name = default_name
            
    logger.info(f"Selected:\n{preferred_name}")
    return preferred_name, preferred_idx

# Global registries of known providers (plugins can register themselves here)
RECOGNIZERS = {}
WAKE_DETECTORS = {}
TTS_PROVIDERS = {}

class VoiceEngineService(UltronService):
    """
    Unified voice coordinator that acts as the hardware bridge.
    Chooses and manages active Recognition, Wake, and TTS providers via config.
    """
    def __init__(self):
        super().__init__("VoiceEngineService")
        self.logger = logging.getLogger("ultron-agent")
        
        # Resolve active configurations
        self.reco_provider_name = config_loader.get("voice", "recognizer", "sapi")
        self.wake_provider_name = config_loader.get("voice", "wake", "sapi_wake")
        self.tts_provider_name = config_loader.get("voice", "tts", "pyttsx3")
        self.wake_phrase = config_loader.get("voice", "wake_phrase", "ultron")
        
        self.active_recognizer = None
        self.active_wake = None
        self.active_tts = None

        # Initialization state machine (updated by background VoskThread)
        self.init_state = "UNINITIALIZED"  # UNINITIALIZED|LOADING_MODEL|OPENING_MICROPHONE|STARTING_RECOGNITION|READY|ERROR
        
        self.diagnostics = {
            "current_microphone": "Microphone (GENERAL WEBCAM)",
            "recognition_engine": self.reco_provider_name,
            "wake_engine": self.wake_provider_name,
            "tts_engine": self.tts_provider_name,
            "grammar_loaded": "DictationGrammar",
            "wake_grammar_active": True,
            "dictation_active": True,
            "last_recognized_phrase": "None",
            "last_confidence_score": 0.0,
            "callback_count": 0,
            "com_status": "Healthy",
            "wake_matches": 0,
            "last_recognition_timestamp": 0.0,
            "current_speaker": "Speakers (Realtek High Definition Audio)",
            "last_ai_response": "None",
            "last_error": "None"
        }

        # Subscribe to provider changes
        event_bus.subscribe("RECOGNITION_PROVIDER_CHANGED", self._on_reco_changed)
        event_bus.subscribe("TTS_PROVIDER_CHANGED", self._on_tts_changed)
        event_bus.subscribe("AI_RESPONSE_SPOKEN", self._on_ai_response)
        event_bus.subscribe("ERROR_OCCURRED", self._on_error_occurred)
        event_bus.subscribe("WAKE_DETECTED", self._on_wake_detected)
        event_bus.subscribe("VoiceStarted", self._on_voice_started)
        event_bus.subscribe("VoiceStopped", self._on_voice_stopped)

    def start(self) -> bool:
        self.active = True
        self.logger.info("Starting Voice Engine Service...")
        
        # Enumerate and select preferred microphone
        preferred_name, preferred_idx = enumerate_and_select_microphone(self.logger)
        self.diagnostics["current_microphone"] = preferred_name
        
        # Trace Microphone stage on start
        from ultron.voice.pipeline_tracker import trace_pipeline
        trace_pipeline("Microphone", f"Selected: '{preferred_name}' (Index: {preferred_idx})")
        
        # Instantiate active providers
        self.resolve_providers()
        
        # Pass preferred index to active_recognizer
        if self.active_recognizer:
            if hasattr(self.active_recognizer, "device"):
                self.active_recognizer.device = preferred_idx
            self.active_recognizer.start()  # returns immediately; model loads in VoskThread
            self.init_state = "STARTING_RECOGNITION"
        if self.active_wake:
            self.active_wake.start()
        if self.active_tts:
            self.active_tts.start()
            
        self.publish_diagnostics()
        self.logger.info(
            f"Configured Wake Phrase:\n{self.wake_phrase}"
        )
        return True

    def stop(self) -> bool:
        self.active = False
        if self.active_recognizer:
            self.active_recognizer.stop()
        if self.active_wake:
            self.active_wake.stop()
        if self.active_tts:
            self.active_tts.stop()
        return True

    def health(self) -> str:
        if not self.active:
            return "Offline"
        
        reco_h = self.active_recognizer.health() if self.active_recognizer else "Offline"
        wake_h = self.active_wake.health() if self.active_wake else "Offline"
        tts_h = self.active_tts.health() if self.active_tts else "Offline"
        
        if "Error" in [reco_h, wake_h, tts_h]:
            return "Error"
        if "Offline" in [reco_h, wake_h, tts_h]:
            return "Degraded"
        return "Running"

    def resolve_providers(self):
        """Resolves provider instances from global registries."""
        # 1. Speech Recognition
        if not self.active_recognizer:
            reco_class = RECOGNIZERS.get(self.reco_provider_name)
            if reco_class:
                self.active_recognizer = reco_class()
            else:
                self.logger.error(f"Speech Recognition provider '{self.reco_provider_name}' not found.")
            
        # 2. Wake Word Detector
        if not self.active_wake:
            wake_class = WAKE_DETECTORS.get(self.wake_provider_name)
            if wake_class:
                self.active_wake = wake_class()
                self.active_wake.set_wake_phrase(self.wake_phrase)
            else:
                self.logger.error(f"Wake provider '{self.wake_provider_name}' not found.")
            
        # 3. Text to Speech
        if not self.active_tts:
            tts_class = TTS_PROVIDERS.get(self.tts_provider_name)
            if tts_class:
                self.active_tts = tts_class()
            else:
                self.logger.error(f"TTS provider '{self.tts_provider_name}' not found.")

    def update_wake_phrase(self, new_phrase: str):
        self.wake_phrase = new_phrase.lower().strip()
        if self.active_wake:
            self.active_wake.set_wake_phrase(new_phrase)
        self.diagnostics["current_wake_phrase"] = self.wake_phrase
        self.publish_diagnostics()

    def _on_reco_changed(self, event):
        new_provider = event.payload.get("provider")
        if new_provider and new_provider != self.reco_provider_name:
            self.logger.info(f"Switching Recognition provider to: {new_provider}")
            if self.active_recognizer:
                self.active_recognizer.stop()
                
            self.reco_provider_name = new_provider
            reco_class = RECOGNIZERS.get(new_provider)
            if reco_class:
                self.active_recognizer = reco_class()
                # Restore active callback if set by RecognitionService
                from ultron.core.service_manager import service_manager
                reco_service = service_manager.get_service("VoiceRecognitionService")
                if reco_service and hasattr(reco_service, "_handle_speech"):
                    self.active_recognizer.set_callback(reco_service._handle_speech)
                
                # Print active provider
                self.logger.info(f"Recognition Provider:\n{new_provider.upper()}")
                
                self.active_recognizer.start()
                
            self.diagnostics["recognition_engine"] = new_provider
            self.publish_diagnostics()

    def _on_tts_changed(self, event):
        new_provider = event.payload.get("provider")
        if new_provider and new_provider != self.tts_provider_name:
            self.logger.info(f"Switching TTS provider to: {new_provider}")
            if self.active_tts:
                self.active_tts.stop()
                
            self.tts_provider_name = new_provider
            tts_class = TTS_PROVIDERS.get(new_provider)
            if tts_class:
                self.active_tts = tts_class()
                # Update service_manager registration
                from ultron.core.service_manager import service_manager
                service_manager.register_service("SpeechService", self.active_tts)
                self.active_tts.start()
                
            self.diagnostics["tts_engine"] = new_provider
            self.publish_diagnostics()

    def _on_ai_response(self, event):
        text = event.payload.get("text", "None")
        self.diagnostics["last_ai_response"] = text
        self.publish_diagnostics()

    def _on_error_occurred(self, event):
        err = event.payload.get("error", event.payload.get("message", "Unknown error"))
        self.diagnostics["last_error"] = str(err)
        self.publish_diagnostics()

    def _on_wake_detected(self, event):
        self.diagnostics["wake_matches"] += 1
        self.diagnostics["last_wake_event"] = event.payload.get("timestamp", time.time())
        self.publish_diagnostics()

    def _on_voice_started(self, event):
        from ultron.core.event_bus import event_bus
        event_bus.publish("VOICE_STARTED", {})

    def _on_voice_stopped(self, event):
        from ultron.core.event_bus import event_bus
        event_bus.publish("VOICE_STOPPED", {})

    def switch_microphone(self, device_name: str, device_index: int):
        self.logger.info(f"Switching microphone to {device_name} (Index: {device_index})")
        self.diagnostics["current_microphone"] = device_name
        
        # Save to SQLite
        try:
            from ultron.memory import get_memory_manager
            mem = get_memory_manager()
            if mem:
                records = mem.list_records("voice_settings")
                sample_rate = 16000
                for r in records:
                    if r["title"] == "recognition_sample_rate":
                        sample_rate = int(r["content"])
                save_preferred_mic(device_name, device_index, sample_rate)
        except Exception:
            save_preferred_mic(device_name, device_index)
            
        if self.active_recognizer:
            if hasattr(self.active_recognizer, "device"):
                self.active_recognizer.device = device_index
            if hasattr(self.active_recognizer, "active") and self.active_recognizer.active:
                self.logger.info("Restarting active recognizer stream for microphone switch...")
                self.active_recognizer.stop()
                time.sleep(0.2)
                self.active_recognizer.start()
        self.publish_diagnostics()

    def switch_sample_rate(self, rate: int):
        self.logger.info(f"Switching speech recognition sample rate to {rate} Hz")
        try:
            from ultron.memory import get_memory_manager
            mem = get_memory_manager()
            if mem:
                records = mem.list_records("voice_settings")
                mic_name = self.diagnostics.get("current_microphone", "")
                mic_idx = None
                for r in records:
                    if r["title"] == "preferred_microphone_index":
                        mic_idx = int(r["content"])
                save_preferred_mic(mic_name, mic_idx if mic_idx is not None else 0, rate)
        except Exception:
            pass
            
        if self.active_recognizer:
            if hasattr(self.active_recognizer, "switch_sample_rate"):
                self.active_recognizer.switch_sample_rate(rate)
        self.publish_diagnostics()

    def publish_diagnostics(self):
        """Publishes detailed live diagnostics update to the Event Bus."""
        import os
        from ultron.core.state_manager import state_manager
        
        self.diagnostics["com_status"] = "Healthy" if self.health() == "Running" else "Degraded"
        self.diagnostics["recognition_engine"] = self.reco_provider_name.capitalize() if self.reco_provider_name else "-"
        self.diagnostics["wake_engine"] = self.wake_provider_name
        self.diagnostics["tts_engine"] = self.tts_provider_name
        self.diagnostics["current_wake_phrase"] = self.wake_phrase
        self.diagnostics["recognition_status"] = self.active_recognizer.health() if self.active_recognizer else "Offline"
        self.diagnostics["wake_status"] = self.active_wake.health() if self.active_wake else "Offline"
        self.diagnostics["tts_status"] = self.active_tts.health() if self.active_tts else "Offline"
        
        # Extended fields for Voice Diagnostics Dashboard
        self.diagnostics["microphone"] = self.diagnostics.get("current_microphone", "GENERAL WEBCAM")
        self.diagnostics["status"] = state_manager.state
        self.diagnostics["last_recognized_speech"] = self.diagnostics.get("last_recognized_phrase", "-")
        self.diagnostics["last_wake_phrase"] = self.wake_phrase.capitalize()
        self.diagnostics["recognition_confidence"] = self.diagnostics.get("last_confidence_score", 0.0)
        
        # Query session information from VoiceSessionManager
        session_active = False
        session_timeout = 10
        last_wake_time = 0.0
        last_command = "-"
        last_response = "-"
        convo_id = "-"
        sec_rem = "-"
        timer_active = "Inactive"
        avg_rec_lat = 0.0
        avg_res_lat = 0.0
        last_state_transition = "-"
        
        try:
            from ultron.core.voice_session_manager import get_voice_session_manager, VoiceState
            mgr = get_voice_session_manager()
            if mgr:
                session_active = (mgr.state != VoiceState.SLEEPING)
                session_timeout = mgr.session_timeout
                last_wake_time = mgr.last_wake_time
                last_command = mgr.last_command
                last_response = mgr.last_response
                convo_id = mgr.convo_id
                timer_active = "Active" if mgr.session_timer.isActive() else "Inactive"
                rem_ms = mgr.session_timer.remainingTime()
                sec_rem = f"{rem_ms / 1000.0:.1f} s" if rem_ms >= 0 else "-"
                avg_rec_lat = mgr.avg_recognition_latency
                avg_res_lat = mgr.avg_response_latency
                last_state_transition = mgr.state.name
        except Exception:
            pass

        self.diagnostics["session_active"] = "Yes" if session_active else "No"
        self.diagnostics["session_timeout"] = f"{session_timeout} s"
        self.diagnostics["last_wake_time"] = time.strftime('%H:%M:%S', time.localtime(last_wake_time)) if last_wake_time > 0 else "-"
        self.diagnostics["last_command"] = last_command
        self.diagnostics["last_response"] = last_response
        self.diagnostics["convo_id"] = convo_id
        self.diagnostics["timer_active"] = timer_active
        self.diagnostics["seconds_remaining"] = sec_rem
        self.diagnostics["avg_recognition_latency"] = f"{avg_rec_lat * 1000:.0f} ms"
        self.diagnostics["avg_response_latency"] = f"{avg_res_lat * 1000:.0f} ms"
        self.diagnostics["last_state_transition"] = last_state_transition
        
        # Audio chunks and latency
        audio_chunks = 0
        latency = 0.0
        model_name = "(resolving\u2026)"  # updated from recognizer once model loads
        
        dropped_buffers = 0
        if self.active_recognizer:
            if hasattr(self.active_recognizer, "chunks_received"):
                audio_chunks = self.active_recognizer.chunks_received
            if hasattr(self.active_recognizer, "latency"):
                latency = self.active_recognizer.latency
            if hasattr(self.active_recognizer, "model_name") and self.active_recognizer.model_name:
                model_name = self.active_recognizer.model_name
            if hasattr(self.active_recognizer, "dropped_buffers"):
                dropped_buffers = self.active_recognizer.dropped_buffers
                
        self.diagnostics["audio_chunks"] = audio_chunks
        self.diagnostics["dropped_buffers"] = dropped_buffers
        self.diagnostics["recognition_latency"] = f"{latency * 1000:.0f} ms"
        self.diagnostics["model"] = model_name
        
        # Thread status checks
        self.diagnostics["voice_thread"] = "Running" if (self.active_recognizer and self.active_recognizer.health() == "Running") else self.active_recognizer.health() if self.active_recognizer else "Offline"
        self.diagnostics["wake_thread"] = "Running" if (self.active_wake and self.active_wake.health() == "Running") else "Offline"
        self.diagnostics["init_state"] = self.init_state
        
        # Dynamically query other services and status fields (Phase 5.3)
        try:
            from ultron.core.service_manager import service_manager
            active_srvs = []
            for s in service_manager.list_services():
                srv = service_manager.get_service(s)
                if srv:
                    is_act = srv.is_active() if hasattr(srv, "is_active") else getattr(srv, "active", False)
                    if is_act:
                        active_srvs.append(s)
            self.diagnostics["running_services_count"] = len(active_srvs)
        except Exception:
            self.diagnostics["running_services_count"] = 0

        try:
            from ultron.core.plugin_loader import plugin_loader
            if plugin_loader:
                self.diagnostics["plugin_count"] = len(plugin_loader.loaded_plugins)
            else:
                self.diagnostics["plugin_count"] = 0
        except Exception:
            self.diagnostics["plugin_count"] = 0

        # Check DB Size
        try:
            db_size = os.path.getsize("ultron_memory.db")
            if db_size < 1024 * 1024:
                self.diagnostics["sqlite_size"] = f"{db_size / 1024:.1f} KB"
            else:
                self.diagnostics["sqlite_size"] = f"{db_size / (1024 * 1024):.2f} MB"
        except Exception:
            self.diagnostics["sqlite_size"] = "0 KB"

        # Extra provider/state placeholders
        self.diagnostics["vision_engine"] = "opencv"
        self.diagnostics["llm_engine"] = "Ollama"
        self.diagnostics["camera"] = "GENERAL WEBCAM"
        self.diagnostics["current_skill"] = "CommandDispatcher"
        self.diagnostics["current_project"] = "ULTRON OS"
        
        event_bus.publish("VOICE_DIAGNOSTICS_UPDATE", self.diagnostics)

def register_recognizer(name: str, provider_class):
    RECOGNIZERS[name] = provider_class
    logging.getLogger("ultron-agent").info(f"Registered voice recognition provider plugin: {name}")

def register_wake_detector(name: str, provider_class):
    WAKE_DETECTORS[name] = provider_class
    logging.getLogger("ultron-agent").info(f"Registered wake provider plugin: {name}")

def register_tts_provider(name: str, provider_class):
    TTS_PROVIDERS[name] = provider_class
    logging.getLogger("ultron-agent").info(f"Registered TTS provider plugin: {name}")
