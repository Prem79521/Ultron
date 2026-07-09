import win32com.client
import pythoncom
import time

class SapiEventSink:
    def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
        newResult = win32com.client.Dispatch(Result)
        print(f"\n[SUCCESS] SAPI Heard: {newResult.PhraseInfo.GetText()}")

def test_inproc_mic():
    pythoncom.CoInitialize()
    print("Initializing In-Process Engine...")
    engine = win32com.client.Dispatch("SAPI.SpInprocRecognizer")
    
    print("\n--- Available Audio Inputs ---")
    category = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
    category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput", False)
    
    tokens = category.EnumerateTokens()
    for i in range(tokens.Count):
        token = tokens.Item(i)
        print(f"[{i}] {token.GetDescription()}")

    print("\n--- Binding Audio ---")
    # category.Default is a string property containing the registry path of the default token
    default_audio_id = category.Default
    
    default_audio_token = win32com.client.Dispatch("SAPI.SpObjectToken")
    default_audio_token.SetId(default_audio_id)
    
    engine.AudioInput = default_audio_token
    print(f"Bound to: {engine.AudioInput.GetDescription()}")

    # Setup Context and Events
    context = engine.CreateRecoContext()
    events = win32com.client.WithEvents(context, SapiEventSink)

    # Setup Grammar
    grammar = context.CreateGrammar(0)
    grammar.DictationSetState(0)
    rule = grammar.Rules.Add("WakeRule", 1, 32)
    rule.InitialState.AddWordTransition(None, "Arise")
    grammar.Rules.Commit()
    grammar.CmdSetRuleState("WakeRule", 1)

    print("\nListening for 'Arise'... (15-second timeout. Speak now. Press Ctrl+C to stop)")
    
    start_time = time.time()
    try:
        while time.time() - start_time < 15:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting diagnostic.")
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    test_inproc_mic()
