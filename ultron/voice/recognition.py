"""
ULTRON Speech Recognition Module — Offline SAPI5 voice listener running in a background thread.
"""

import threading
import time
import pythoncom
import win32com.client
import logging
import string
from ultron.core.event_bus import event_bus
from ultron.core.service_manager import UltronService

# ===================================================================
# SAPI5 Grammar and Rule Constants (Scenario 1)
# ===================================================================
GRAMMAR_ID_WAKE = 1
RULE_ACTIVE = 1
RULE_INACTIVE = 0
DICTATION_ENABLED = 1
DICTATION_DISABLED = 0
SAPI_DYNAMIC_GRAMMAR = 0
SAPI_RULE_ACTIVE = 1

def normalize_phrase(text: str) -> str:
    """Trims, lowers, and strips punctuation and extra whitespaces from phrases (Scenario 3)."""
    if not text:
        return ""
    text = text.lower().strip()
    # Remove punctuation
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())

class SapiEvents:
    callback_ref = None
    logger = None

    def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
        if SapiEvents.callback_ref:
            try:
                newResult = win32com.client.CastTo(Result, "ISpeechRecoResult")
                phrase_info = newResult.PhraseInfo
                text = phrase_info.GetText()
                if text:
                    # Capture actual confidence score (Scenario 4)
                    confidence = 1.0
                    elements = phrase_info.Elements
                    if elements and elements.Count > 0:
                        confidence = elements.Item(0).ActualConfidence
                        
                    # Log confidence scores to developer console
                    if SapiEvents.logger:
                        SapiEvents.logger.info(
                            f"RECOGNIZED: '{text}' | CONFIDENCE: {confidence:.2f} | "
                            f"TYPE: {RecognitionType} | TIMESTAMP: {time.time():.2f}"
                        )
                        
                    # Publish telemetry telemetry events
                    event_bus.publish("RECOGNITION_TELEMETRY", {
                        "phrase": text,
                        "confidence": confidence,
                        "type": RecognitionType,
                        "timestamp": time.time()
                    })
                    
                    SapiEvents.callback_ref(text, confidence)
            except Exception as e:
                if SapiEvents.logger:
                    SapiEvents.logger.error(f"SAPI5 recognition callback processing failed: {e}")

