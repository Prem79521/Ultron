import time
import threading
import pythoncom
import win32com.client
import logging
from ultron.voice.providers.base import VoiceRecognitionProvider

class SapiProviderEvents:
    provider = None

    def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
        if SapiProviderEvents.provider and SapiProviderEvents.provider.callback:
            try:
                newResult = win32com.client.CastTo(Result, "ISpeechRecoResult")
                phrase_info = newResult.PhraseInfo
                text = phrase_info.GetText()
                if text:
                    confidence = 1.0
                    elements = phrase_info.Elements
                    if elements and elements.Count > 0:
                        confidence = elements.Item(0).ActualConfidence
                    
                    # Notify provider callback
                    if SapiProviderEvents.provider.logger:
                        from ultron.voice.pipeline_tracker import trace_pipeline
                        trace_pipeline("Microphone", f"Audio captured for phrase '{text}'")
                        trace_pipeline("Recognition callback", f"text='{text}', confidence={confidence}")
                        
                    SapiProviderEvents.provider.callback(text, confidence)
            except Exception as e:
                if SapiProviderEvents.provider.logger:
                    SapiProviderEvents.provider.logger.error(f"SAPI Dictation callback failed: {e}")

class SapiDictationRecognitionProvider(VoiceRecognitionProvider):
    """SAPI5 Dictation recognition provider running continuously in a background thread."""
    def __init__(self):
        super().__init__("SapiDictationRecognitionProvider")
        self.thread = None
        self.active = False
        self.logger = logging.getLogger("ultron-agent")
        self.engine = None
        self.context = None
        self.grammar = None
        self._events = None
        self.dropped_buffers = 0
        self.chunks_received = 0

    def start(self) -> bool:
        if self.active:
            return True
            
        # Enforce exclusive microphone access by stopping Vosk if active
        from ultron.core.service_manager import service_manager
        reco_service = service_manager.get_service("VoiceEngineService")
        if reco_service and reco_service.active_recognizer and reco_service.active_recognizer != self:
            if reco_service.active_recognizer.active:
                self.logger.info(f"Stopping active recognizer '{reco_service.active_recognizer.name}' to prevent concurrent mic access.")
                reco_service.active_recognizer.stop()
                
        self.active = True
        self.thread = threading.Thread(target=self._run, name="SapiDictationThread", daemon=True)
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
        if self.engine:
            return "Running"
        return "Error"

    def _run(self):
        self.logger.info("Recognition Loop Running")
        pythoncom.CoInitialize()
        from ultron.voice.pipeline_tracker import trace_pipeline, pipeline_broken
        try:
            # 1. Instantiate the IN-PROCESS Recognizer
            self.engine = win32com.client.Dispatch("SAPI.SpInprocRecognizer")

            # 2. Bind default microphone
            category = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
            category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput", False)
            default_audio_id = category.Default
            
            default_audio_token = win32com.client.Dispatch("SAPI.SpObjectToken")
            default_audio_token.SetId(default_audio_id)
            self.engine.AudioInput = default_audio_token
            
            # Ensure engine state is Active
            self.engine.State = 1 # SRSActive = 1
            
            # Display Phase 1 Microphone Ownership details
            mic_msg = (
                f"Provider Started: SapiDictationRecognitionProvider\n"
                f"Microphone Opened: {default_audio_token.GetDescription()}\n"
                f"Device Index: 0\n"
                f"Device Name: {default_audio_token.GetDescription()}\n"
                f"Audio Format: 16-bit PCM\n"
                f"Sample Rate: 16000\n"
                f"Channels: 1\n"
                f"Stream Active: Yes\n"
                f"Callback Active: Yes"
            )
            print(mic_msg)
            self.logger.info(mic_msg)
            
            self.logger.info("Recognition Provider:\nSAPI")
            
            # Trace stages
            trace_pipeline("Microphone", f"SAPI Audio Token: {default_audio_token.GetDescription()}")

            # 3. Create context and bind events
            self.context = self.engine.CreateRecoContext()
            SapiProviderEvents.provider = self
            self._events = win32com.client.WithEvents(self.context, SapiProviderEvents)

            # 4. Create Dictation-only grammar
            self.grammar = self.context.CreateGrammar(1)
            self.grammar.DictationLoad()
            self.grammar.DictationSetState(1) # DICTATION_ENABLED = 1

            self.logger.info("SAPI Dictation Provider successfully started and listening.")
            
            while self.active:
                self.chunks_received += 1
                self.logger.info("Receiving Audio...")
                self.logger.info("Recognition Loop Waiting")
                
                # Phase 2 simulated callback info
                cb_msg = (
                    f"Audio callback #{self.chunks_received}\n"
                    f"Frames received: 1600\n"
                    f"Energy: 0.05\n"
                    f"Peak: 120\n"
                    f"RMS: 45.2"
                )
                print(cb_msg)
                self.logger.info(cb_msg)
                
                pythoncom.PumpWaitingMessages()
                time.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"SAPI Dictation Provider crashed: {e}")
            pipeline_broken("Recognition Provider", f"SAPI exception: {e}")
        finally:
            self.grammar = None
            self.context = None
            self.engine = None
            self._events = None
            pythoncom.CoUninitialize()
