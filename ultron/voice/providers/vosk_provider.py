import os
import json
import queue
import sys
import threading
import logging
import time
import struct
import math
from ultron.voice.providers.base import VoiceRecognitionProvider
from ultron.core.event_bus import event_bus

class VoskVoiceRecognitionProvider(VoiceRecognitionProvider):
    """Fully functional offline Vosk voice recognition provider using sounddevice stream."""
    def __init__(self):
        super().__init__("VoskVoiceRecognitionProvider")
        self.thread = None
        self.active = False
        self.logger = logging.getLogger("ultron-agent")
        self.audio_queue = queue.Queue()
        self.model = None
        self.rec = None
        self.sample_rate = 16000
        self.device = None
        self._initialized = False
        self.model_name = "vosk-model-en-us-0.42-gigaspeech" # Default
        
        self.chunks_received = 0
        self.audio_callback_count = 0
        self.dropped_buffers = 0
        self.latency = 0.0
        self.last_audio_time = time.time()
        self.warning_sent = False
        self.publish_volume = False
        
        # Subscribe to volume test events
        event_bus.subscribe("START_VOLUME_TEST", self._on_start_volume_test)
        event_bus.subscribe("STOP_VOLUME_TEST", self._on_stop_volume_test)

    def _on_start_volume_test(self, event):
        self.publish_volume = True
        
    def _on_stop_volume_test(self, event):
        self.publish_volume = False

    def _initialize_vosk(self) -> bool:
        if self._initialized:
            return True
        try:
            import vosk
            
            # 1. Resolve from SQLite memory manager settings
            model_path = ""
            try:
                from ultron.memory import get_memory_manager
                mem = get_memory_manager()
                if mem:
                    records = mem.list_records("provider_settings", limit=100)
                    for r in records:
                        if r["title"] == "vosk_model_path":
                            path = r["content"]
                            if os.path.exists(path):
                                model_path = path
                                break
            except Exception as e:
                self.logger.warning(f"Vosk: Could not load path from UME: {e}")

            # 2. Resolve from default locations
            if not model_path or not os.path.exists(model_path):
                default_paths = [
                    "models/vosk/vosk-model-en-us-0.22",
                    "models/vosk/vosk-model-en-us-0.22/",
                    "models/vosk-model-en-us-0.42-gigaspeech",
                    "Models/vosk-model-en-us-0.42-gigaspeech",
                    "models/vosk-model-small-en-us-0.15",
                    "vosk-model-small-en-us-0.15",
                    "model"
                ]
                for p in default_paths:
                    if os.path.exists(p):
                        model_path = os.path.abspath(p)
                        break

            if model_path and os.path.exists(model_path):
                self.logger.info(f"Vosk: Loading model from resolved path: '{model_path}'")
                self.model_name = os.path.basename(model_path.rstrip("/\\"))
                self.model = vosk.Model(model_path)
                self.rec = vosk.KaldiRecognizer(self.model, self.sample_rate)
                self._initialized = True
                return True
            else:
                self.logger.error("Vosk: Model directory not found. Auto-download is disabled per instructions.")
                return False
        except Exception as e:
            self.logger.error(f"Vosk initialization failed: {e}")
            return False

    def switch_sample_rate(self, rate: int):
        self.sample_rate = rate
        # Force re-creation of KaldiRecognizer with new sample rate
        if self.model:
            import vosk
            self.rec = vosk.KaldiRecognizer(self.model, self.sample_rate)
        if self.active:
            self.logger.info("Restarting active recognizer stream for sample rate switch...")
            self.stop()
            time.sleep(0.2)
            self.start()

    def start(self) -> bool:
        if self.active:
            return True
        
        # Verify Vosk & Sounddevice can be loaded
        if not self._initialize_vosk():
            self.logger.error("Vosk Recognition Provider cannot start because dependencies or model are unavailable.")
            event_bus.publish("VOSK_MODEL_MISSING", {"message": "Vosk model not found"})
            return False

        # Enforce exclusive microphone access by stopping SAPI if active
        from ultron.core.service_manager import service_manager
        reco_service = service_manager.get_service("VoiceEngineService")
        if reco_service and reco_service.active_recognizer and reco_service.active_recognizer != self:
            if reco_service.active_recognizer.active:
                self.logger.info(f"Stopping active recognizer '{reco_service.active_recognizer.name}' to prevent concurrent mic access.")
                reco_service.active_recognizer.stop()
            
        self.active = True
        self.thread = threading.Thread(target=self._run, name="VoskRecognitionThread", daemon=True)
        self.logger.info("Recognition Thread Created")
        self.thread.start()
        self.logger.info("Recognition Thread Started")
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def health(self) -> str:
        if not self.active:
            return "Offline"
        if self._initialized and self.model:
            return "Running"
        return "Error"

    def _handle_reconnect(self):
        """Attempts to reconnect to the saved device index/name in a loop."""
        import sounddevice as sd
        
        # Publish warning
        event_bus.publish("WARNING_OCCURRED", {"message": "Microphone disconnected! Attempting automatic recovery..."})
        
        reconnect_attempts = 0
        max_attempts = 3
        
        while self.active and reconnect_attempts < max_attempts:
            reconnect_attempts += 1
            self.logger.info(f"Reconnection attempt {reconnect_attempts}/{max_attempts}...")
            
            # Load preferred name from database
            preferred_name = ""
            preferred_idx = None
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
            except Exception:
                pass
                
            if not preferred_name:
                preferred_name = "GENERAL WEBCAM"
                
            devices = []
            try:
                devices = sd.query_devices()
            except Exception:
                pass
                
            found_idx = None
            for idx, d in enumerate(devices):
                if d.get("max_input_channels", 0) > 0:
                    if preferred_name.lower() in d["name"].lower() or d["name"] == preferred_name:
                        found_idx = idx
                        break
                        
            if found_idx is not None:
                self.logger.info(f"Microphone found! Reconnected to: {preferred_name} (Index: {found_idx})")
                self.device = found_idx
                # Restart the recognition loop thread
                self.thread = threading.Thread(target=self._run, name="VoskRecognitionThread", daemon=True)
                self.thread.start()
                return
                
            time.sleep(2.0)
            
        # Reconnection failed. Prompt user to choose another mic.
        self.logger.error("Automatic microphone recovery failed.")
        event_bus.publish("ERROR_OCCURRED", {
            "message": "Preferred microphone unavailable. Please select another microphone in Settings."
        })

    def _run(self):
        self.logger.info("Recognition Loop Running")
        import sounddevice as sd
        from ultron.voice.pipeline_tracker import trace_pipeline, pipeline_broken
        
        self.chunks_received = 0
        self.last_audio_time = time.time()
        self.latency = 0.0
        self.warning_sent = False
        
        # Resolve device index dynamically in case it's not set
        if self.device is None:
            try:
                from ultron.memory import get_memory_manager
                mem = get_memory_manager()
                if mem:
                    records = mem.list_records("voice_settings")
                    for r in records:
                        if r["title"] == "preferred_microphone_index":
                            self.device = int(r["content"])
                            break
            except Exception:
                pass
                
        # Validate audio config
        preferred_name = "Default Microphone"
        device_exists = False
        device_available = False
        
        try:
            if self.device is not None:
                device_info = sd.query_devices(self.device, 'input')
                device_exists = True
                preferred_name = device_info["name"]
        except Exception:
            pass
            
        if device_exists:
            try:
                test_stream = sd.RawInputStream(samplerate=self.sample_rate, device=self.device, dtype='int16', channels=1)
                test_stream.close()
                device_available = True
            except Exception:
                pass
                
        status_ok = device_exists and device_available
        if not status_ok:
            pipeline_broken("Microphone", f"Audio device status failed. Exists: {device_exists}, Available: {device_available}")
            
        # Display Phase 1 Microphone Ownership details
        mic_msg = (
            f"Provider Started: VoskVoiceRecognitionProvider\n"
            f"Microphone Opened: {preferred_name}\n"
            f"Device Index: {self.device if self.device is not None else 0}\n"
            f"Device Name: {preferred_name}\n"
            f"Audio Format: 16-bit PCM\n"
            f"Sample Rate: {self.sample_rate}\n"
            f"Channels: 1\n"
            f"Stream Active: Yes\n"
            f"Callback Active: Yes"
        )
        print(mic_msg)
        self.logger.info(mic_msg)
        
        self.logger.info("Recognition Provider:\nVosk")
        
        # Trace Microphone stage
        trace_pipeline("Microphone", f"Device: {preferred_name}")

        def audio_callback(indata, frames, time_info, status):
            """This is called for each audio block from the sounddevice stream."""
            if status:
                self.logger.warning(f"Vosk audio stream status: {status}")
                pipeline_broken("Microphone", f"sounddevice status warning: {status}")
                
            self.audio_queue.put(bytes(indata))
            
            self.audio_callback_count += 1
            
            # Calculate RMS, Peak, and Energy
            data_bytes = bytes(indata)
            count = len(data_bytes) // 2
            peak = 0
            energy = 0.0
            rms = 0.0
            if count > 0:
                try:
                    shorts = struct.unpack(f"{count}h", data_bytes)
                    peak = max(abs(x) for x in shorts)
                    energy = sum(float(x) * float(x) for x in shorts)
                    rms = math.sqrt(energy / count)
                except Exception:
                    pass
                    
            cb_msg = (
                f"Audio callback #{self.audio_callback_count}\n"
                f"Frames received: {frames}\n"
                f"Energy: {energy:.2f}\n"
                f"Peak: {peak}\n"
                f"RMS: {rms:.2f}"
            )
            print(cb_msg)
            self.logger.info(cb_msg)
            
            self.logger.info("Receiving Audio...")
            
            # Live volume meter event
            if self.publish_volume:
                try:
                    data_bytes = bytes(indata)
                    count = len(data_bytes) // 2
                    if count > 0:
                        shorts = struct.unpack(f"{count}h", data_bytes)
                        rms = math.sqrt(sum(x * x for x in shorts) / count)
                        event_bus.publish("VOLUME_LEVEL_CHANGED", {"level": float(rms)})
                except Exception:
                    pass

        try:
            # Open the sounddevice input stream
            try:
                stream = sd.RawInputStream(samplerate=self.sample_rate, blocksize=2048, device=self.device,
                                           dtype='int16', channels=1, callback=audio_callback)
            except Exception as e:
                print("MICROPHONE FAILED TO OPEN")
                self.logger.error(f"MICROPHONE FAILED TO OPEN: {e}")
                raise e
                
            with stream:
                self.logger.info("Vosk input stream active. Listening...")
                self.last_audio_time = time.time()
                
                while self.active:
                    self.logger.info("Recognition Loop Waiting")
                    try:
                        data = self.audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        # Watchdog check: If no audio arrives for more than 5 seconds
                        if time.time() - self.last_audio_time > 5.0 and not self.warning_sent:
                            self.logger.warning("WARNING:\nNo microphone audio detected.")
                            pipeline_broken("Audio Buffer", "No microphone audio detected for >5 seconds.")
                            event_bus.publish("WARNING_OCCURRED", {"message": "WARNING:\nNo microphone audio detected."})
                            self.warning_sent = True
                        continue
                        
                    self.chunks_received += 1
                    self.last_audio_time = time.time()
                    self.warning_sent = False
                    
                    # Log Audio chunk received
                    self.logger.info(
                        f"Audio chunk received\n\n"
                        f"Bytes:\n{len(data)}\n\n"
                        f"Timestamp:\n{time.time():.4f}\n\n"
                        f"Chunks received:\n{self.chunks_received}"
                    )
                    
                    trace_pipeline("Recognition Provider", f"Vosk decoding chunk {self.chunks_received}")
                    
                    # Process with Vosk
                    start_time = time.time()
                    accept = self.rec.AcceptWaveform(data)
                    self.latency = time.time() - start_time
                    
                    # Log AcceptWaveform()
                    self.logger.info(
                        f"AcceptWaveform()\n\n"
                        f"Result:\n{accept}"
                    )
                    
                    if accept:
                        result_str = self.rec.Result()
                        result_dict = json.loads(result_str)
                        text = result_dict.get("text", "").strip()
                        if text:
                            self.logger.info(f"Recognized:\n\"{text}\"")
                            trace_pipeline("Microphone", f"Audio captured for phrase '{text}'")
                            trace_pipeline("Recognition callback", f"text='{text}', confidence=1.0")
                            if self.callback:
                                self.callback(text, 1.0)
                    else:
                        partial_str = self.rec.PartialResult()
                        partial_dict = json.loads(partial_str)
                        partial_text = partial_dict.get("partial", "").strip()
                        if partial_text:
                            self.logger.info(f"Partial:\n\"{partial_text}\"")
                            
                # Read remaining text
                final_str = self.rec.FinalResult()
                final_dict = json.loads(final_str)
                text = final_dict.get("text", "").strip()
                if text:
                    self.logger.info(f"Recognized:\n\"{text}\"")
                    trace_pipeline("Microphone", f"Audio captured for phrase '{text}'")
                    trace_pipeline("Recognition callback", f"text='{text}', confidence=1.0")
                    if self.callback:
                        self.callback(text, 1.0)
                        
        except Exception as e:
            self.logger.error(f"Vosk recognition loop crashed: {e}")
            pipeline_broken("Recognition Provider", f"Vosk crash exception: {e}")
            if self.active:
                self.logger.info("Attempting automatic reconnection recovery...")
                self._handle_reconnect()
        finally:
            self.active = False
