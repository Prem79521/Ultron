"""
ULTRON Onboarding Integration Diagnostic Test.
Simulates first-time boot, user name entry, and SQLite verification.
"""

import sys
import os
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

sys.path.insert(0, os.getcwd())

# Delete existing DB to force first launch state
DB_FILE = "ultron_memory.db"
if os.path.exists(DB_FILE):
    try:
        os.remove(DB_FILE)
        print("[TEST] Removed existing ultron_memory.db for clean onboarding test.")
    except Exception as e:
        print(f"[TEST] Warning: Could not remove DB: {e}")

from ultron.core import CoreSystem
from ultron.memory import MemoryManager
from ultron.skills import SkillRegistry, register_all_skills
from ultron.voice import Pyttsx3VoiceProvider
from ui.application import UltronUIApplication

def run_test():
    core = CoreSystem()
    memory = MemoryManager(db_path=DB_FILE)
    
    skills = SkillRegistry(core, memory)
    register_all_skills(skills)
    core.register_module("skills_registry", skills)
    
    # Use Pyttsx3VoiceProvider
    voice = Pyttsx3VoiceProvider()
    core.session.initialize_session(core.events)
    
    ui_app = UltronUIApplication(core, memory, voice, skills)
    
    def test_sequence():
        print("\n=== STARTING ONBOARDING TEST ===")
        main_win = ui_app.main_window
        if not main_win:
            print("[FAIL] Main window not created.")
            QApplication.quit()
            return
            
        print(f"Initial UI State: {main_win.operator_state}")
        print(f"Greeting text: '{main_win.greeting_lbl.text()}'")
        
        if main_win.operator_state != "onboarding":
            print("[FAIL] UI not in onboarding mode on clean boot.")
            QApplication.quit()
            return
            
        # Simulate typing 'Prem' and submitting
        print("[TEST] Simulating typing 'Prem' in input box...")
        main_win.cmd_input.setText("Prem")
        print("[TEST] Submitting command...")
        main_win.submit_command()
        
        # Allow database write to complete
        time.sleep(0.5)
        
        print(f"Post-Onboarding UI State: {main_win.operator_state}")
        print(f"Greeting text: '{main_win.greeting_lbl.text()}'")
        
        # Verify SQLite preference value
        pref_records = memory.list_records("preference")
        display_name = None
        for r in pref_records:
            if r["title"] == "display_name":
                display_name = r["content"]
                
        print(f"UME Stored Name: '{display_name}'")
        
        if display_name == "Prem" and main_win.operator_state == "normal":
            print("[SUCCESS] Onboarding completed and verified in database!")
        else:
            print("[FAIL] Onboarding verification failed.")

            
        print("===============================\n")
        
        # Terminate test cleanly
        ui_app.main_window.close_gracefully()

    # Trigger diagnostic sequence after boot sequence completes (6 seconds)
    QTimer.singleShot(6000, test_sequence)
    
    # Start QApplication loop
    sys.exit(ui_app.start())

if __name__ == "__main__":
    run_test()
