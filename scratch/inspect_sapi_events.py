"""
SAPI5 Detailed Event Inspector
Inspects fine-grained SAPI recognition events (SpeechStart, Hypothesis, FalseRecognition, Recognition)
to see if SAPI hears the voice but rejects it due to low confidence.
"""

import sys
import os
import time
import pythoncom
import win32com.client

class DetailedSapiEvents:
    def OnSpeechStart(self, StreamNumber, StreamPosition):
        print("\n[EVENT] OnSpeechStart: Speech detected in audio stream.")

    def OnHypothesis(self, StreamNumber, StreamPosition, Result):
        try:
            newResult = win32com.client.CastTo(Result, "ISpeechRecoResult")
            text = newResult.PhraseInfo.GetText()
            print(f"[EVENT] OnHypothesis: '{text}'")
        except Exception as e:
            print(f"[EVENT] OnHypothesis error: {e}")

    def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
        try:
            newResult = win32com.client.CastTo(Result, "ISpeechRecoResult")
            text = newResult.PhraseInfo.GetText()
            print(f"\n[EVENT] OnRecognition (SUCCESS): '{text}'")
        except Exception as e:
            print(f"[EVENT] OnRecognition error: {e}")

    def OnFalseRecognition(self, StreamNumber, StreamPosition, Result):
        try:
            newResult = win32com.client.CastTo(Result, "ISpeechRecoResult")
            text = newResult.PhraseInfo.GetText()
            print(f"\n[EVENT] OnFalseRecognition (REJECTED): Best guess was '{text}'")
        except Exception as e:
            print(f"[EVENT] OnFalseRecognition error: {e}")

def run_detailed_event_test():
    pythoncom.CoInitialize()
    try:
        # Create In-Process Recognizer
        engine = win32com.client.Dispatch("SAPI.SpInprocRecognizer")
        
        # Bind audio input
        category = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
        category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput", False)
        default_audio_token = win32com.client.Dispatch("SAPI.SpObjectToken")
        default_audio_token.SetId(category.Default)
        engine.AudioInput = default_audio_token
        print(f"Bound to audio device: {engine.AudioInput.GetDescription()}")

        # Ensure active state
        engine.State = 1 # SRSActive = 1
        
        context = engine.CreateRecoContext()
        events = win32com.client.WithEvents(context, DetailedSapiEvents)
        
        grammar = context.CreateGrammar(1)
        
        # Rule attributes: SRATopLevel=1, SRADynamic=32
        rule = grammar.Rules.Add("WakeRule", 33, 1)
        rule.InitialState.AddWordTransition(None, "Arise")
        grammar.Rules.Commit()
        
        grammar.CmdSetRuleState("WakeRule", 1) # SGDSActive = 1
        
        print("\n--- Detailed Event Monitoring Started ---")
        print("Please speak the wake word 'Arise' or make other sounds/speech.")
        print("Monitoring for 15 seconds. Speak now...")
        
        start_time = time.time()
        while time.time() - start_time < 15:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)

        print("\n--- Monitoring Stopped ---")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    run_detailed_event_test()
