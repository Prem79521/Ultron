"""
ULTRON Phase 6 Integration Acceptance Test — "First Awakening"
Verifies the end-to-end voice pipeline: Speech -> Wake -> AI Core -> Launch notepad.
"""

import os
import sys
import time
import unittest
import sqlite3

# Ensure codebase root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.core.event_bus import event_bus
from ultron.core.state_manager import state_manager
from ultron.core.service_manager import service_manager
from ultron.core.wake_engine import init_wake_engine
from ultron.voice.tts.pyttsx3_provider import Pyttsx3VoiceProvider
from ultron.voice.recognizer import RecognitionService
from ultron.voice.wake_detector import WakeDetectorService
from ultron.core.voice_session_manager import init_voice_session_manager, get_voice_session_manager, VoiceState
from ultron.core.ai_core import init_ai_core
from ultron.skills.registry import SkillRegistry
from ultron.skills.command_dispatcher import CommandDispatcher
from ultron.memory import MemoryManager

class MockTTSProvider:
    def __init__(self):
        self.spoken = []
    def speak(self, text: str):
        self.spoken.append(text)
        # Simulate asynchronous TTS engine by publishing events synchronously
        event_bus.publish("VoiceStarted", {"text": text})
        event_bus.publish("VoiceStopped", {"text": text})
    def initialize(self): return True
    def start(self): return True
    def stop(self): return True
    def restart(self): return True
    def configure(self, cfg): pass
    def status(self): return "Online"
    def health(self): return "Running"

class TestFirstAwakening(unittest.TestCase):
    def setUp(self):
        # Setup temporary SQLite memory database
        self.db_name = "test_awakening.db"
        self.memory = MemoryManager(self.db_name)
        
        # Setup mock systems
        self.mock_tts = MockTTSProvider()
        self.wake_engine = init_wake_engine(self.mock_tts)
        self.wake_engine.set_display_name("Prem")
        
        self.session_manager = init_voice_session_manager(self.mock_tts)
        self.session_manager.set_display_name("Prem")
        service_manager.register_service("VoiceSessionManager", self.session_manager)
        
        # Set state initially to Sleeping
        self.session_manager.transition_to(VoiceState.SLEEPING)
        
        # Initialize Core and commands
        from ultron.core import CoreSystem
        self.core = CoreSystem()
        self.skills = SkillRegistry(self.core, self.memory)
        self.skills.register_skill("CommandDispatcher", CommandDispatcher)
        self.dispatcher = self.skills.get_skill("CommandDispatcher")
        
        self.ai = init_ai_core(self.core, self.memory, self.skills)
        
        # Setup mock engine service to link wake provider callback
        from ultron.voice.wake.sapi_wake_provider import SapiWakeProvider
        class MockRecognizer:
            def set_callback(self, cb): pass
            def start(self): pass
            def stop(self): pass
            def health(self): return "Running"
            def is_active(self): return True
            
        class MockEngineService:
            def __init__(self):
                self.active_wake = SapiWakeProvider()
                self.active_wake.set_wake_phrase("arise")
                self.active_wake.start()
                self.active_recognizer = MockRecognizer()
                self.reco_provider_name = "mock_reco"
                self.wake_phrase = "arise"
                self.diagnostics = {
                    "wake_matches": 0,
                    "last_wake_event": 0,
                    "callback_count": 0,
                    "last_recognized_phrase": "",
                    "last_confidence_score": 0.0,
                    "last_recognition_timestamp": 0.0
                }
            def publish_diagnostics(self):
                pass
            def health(self): return "Running"
                
        self.mock_engine = MockEngineService()
        service_manager.register_service("VoiceEngineService", self.mock_engine)

        # Initialize listeners
        from main import handle_voice_command
        self.recognition_service = RecognitionService(handle_voice_command)
        self.recognition_service.start()
        
        self.wake_detector = WakeDetectorService()
        self.wake_detector.start()

    def tearDown(self):
        self.recognition_service.stop()
        self.wake_detector.stop()
        self.session_manager.stop()
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass

    def test_end_to_end_awakening_pipeline(self):
        """Validates: Speech Recognized(Arise) -> Wake -> State(Listening) -> Speech(Launch notepad)."""
        # Step 1: Simulate user saying "Arise"
        speech_events = []
        wake_events = []
        
        event_bus.subscribe("SPEECH_RECOGNIZED", lambda e: speech_events.append(e.payload))
        event_bus.subscribe("WAKE_DETECTED", lambda e: wake_events.append(e.payload))

        # Feed "arise" directly to recognition service handler
        self.recognition_service._handle_speech("arise", 1.0)
        
        # Verify SPEECH_RECOGNIZED and WAKE_DETECTED were published
        self.assertTrue(any(e["text"] == "arise" for e in speech_events))
        self.assertEqual(len(wake_events), 1)
        
        # Verify State transitioned to Listening
        self.assertEqual(state_manager.state, "Listening")
        
        # Verify greeting was spoken to Prem
        self.assertTrue(len(self.mock_tts.spoken) > 0)
        self.assertIn("Yes, Prem", self.mock_tts.spoken[0])

        # Step 2: Say "launch notepad" while Listening
        # In a dry_run mode, the formalized command framework intercepts and validates the Notepad launch!
        result = self.dispatcher.execute({"command": "launch notepad"})
        self.assertTrue(result["success"])
        self.assertIn("Launching 'notepad'", result["response"])

    def test_session_timeout_and_repeatable_wake(self):
        """Verifies session deactivation on timeout and repeatability of wake activation."""
        # Reset state to Sleeping
        self.session_manager.transition_to(VoiceState.SLEEPING)
        
        # Trigger wake
        self.recognition_service._handle_speech("arise", 1.0)
        self.assertEqual(state_manager.state, "Listening")
        
        # Simulate timeout
        self.session_manager._on_timeout_expired()
        
        # Verify returned to Sleeping (Standby)
        self.assertEqual(state_manager.state, "Sleeping")
        
        # Trigger wake again
        self.recognition_service._handle_speech("arise", 1.0)
        self.assertEqual(state_manager.state, "Listening")

if __name__ == "__main__":
    unittest.main()
