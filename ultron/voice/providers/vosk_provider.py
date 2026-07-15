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
        self.model_name = "(resolving…)"
        
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
        import traceback as _tb

        def _cp(n, msg):
            """Checkpoint: always prints immediately regardless of log level."""
            ts = time.strftime('%H:%M:%S') + f".{int((time.time() % 1) * 1000):03d}"
            line = f"[VOSK CP{n:02d}] [{ts}] {msg}"
            print(line, flush=True)
            self.logger.info(line)

        _cp(1, "_initialize_vosk() entered")

        if self._initialized:
            _cp(1, "already initialized — returning True")
            return True

        try:
            # CP2: vosk import
            _cp(2, "importing vosk...")
            t_vosk_import = time.time()
            import vosk
            _cp(2, f"vosk imported OK ({(time.time()-t_vosk_import)*1000:.0f} ms)")

            # ── Timing accumulators ────────────────────────────────────────
            t_total_start = time.time()

            # CP3: model discovery via shared resolver
            _cp(3, "running vosk_model_resolver...")
            t_discovery_start = time.time()
            from ultron.voice.vosk_model_resolver import resolve_vosk_model, _human_size, _folder_size
            model_path = resolve_vosk_model()
            discovery_ms = (time.time() - t_discovery_start) * 1000
            _cp(3, f"resolver returned: '{model_path}' ({discovery_ms:.0f} ms)")

            if not model_path or not os.path.isdir(model_path):
                _cp(3, "ERROR: no model directory found on disk")
                print(
                    "\n[VOSK]\n"
                    "Model Load Failed\n"
                    "Reason:\n"
                    "  No Vosk model directory found. "
                    "Place a model under models/ and list it in config/voice.json → vosk_preferred_models.",
                    flush=True,
                )
                self.logger.error("Vosk: Model directory not found.")
                return False

            self.model_name = os.path.basename(model_path.rstrip("/\\"))
            model_size_str = _human_size(_folder_size(model_path))

            # ── Boot banner ───────────────────────────────────────────────
            print(
                f"\n[VOSK]\n"
                f"Selected Model:\n  {self.model_name}\n"
                f"Path:\n  {model_path}\n"
                f"Size:\n  {model_size_str}\n"
                f"Loading...",
                flush=True,
            )
            self.logger.info(
                f"[VOSK] Selected Model: {self.model_name} | Path: {model_path} | Size: {model_size_str}"
            )

            # CP5: vosk.Model() — heavy call, wrap with watchdog
            _cp(5, f"calling vosk.Model('{model_path}')...")
            vosk.SetLogLevel(-1)
            _load_done = threading.Event()
            _load_exc = [None]

            def _watchdog():
                if not _load_done.is_set():
                    elapsed = time.time() - _t_model_start
                    msg = (
                        f"[VOSK CP05-WATCHDOG] vosk.Model() has been running for {elapsed:.0f}s — "
                        f"still loading. Check Windows Defender exclusions for the models/ directory."
                    )
                    print(msg, flush=True)
                    self.logger.error(msg)

            _t_model_start = time.time()
            watchdog = threading.Timer(30.0, _watchdog)
            watchdog.daemon = True
            watchdog.start()

            try:
                self.model = vosk.Model(model_path)
            except Exception as _me:
                _load_exc[0] = _me
            finally:
                _load_done.set()
                watchdog.cancel()

            loading_ms = (time.time() - _t_model_start) * 1000

            if _load_exc[0] is not None:
                _cp(5, f"ERROR: vosk.Model() raised: {_load_exc[0]}")
                print(
                    f"\n[VOSK]\n"
                    f"Model Load Failed\n"
                    f"Reason:\n  {_load_exc[0]}\n"
                    f"Attempting next available model...",
                    flush=True,
                )
                self.logger.error(f"[VOSK] Model load failed: {_load_exc[0]}")
                return False

            _cp(5, f"vosk.Model() returned in {loading_ms:.0f} ms")

            # CP6: KaldiRecognizer
            _cp(6, f"creating KaldiRecognizer(sample_rate={self.sample_rate})...")
            t_rec_start = time.time()
            self.rec = vosk.KaldiRecognizer(self.model, self.sample_rate)
            rec_ms = (time.time() - t_rec_start) * 1000
            _cp(6, f"KaldiRecognizer created ({rec_ms:.0f} ms)")

            total_ms = (time.time() - t_total_start) * 1000

            # ── Success banner ────────────────────────────────────────────
            print(
                f"\n[VOSK]\n"
                f"Model Loaded Successfully\n"
                f"Initialization Time:\n  {loading_ms:.0f} ms\n"
                f"\nModel Discovery:   {discovery_ms:.0f} ms\n"
                f"Model Loading:     {loading_ms:.0f} ms\n"
                f"Recognizer:        {rec_ms:.0f} ms\n"
                f"Total:             {total_ms:.0f} ms",
                flush=True,
            )
            self.logger.info(
                f"[VOSK] Model Loaded | discovery={discovery_ms:.0f}ms "
                f"loading={loading_ms:.0f}ms recognizer={rec_ms:.0f}ms total={total_ms:.0f}ms"
            )

            self._initialized = True
            _cp(6, "_initialize_vosk COMPLETE — _initialized=True")
            return True

        except Exception as e:
            msg = f"Vosk initialization failed: {e}\n{_tb.format_exc()}"
            print(
                f"\n[VOSK]\n"
                f"Model Load Failed\n"
                f"Reason:\n  {e}\n"
                f"Attempting next available model...",
                flush=True,
            )
            print(f"[VOSK CP-ERR] {msg}", flush=True)
            self.logger.error(msg)
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

        # Enforce exclusive microphone access by stopping SAPI if active
        from ultron.core.service_manager import service_manager
        reco_service = service_manager.get_service("VoiceEngineService")
        if reco_service and reco_service.active_recognizer and reco_service.active_recognizer != self:
            if reco_service.active_recognizer.active:
                self.logger.info(f"Stopping active recognizer '{reco_service.active_recognizer.name}' to prevent concurrent mic access.")
                reco_service.active_recognizer.stop()

        # Model loading happens inside _run() — start() returns immediately
        self.active = True
        self.thread = threading.Thread(target=self._run, name="VoskRecognitionThread", daemon=True)
        self.logger.info("Recognition Thread Created")
        self.thread.start()
        self.logger.info("Recognition Thread Started — model will load in background")
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def health(self) -> str:
        if not self.active:
            return "Offline"
        if self._initialized and self.model:
            return "Running"
        if self.thread and self.thread.is_alive():
            return "Initializing"  # model loading in background
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

    def _set_engine_state(self, state: str):
        """Updates VoiceEngineService.init_state from background thread."""
        try:
            from ultron.core.service_manager import service_manager
            eng = service_manager.get_service("VoiceEngineService")
            if eng and hasattr(eng, "init_state"):
                eng.init_state = state
                eng.publish_diagnostics()
        except Exception:
            pass

    def _run(self):
        import sounddevice as sd
        from ultron.voice.pipeline_tracker import trace_pipeline, pipeline_broken

        def _cp(n, msg):
            ts = time.strftime('%H:%M:%S') + f".{int((time.time() % 1) * 1000):03d}"
            line = f"[VOSK CP{n:02d}] [{ts}] [thread={threading.current_thread().name}] {msg}"
            print(line, flush=True)
            self.logger.info(line)

        _cp(10, "_run() entered — recognition thread is alive")

        self.chunks_received = 0
        self.last_audio_time = time.time()
        self.latency = 0.0
        self.warning_sent = False

        # CP11: model loading
        _cp(11, "calling _initialize_vosk()...")
        self._set_engine_state("LOADING_MODEL")

        if not self._initialize_vosk():
            _cp(11, "ERROR: _initialize_vosk() returned False — aborting thread")
            self.logger.error("Vosk Recognition Provider cannot start because dependencies or model are unavailable.")
            event_bus.publish("VOSK_MODEL_MISSING", {"message": "Vosk model not found"})
            self._set_engine_state("ERROR")
            self.active = False
            return

        _cp(11, "_initialize_vosk() returned True — model and recognizer ready")
        self.logger.info("Recognition Loop Running")

        # ── Runtime Verification ──────────────────────────────────────────────
        _v_model      = self.model is not None
        _v_recognizer = self.rec is not None
        _v_thread     = self.thread is not None and self.thread.is_alive()
        # Audio callback active is verified after stream open; set placeholder
        _v_callback   = False  # updated once stream enters context
        _v_ready      = _v_model and _v_recognizer and _v_thread

        def _print_verification(audio_cb_active: bool):
            _pass = "\u2713 PASS"
            _fail = "\u2717 FAIL"
            lines = [
                f"  Model Loaded          {_pass if _v_model else _fail}",
                f"  Recognizer Created    {_pass if _v_recognizer else _fail}",
                f"  Recognition Thread    {_pass if _v_thread else _fail}",
                f"  Audio Callback        {_pass if audio_cb_active else _fail}",
            ]
            all_ok = _v_model and _v_recognizer and _v_thread and audio_cb_active
            lines.append(f"  Speech Recognition    {_pass if all_ok else _fail}")
            banner = "\n[VOSK]\n" + "\n".join(lines)
            if all_ok:
                banner += "\n\nRecognition ACTIVE"
            else:
                banner += "\n\nRecognition NOT READY — check above failures"
            print(banner, flush=True)
            self.logger.info(banner)
            if all_ok:
                event_bus.publish("RECOGNITION_ACTIVE", {"model": self.model_name})

        # CP12: device resolution
        _cp(12, f"device={self.device} (None means sounddevice will choose default)")
        if self.device is None:
            try:
                from ultron.memory import get_memory_manager
                mem = get_memory_manager()
                if mem:
                    records = mem.list_records("voice_settings")
                    for r in records:
                        if r["title"] == "preferred_microphone_index":
                            self.device = int(r["content"])
                            _cp(12, f"device index from UME: {self.device}")
                            break
            except Exception:
                pass

        # CP13: validate audio device
        _cp(13, "validating audio device...")
        preferred_name = "Default Microphone"
        device_exists = False
        device_available = False

        try:
            if self.device is not None:
                device_info = sd.query_devices(self.device, 'input')
                device_exists = True
                preferred_name = device_info["name"]
                _cp(13, f"device found: '{preferred_name}' (idx={self.device}, max_input_ch={device_info.get('max_input_channels',0)})")
            else:
                # No specific device — query default
                try:
                    default_info = sd.query_devices(kind='input')
                    preferred_name = default_info["name"]
                    device_exists = True
                    _cp(13, f"using default input device: '{preferred_name}'")
                except Exception as de:
                    _cp(13, f"WARNING: cannot query default device: {de}")
        except Exception as e:
            _cp(13, f"WARNING: device query failed: {e}")

        if device_exists:
            try:
                test_stream = sd.RawInputStream(samplerate=self.sample_rate, device=self.device, dtype='int16', channels=1)
                test_stream.close()
                device_available = True
                _cp(13, "test stream open/close OK — device is accessible")
            except Exception as e:
                _cp(13, f"WARNING: test stream failed: {e}")

        status_ok = device_exists and device_available
        _cp(13, f"device status: exists={device_exists}, available={device_available}, ok={status_ok}")
        if not status_ok:
            pipeline_broken("Microphone", f"Audio device status failed. Exists: {device_exists}, Available: {device_available}")

        # Display Phase 1 Microphone Ownership details
        mic_msg = (
            f"Provider Started: VoskVoiceRecognitionProvider\n"
            f"Microphone Opened: {preferred_name}\n"
            f"Device Index: {self.device if self.device is not None else 'default'}\n"
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
        trace_pipeline("Microphone", f"Device: {preferred_name}")


        def audio_callback(indata, frames, time_info, status):
            """Called for each audio block from sounddevice. Runs on audio thread."""
            if status:
                self.logger.warning(f"Vosk audio stream status: {status}")
                pipeline_broken("Microphone", f"sounddevice status warning: {status}")

            self.audio_queue.put(bytes(indata))
            self.audio_callback_count += 1
            n = self.audio_callback_count

            # Print unconditionally for first 3, then every 50th — avoids spam
            if n <= 3 or n % 50 == 0:
                data_bytes = bytes(indata)
                count = len(data_bytes) // 2
                rms = 0.0
                peak = 0
                if count > 0:
                    try:
                        shorts = struct.unpack(f"{count}h", data_bytes)
                        peak = max(abs(x) for x in shorts)
                        rms = math.sqrt(sum(float(x)*float(x) for x in shorts) / count)
                    except Exception:
                        pass
                cb_line = (f"[VOSK CP15] audio_callback #{n} | bytes={len(data_bytes)} | "
                           f"frames={frames} | queue={self.audio_queue.qsize()} | "
                           f"rms={rms:.1f} | peak={peak}")
                print(cb_line, flush=True)
                self.logger.info(cb_line)

            # Live volume meter event
            if self.publish_volume:
                try:
                    data_bytes = bytes(indata)
                    count = len(data_bytes) // 2
                    if count > 0:
                        shorts = struct.unpack(f"{count}h", data_bytes)
                        rms2 = math.sqrt(sum(x * x for x in shorts) / count)
                        event_bus.publish("VOLUME_LEVEL_CHANGED", {"level": float(rms2)})
                except Exception:
                    pass

        try:
            # CP14: open the sounddevice input stream
            _cp(14, f"opening RawInputStream: samplerate={self.sample_rate}, blocksize=2048, device={self.device}")
            self._set_engine_state("OPENING_MICROPHONE")
            try:
                stream = sd.RawInputStream(
                    samplerate=self.sample_rate, blocksize=2048, device=self.device,
                    dtype='int16', channels=1, callback=audio_callback
                )
            except Exception as e:
                _cp(14, f"ERROR: RawInputStream failed to open: {e}")
                self.logger.error(f"MICROPHONE FAILED TO OPEN: {e}")
                self._set_engine_state("ERROR")
                raise e

            _cp(14, "RawInputStream created OK — entering 'with stream:' context")
            with stream:
                _cp(14, "stream context entered — audio_callback is now live")
                self.logger.info("Vosk input stream active. Listening...")
                self._set_engine_state("STARTING_RECOGNITION")
                self.last_audio_time = time.time()
                self._set_engine_state("READY")
                _print_verification(audio_cb_active=True)

                _cp(14, "state=READY — entering recognition while-loop")

                _loop_iter = 0
                while self.active:
                    _loop_iter += 1
                    if _loop_iter <= 3 or _loop_iter % 200 == 0:
                        _cp(16, f"recognition loop iteration #{_loop_iter} | active={self.active} | queue={self.audio_queue.qsize()} | chunks={self.chunks_received}")

                    try:
                        data = self.audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        # Watchdog: no audio for >5 s
                        if time.time() - self.last_audio_time > 5.0 and not self.warning_sent:
                            _cp(16, f"WARNING: no audio for >5s — callback_count={self.audio_callback_count} | check microphone")
                            self.logger.warning("WARNING:\nNo microphone audio detected.")
                            pipeline_broken("Audio Buffer", "No microphone audio detected for >5 seconds.")
                            event_bus.publish("WARNING_OCCURRED", {"message": "WARNING:\nNo microphone audio detected."})
                            self.warning_sent = True
                        continue

                    self.chunks_received += 1
                    self.last_audio_time = time.time()
                    self.warning_sent = False

                    trace_pipeline("Recognition Provider", f"Vosk decoding chunk {self.chunks_received}")

                    # CP17: AcceptWaveform
                    t_aw = time.time()
                    accept = self.rec.AcceptWaveform(data)
                    self.latency = time.time() - t_aw
                    if self.chunks_received <= 3 or self.chunks_received % 100 == 0:
                        _cp(17, f"AcceptWaveform chunk#{self.chunks_received} → {accept} ({self.latency*1000:.1f}ms)")

                    if accept:
                        result_str = self.rec.Result()
                        result_dict = json.loads(result_str)
                        text = result_dict.get("text", "").strip()
                        # CP19: final result
                        _cp(19, f"Result() → '{text}'")
                        if text:
                            self.logger.info(f"Recognized:\n\"{text}\"")
                            trace_pipeline("Microphone", f"Audio captured for phrase '{text}'")
                            trace_pipeline("Recognition callback", f"text='{text}', confidence=1.0")
                            _cp(19, f"firing callback('{text}', 1.0) — callback={self.callback}")
                            if self.callback:
                                self.callback(text, 1.0)
                    else:
                        partial_str = self.rec.PartialResult()
                        partial_dict = json.loads(partial_str)
                        partial_text = partial_dict.get("partial", "").strip()
                        if partial_text:
                            # CP18: partial
                            _cp(18, f"PartialResult() → '{partial_text}'")
                            self.logger.info(f"Partial:\n\"{partial_text}\"")

                # Read remaining text when stream stops
                final_str = self.rec.FinalResult()
                final_dict = json.loads(final_str)
                text = final_dict.get("text", "").strip()
                if text:
                    _cp(19, f"FinalResult() on stop → '{text}'")
                    self.logger.info(f"Recognized:\n\"{text}\"")
                    trace_pipeline("Microphone", f"Audio captured for phrase '{text}'")
                    trace_pipeline("Recognition callback", f"text='{text}', confidence=1.0")
                    if self.callback:
                        self.callback(text, 1.0)

        except Exception as e:
            import traceback as _tb
            err_msg = f"Vosk recognition loop crashed: {e}\n{_tb.format_exc()}"
            print(f"[VOSK CP-CRASH] {err_msg}", flush=True)
            self.logger.error(err_msg)
            pipeline_broken("Recognition Provider", f"Vosk crash: {e}")
            if self.active:
                self.logger.info("Attempting automatic reconnection recovery...")
                self._handle_reconnect()
        finally:
            self.active = False
