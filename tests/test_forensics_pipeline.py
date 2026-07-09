import unittest
import string
from ultron.voice.pipeline_tracker import trace_pipeline, pipeline_broken
from ultron.voice.wake.sapi_wake_provider import SapiWakeProvider

class TestForensicsPipeline(unittest.TestCase):
    def test_pipeline_tracker_runs_without_error(self):
        # Verify that tracing stages does not raise errors
        trace_pipeline("Microphone", "Test Device")
        trace_pipeline("Audio Buffer", "1024 bytes")
        trace_pipeline("Recognition Provider", "Test Vosk")
        trace_pipeline("Recognized Text", "arise")
        trace_pipeline("Wake Detector", "Checking")
        trace_pipeline("Wake Match", "Matched")
        trace_pipeline("VoiceSessionManager", "Transitioning")
        trace_pipeline("AI Queue", "Queued")
        trace_pipeline("Execution", "Ran notepad")
        
        # Verify that logging breaks does not raise errors
        pipeline_broken("Microphone", "Microphone disconnected")

    def test_sapi_wake_provider_cleaning(self):
        # Verify normalization cleans text as specified
        provider = SapiWakeProvider()
        provider.set_wake_phrase("arise")
        
        # Mock callback
        matched = False
        def callback():
            nonlocal matched
            matched = True
        provider.set_callback(callback)
        
        provider.start()
        
        # Test case: different cases, punctuation, and extra whitespace
        provider.process_speech("  ,  Arise!  ", 1.0)
        self.assertTrue(matched)

if __name__ == "__main__":
    unittest.main()
