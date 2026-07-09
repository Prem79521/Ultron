"""
ULTRON SAPI5 Root Cause Investigation: Pure MSDN Implementation (Interactive)
Minimal command grammar built strictly from Microsoft specifications.
Requires pressing Enter before each test to allow the user to speak.
"""

import sys
import os
import time
import pythoncom
import win32com.client

# SAPI 5.4 Constants
SRATopLevel = 1        # Rule can be active for recognition
SRADynamic = 32        # Rule can be modified programmatically at runtime
SRSActive = 1          # Recognizer is active and processing audio

class MsdnSapiEvents:
    heard = False
    def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
        MsdnSapiEvents.heard = True
        try:
            newResult = win32com.client.CastTo(Result, "ISpeechRecoResult")
            text = newResult.PhraseInfo.GetText()
            print(f"\n>>> [SUCCESS] SAPI Heard: '{text}'!")
        except Exception as e:
            print(f"Error in callback: {e}")

def test_msdn_grammar(use_dynamic_flag=True, set_engine_state=True):
    print(f"\n--- Testing configuration: use_dynamic_flag={use_dynamic_flag}, set_engine_state={set_engine_state} ---")
    input("Press Enter when you are ready to speak, then say 'Arise'...")
    
    pythoncom.CoInitialize()
    
    try:
        # 1. Create In-Process Recognizer
        engine = win32com.client.Dispatch("SAPI.SpInprocRecognizer")
        
        # 2. Bind default audio input
        category = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
        category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput", False)
        default_audio_token = win32com.client.Dispatch("SAPI.SpObjectToken")
        default_audio_token.SetId(category.Default)
        engine.AudioInput = default_audio_token
        print(f"Audio device: {engine.AudioInput.GetDescription()}")

        # 3. Set Engine State if requested
        if set_engine_state:
            engine.State = SRSActive
            print("Recognizer state set to SRSActive (1).")
        else:
            print("Recognizer state left as default.")

        # 4. Create Context
        context = engine.CreateRecoContext()
        events = win32com.client.WithEvents(context, MsdnSapiEvents)

        # 5. Create Grammar
        grammar = context.CreateGrammar(1)

        # 6. Add Rule
        attributes = (SRATopLevel | SRADynamic) if use_dynamic_flag else SRATopLevel
        rule_id = 1
        
        print(f"Adding rule 'WakeRule' with Attributes={attributes} and RuleId={rule_id}...")
        rule = grammar.Rules.Add("WakeRule", attributes, rule_id)

        # 7. Add Word Transition
        rule.InitialState.AddWordTransition(None, "Arise")
        
        # 8. Commit
        grammar.Rules.Commit()
        print("Grammar changes committed.")

        # 9. Set Rule State to Active
        grammar.CmdSetRuleState("WakeRule", 1) # SGDSActive = 1
        print("Rule state set to SGDSActive (1).")

        # 10. Pump Messages
        print("Listening for 'Arise'... (15 seconds countdown. Please speak now!)")
        MsdnSapiEvents.heard = False
        start_time = time.time()
        while time.time() - start_time < 15:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)
            if MsdnSapiEvents.heard:
                break
        
        if MsdnSapiEvents.heard:
            print("RESULT: RECOGNITION SUCCESSFUL.")
            success = True
        else:
            print("RESULT: NO RECOGNITION EVENT RECEIVED.")
            success = False

    except Exception as e:
        print(f"Test failed with exception: {e}")
        success = False
    finally:
        pythoncom.CoUninitialize()
        
    return success

if __name__ == "__main__":
    print("Beginning SAPI5 interactive command grammar tests.")
    
    # Test 1: Full MSDN specification: use_dynamic_flag=True, set_engine_state=True
    print("\n================== TEST 1 (MSDN SPECIFICATION) ==================")
    success = test_msdn_grammar(use_dynamic_flag=True, set_engine_state=True)
    
    if not success:
        # If it fails, let's try other combinations to isolate
        print("\n================== TEST 2 (NO ENGINE STATE SET) ==================")
        test_msdn_grammar(use_dynamic_flag=True, set_engine_state=False)
        
        print("\n================== TEST 3 (NO DYNAMIC FLAG SET) ==================")
        test_msdn_grammar(use_dynamic_flag=False, set_engine_state=True)
