"""
SAPI5 Shared Recognizer Command Grammar Test
Tests if SAPI.SpSharedRecognizer can successfully compile and run 
a dynamic command grammar for the word "Arise".
"""

import sys
import time
import pythoncom
import win32com.client

class SharedSapiEvents:
    heard = False
    def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
        SharedSapiEvents.heard = True
        try:
            newResult = win32com.client.CastTo(Result, "ISpeechRecoResult")
            text = newResult.PhraseInfo.GetText()
            print(f"\n>>> [SUCCESS] Shared SAPI Heard: '{text}'!")
        except Exception as e:
            print(f"Error in callback: {e}")

def run_shared_test():
    print("Initializing Shared Recognizer...")
    pythoncom.CoInitialize()
    
    try:
        # Create Shared Recognizer (uses system microphone automatically)
        engine = win32com.client.Dispatch("SAPI.SpSharedRecognizer")
        print("Shared Recognizer created.")

        context = engine.CreateRecoContext()
        events = win32com.client.WithEvents(context, SharedSapiEvents)
        print("Events bound.")

        grammar = context.CreateGrammar(1)
        
        # Add rule: SRATopLevel = 1, SRADynamic = 32
        rule = grammar.Rules.Add("WakeRule", 33, 1)
        rule.InitialState.AddWordTransition(None, "Arise")
        grammar.Rules.Commit()
        print("Dynamic grammar committed.")

        grammar.CmdSetRuleState("WakeRule", 1) # SGDSActive = 1
        print("Rule 'WakeRule' set to SGDSActive.")

        print("Listening for 'Arise' via Shared Recognizer... (15 seconds timeout. Speak now!)")
        SharedSapiEvents.heard = False
        start_time = time.time()
        while time.time() - start_time < 15:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)
            if SharedSapiEvents.heard:
                break

        if SharedSapiEvents.heard:
            print("RESULT: Shared recognizer successfully heard command.")
        else:
            print("RESULT: No events heard on Shared recognizer.")

    except Exception as e:
        print(f"Failed with exception: {e}")
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    run_shared_test()