class SapiSpeechListener(UltronService):
    """Offline SAPI5 listener managed as an OS service using In-Process Recognizer."""
    def __init__(self, callback_func, wake_word: str = "arise"):
        super().__init__("VoiceRecognitionService")
        self.callback = callback_func
        self.wake_word = normalize_phrase(wake_word)
        self.thread = None
        self.logger = logging.getLogger("ultron-agent")
        self.retries = 0
        self.pending_state_change = None
        self.engine = None
        self.reco_context = None
        self.grammar = None
        self._reco_events = None
        
        # Dedicated telemetry diagnostics panel dataset (Scenario 5)
        self.diagnostics = {
            "current_microphone": "Microphone (GENERAL WEBCAM)",
            "recognition_engine": "SAPI.SpInprocRecognizer",
            "recognition_thread": "VoiceRecognitionServiceThread",
            "grammar_loaded": "WakeGrammar, DictationGrammar",
            "wake_grammar_active": True,
            "dictation_active": False,
            "last_recognized_phrase": "None",
            "last_confidence_score": 0.0,
            "callback_count": 0,
            "com_status": "Uninitialized",
            "wake_matches": 0,
            "last_recognition_timestamp": 0.0
        }
        
        # Monitor OS state transitions to synchronize SAPI5 grammar rules (Bug 16 / Scenario 6)
        event_bus.subscribe("STATE_CHANGED", self.on_state_changed)

    def on_state_changed(self, event):
        """Thread-safe state notifier backing up values to be processed on COM worker thread."""
        self.pending_state_change = event.payload.get("state")

    def get_diagnostics(self) -> dict:
        """Returns active telemetry diagnostics dictionary."""
        self.diagnostics["com_status"] = "Healthy" if self.engine else "Uninitialized"
        return self.diagnostics

    def update_diagnostics_on_phrase(self, text: str, confidence: float):
        """Internal updater updating metrics upon recognition."""
        self.diagnostics["last_recognized_phrase"] = text
        self.diagnostics["last_confidence_score"] = confidence
        self.diagnostics["callback_count"] += 1
        self.diagnostics["last_recognition_timestamp"] = time.time()
        
        if normalize_phrase(text) == self.wake_word:
            self.diagnostics["wake_matches"] += 1

    def start(self) -> bool:
        from ultron.hal.hal_manager import get_hal_manager
        hal = get_hal_manager()
        if hal and not hal.is_allowed("microphone"):
            self.logger.warning("Voice Recognition: Service start aborted due to missing microphone permission.")
            self.active = False
            return False
            
        self.active = True
        self.thread = threading.Thread(target=self._run, name=self.diagnostics["recognition_thread"], daemon=True)
        self.thread.start()
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def health(self) -> str:
        if not self.active:
            return "Offline"
        if self.retries >= 3:
            return "Error"
        return "Running"

    def _run(self):
        while self.active:
            pythoncom.CoInitialize()
            try:
                # 1. Instantiate the IN-PROCESS Recognizer (bypasses Windows desktop Speech UI)
                self.engine = win32com.client.Dispatch("SAPI.SpInprocRecognizer")

                # 2. Bind the default microphone directly to the InProc engine
                from ultron.hal.hal_manager import get_hal_manager
                hal = get_hal_manager()
                
                # Fetch default audio token dynamically
                category = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
                category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput", False)
                default_audio_id = category.Default
                
                default_audio_token = win32com.client.Dispatch("SAPI.SpObjectToken")
                default_audio_token.SetId(default_audio_id)
                self.engine.AudioInput = default_audio_token
                
                self.diagnostics["current_microphone"] = default_audio_token.GetDescription()

                # 3. Create Context and bind Events
                self.reco_context = self.engine.CreateRecoContext()
                
                # Setup internal proxy callback to capture diagnostics
                def proxy_callback(text, confidence):
                    self.update_diagnostics_on_phrase(text, confidence)
                    self.callback(text, confidence)
                    
                SapiEvents.callback_ref = proxy_callback
                SapiEvents.logger = self.logger
                
                self._reco_events = win32com.client.WithEvents(self.reco_context, SapiEvents)

                # 4. Build and Activate the Grammar Rule
                self.grammar = self.reco_context.CreateGrammar(GRAMMAR_ID_WAKE)
                
                # Pre-load free dictation template
                try:
                    self.grammar.DictationLoad()
                except Exception:
                    pass

                # Build dynamic grammar rules for custom wake word detections (Scenario 2)
                rule = self.grammar.Rules.Add("WakeRule", SAPI_RULE_ACTIVE, SAPI_DYNAMIC_GRAMMAR)
                rule.InitialState.AddWordTransition(None, self.wake_word)
                # Capitalized fallback
                cap_wake = self.wake_word.capitalize()
                if cap_wake != self.wake_word:
                    rule.InitialState.AddWordTransition(None, cap_wake)
                    
                self.grammar.Rules.Commit()

                # Sync initial state rule
                from ultron.core.state_manager import state_manager
                curr_state = state_manager.state
                if curr_state == "Listening":
                    self.grammar.DictationSetState(DICTATION_ENABLED)
                    self.grammar.CmdSetRuleState("WakeRule", RULE_INACTIVE)
                    self.diagnostics["wake_grammar_active"] = False
                    self.diagnostics["dictation_active"] = True
                else:
                    self.grammar.DictationSetState(DICTATION_DISABLED)
                    self.grammar.CmdSetRuleState("WakeRule", RULE_ACTIVE)
                    self.diagnostics["wake_grammar_active"] = True
                    self.diagnostics["dictation_active"] = False

                self.retries = 0  # reset retries on success
                self.logger.info(
                    f"Voice Recognition: In-Process SAPI5 recognizer context created. "
                    f"Target wake word: '{self.wake_word}'"
                )
                
                # Loop and pump messages to receive COM event callbacks
                while self.active:
                    # Sync state changes thread-safely inside the COM apartment loop (Scenario 6)
                    if self.pending_state_change:
                        state = self.pending_state_change
                        self.pending_state_change = None
                        try:
                            if state == "Listening":
                                self.grammar.DictationSetState(DICTATION_ENABLED)
                                self.grammar.CmdSetRuleState("WakeRule", RULE_INACTIVE)
                                self.diagnostics["wake_grammar_active"] = False
                                self.diagnostics["dictation_active"] = True
                            elif state == "Sleeping":
                                self.grammar.DictationSetState(DICTATION_DISABLED)
                                self.grammar.CmdSetRuleState("WakeRule", RULE_ACTIVE)
                                self.diagnostics["wake_grammar_active"] = True
                                self.diagnostics["dictation_active"] = False
                        except Exception as e:
                            self.logger.warning(f"Voice Recognition: Thread-safe grammar toggle error on {state}: {e}")

                    pythoncom.PumpWaitingMessages()
                    time.sleep(0.1)
                    
            except Exception as e:
                pythoncom.CoUninitialize()
                self.retries += 1
                
                # Multi-line diagnostic logging (Scenario 7)
                self.logger.error(
                    f"Voice Recognition: COM thread exception encountered.\n"
                    f"Component: VoiceRecognitionService\n"
                    f"Thread: {threading.current_thread().name}\n"
                    f"Exception Type: {type(e).__name__}\n"
                    f"Error Message: {e}\n"
                    f"Retry Attempt: {self.retries}/3\n"
                    f"Action: Attempting automatic context restart."
                )
                
                if self.retries >= 3:
                    self.logger.error("Voice Recognition: Maximum SAPI5 recovery retries reached. Falling back to text-only mode.")
                    event_bus.publish("DEVICE_DISCONNECTED", {"device": "Microphone"})
                    event_bus.publish("ERROR_OCCURRED", {
                        "message": "SAPI5 microphone interface unavailable. Voice commands disabled.",
                        "service": self.name
                    })
                    self.active = False
                    break
                else:
                    time.sleep(2.0)  # wait before retry
            finally:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
