"""
ULTRON SAPI5 Root Cause Investigation: XML SAPI Grammar Implementation
Minimal command grammar built using Microsoft's recommended XML file loading.
Using the correct LangID for English - UK (809).
"""

import sys
import os
import time
import pythoncom
import win32com.client

SRSActive = 1  # Recognizer is active and processing audio

class XmlSapiEvents:
    heard = False
    def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
        XmlSapiEvents.heard = True
        try:
            newResult = win32com.client.CastTo(Result, "ISpeechRecoResult")
            text = newResult.PhraseInfo.GetText()
            print(f"\n>>> [SUCCESS] XML SAPI Heard: '{text}'!")
        except Exception as e:
            print(f"Error in callback: {e}")

def run_xml_test():
    # 1. Create the XML Grammar file with LANGID="809" (UK English in hex)
    xml_content = """<GRAMMAR LANGID="809">
    <RULE NAME="WakeRule" TOPLEVEL="ACTIVE">
        <L>
            <P>Arise</P>
        </L>
    </RULE>
</GRAMMAR>
"""
    xml_path = os.path.abspath("scratch/grammar.xml")
    os.makedirs(os.path.dirname(xml_path), exist_ok=True)
    with open(xml_path, "w") as f:
        f.write(xml_content)
    print(f"XML grammar file written to: {xml_path}")

    pythoncom.CoInitialize()
    
    # 2. Initialize In-Process Recognizer
    engine = win32com.client.Dispatch("SAPI.SpInprocRecognizer")
    
    # 3. Bind default audio input
    category = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
    category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput", False)
    default_audio_token = win32com.client.Dispatch("SAPI.SpObjectToken")
    default_audio_token.SetId(category.Default)
    engine.AudioInput = default_audio_token
    print(f"Bound to audio device: {engine.AudioInput.GetDescription()}")

    # 4. Set Engine state to Active
    engine.State = SRSActive
    print("Recognizer state set to SRSActive.")

    # 5. Create RecoContext & Events
    context = engine.CreateRecoContext()
    events = win32com.client.WithEvents(context, XmlSapiEvents)

    # 6. Create Grammar and Load XML
    grammar = context.CreateGrammar(1)
    
    # SLOStatic = 0
    grammar.CmdLoadFromFile(xml_path, 0)
    print("XML Grammar loaded successfully via CmdLoadFromFile.")

    # 7. Activate rule
    grammar.CmdSetRuleState("WakeRule", 1) # SGDSActive = 1
    print("Rule 'WakeRule' activated.")

    # 8. Start message pump
    print("Listening for 'Arise'... (15 seconds timeout. Speak now!)")
    XmlSapiEvents.heard = False
    start_time = time.time()
    try:
        while time.time() - start_time < 15:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)
            if XmlSapiEvents.heard:
                break
    except KeyboardInterrupt:
        print("Aborted.")

    if XmlSapiEvents.heard:
        print("RESULT: RECOGNITION SUCCESSFUL.")
    else:
        print("RESULT: NO RECOGNITION EVENT RECEIVED.")

    pythoncom.CoUninitialize()

if __name__ == "__main__":
    run_xml_test()
