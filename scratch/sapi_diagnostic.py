"""
ULTRON Voice Recognition SAPI5 Pipeline Diagnostic Mode
Verifies all 10 stages of the speech recognition pipeline.
"""

import sys
import os
import time
import pythoncom
import win32com.client

class DiagnosticSapiEvents:
    heard_anything = False
    test_mode = False

    def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
        DiagnosticSapiEvents.heard_anything = True
        try:
            # Replicate production CastTo behavior exactly
            newResult = win32com.client.CastTo(Result, "ISpeechRecoResult")
            phrase_info = newResult.PhraseInfo
            text = phrase_info.GetText()
            if text:
                if DiagnosticSapiEvents.test_mode:
                    print(f"Recognized:\n{text}")
                else:
                    print(f"\n[EVENT] OnRecognition() called! Heard: '{text}'")
        except Exception as e:
            print(f"Error in OnRecognition event processing: {e}")

def run_diagnostic(test_mode: bool = False):
    print("==================================================")
    if test_mode:
        print("RUNNING TEMPORARY TEST MODE (DICTATION ONLY)")
        print("• Dictation grammar only.")
        print("• No Wake Engine.")
        print("• No Event Bus.")
        print("• No AI Core.")
    else:
        print("RUNNING SAPI5 PIPELINE ACCEPTANCE DIAGNOSTIC")
    print("==================================================")

    # CHECKPOINT 1: COM initialized
    try:
        pythoncom.CoInitialize()
        print("CHECKPOINT 1\nCOM initialized.")
    except Exception as e:
        print(f"CHECKPOINT 1 FAILED: COM initialization error: {e}")
        return False

    # CHECKPOINT 2: Recognizer object created
    try:
        engine = win32com.client.Dispatch("SAPI.SpInprocRecognizer")
        print("\nCHECKPOINT 2\nRecognizer object created.")
    except Exception as e:
        print(f"CHECKPOINT 2 FAILED: Failed to create SAPI.SpInprocRecognizer: {e}")
        pythoncom.CoUninitialize()
        return False

    # CHECKPOINT 3: Audio device bound successfully. Print audio device description.
    try:
        category = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
        category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput", False)
        default_audio_id = category.Default
        
        default_audio_token = win32com.client.Dispatch("SAPI.SpObjectToken")
        default_audio_token.SetId(default_audio_id)
        engine.AudioInput = default_audio_token
        
        device_description = default_audio_token.GetDescription()
        print(f"\nCHECKPOINT 3\nAudio device bound successfully.")
        print(f"Audio device description: {device_description}")
    except Exception as e:
        print(f"CHECKPOINT 3 FAILED: Failed to bind default audio device: {e}")
        pythoncom.CoUninitialize()
        return False

    # CHECKPOINT 4: Recognition context created
    try:
        reco_context = engine.CreateRecoContext()
        print("\nCHECKPOINT 4\nRecognition context created.")
    except Exception as e:
        print(f"CHECKPOINT 4 FAILED: Failed to create recognition context: {e}")
        pythoncom.CoUninitialize()
        return False

    # CHECKPOINT 5: Grammar created
    try:
        # Replicate production grammar ID
        GRAMMAR_ID_WAKE = 1
        grammar = reco_context.CreateGrammar(GRAMMAR_ID_WAKE)
        print("\nCHECKPOINT 5\nGrammar created.")
    except Exception as e:
        print(f"CHECKPOINT 5 FAILED: Failed to create grammar: {e}")
        pythoncom.CoUninitialize()
        return False

    # CHECKPOINT 6: Grammar committed
    try:
        if test_mode:
            # Temporary test mode: Dictation grammar only
            grammar.DictationLoad()
            grammar.DictationSetState(1) # DICTATION_ENABLED = 1
            print("\nCHECKPOINT 6\nGrammar committed (Dictation load).")
        else:
            # Production wake rule mode
            try:
                grammar.DictationLoad()
            except Exception:
                pass
            
            SAPI_RULE_ACTIVE = 1
            SAPI_DYNAMIC_GRAMMAR = 0
            wake_word = "arise"
            
            rule = grammar.Rules.Add("WakeRule", SAPI_RULE_ACTIVE, SAPI_DYNAMIC_GRAMMAR)
            rule.InitialState.AddWordTransition(None, wake_word)
            rule.InitialState.AddWordTransition(None, wake_word.capitalize())
            
            grammar.Rules.Commit()
            print("\nCHECKPOINT 6\nGrammar committed.")
    except Exception as e:
        print(f"CHECKPOINT 6 FAILED: Failed to commit/load grammar: {e}")
        pythoncom.CoUninitialize()
        return False

    # CHECKPOINT 7: Wake rule activated
    try:
        if test_mode:
            # No Wake Rule in dictation test mode
            print("\nCHECKPOINT 7\nWake rule activated (Skipped: test mode active).")
        else:
            # Deactivate dictation and activate wake rule as done in production Sleeping state
            grammar.DictationSetState(0) # DICTATION_DISABLED = 0
            grammar.CmdSetRuleState("WakeRule", 1) # RULE_ACTIVE = 1
            print("\nCHECKPOINT 7\nWake rule activated.")
    except Exception as e:
        print(f"CHECKPOINT 7 FAILED: Failed to activate wake rule: {e}")
        pythoncom.CoUninitialize()
        return False

    # CHECKPOINT 8: Event sink attached
    try:
        DiagnosticSapiEvents.heard_anything = False
        DiagnosticSapiEvents.test_mode = test_mode
        # Attach event listener
        reco_events = win32com.client.WithEvents(reco_context, DiagnosticSapiEvents)
        print("\nCHECKPOINT 8\nEvent sink attached.")
    except Exception as e:
        print(f"CHECKPOINT 8 FAILED: Failed to attach event sink: {e}")
        pythoncom.CoUninitialize()
        return False

    # CHECKPOINT 9: COM message loop started
    print("\nCHECKPOINT 9\nCOM message loop started.")
    if test_mode:
        print(">>> Speak standard phrases (e.g. 'Hello') now.")
    else:
        print(">>> Speak the wake word ('Arise') now.")
    print("Listening for 15 seconds... (Press Ctrl+C to exit loop early)")

    start_time = time.time()
    try:
        while time.time() - start_time < 15:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nLoop aborted by user.")

    # CHECKPOINT 10: VERIFY whether OnRecognition() is EVER called
    print("\nCHECKPOINT 10\nVERIFY whether OnRecognition() is EVER called.")
    if DiagnosticSapiEvents.heard_anything:
        print("SUCCESS: OnRecognition() was called.")
    else:
        print("NO SAPI RECOGNITION EVENTS RECEIVED.")

    pythoncom.CoUninitialize()
    print("\nCOM uninitialized.")
    return True

if __name__ == "__main__":
    test_arg = "--test-mode" in sys.argv or "-t" in sys.argv
    run_diagnostic(test_mode=test_arg)
