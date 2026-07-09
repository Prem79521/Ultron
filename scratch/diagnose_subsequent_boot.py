"""
ULTRON Subsequent Launch Diagnostic Test.
Verifies that UME retrieves the previously stored operator name and skips onboarding.
"""

import sys
import os
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

sys.path.insert(0, os.getcwd())

DB_FILE = "ultron_memory.db"
if not os.path.exists(DB_FILE):
    print("[TEST] Error: ultron_memory.db does not exist. Run onboarding test first.")
    sys.exit(1)

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
    
    voice = Pyttsx3VoiceProvider()
    core.session.initialize_session(core.events)
    
    ui_app = UltronUIApplication(core, memory, voice, skills)
    
    def test_sequence():
        print("\n=== STARTING SUBSEQUENT BOOT TEST ===")
        main_win = ui_app.main_window
        if not main_win:
            print("[FAIL] Main window not created.")
            QApplication.quit()
            return
            
        print(f"UI State: {main_win.operator_state}")
        print(f"Operator Display Name: '{main_win.display_name}'")
        print(f"Greeting text: '{main_win.greeting_lbl.text()}'")
        
        # Verify onboarding is skipped
        if main_win.operator_state == "normal" and main_win.display_name == "Prem":
            print("[SUCCESS] Skip onboarding verified! Operator profile retrieved dynamically.")
        else:
            print("[FAIL] Operator profile not retrieved correctly.")
            
        print("=====================================\n")
        
        # Terminate cleanly
        ui_app.main_window.close_gracefully()

    QTimer.singleShot(6000, test_sequence)
    sys.exit(ui_app.start())

if __name__ == "__main__":
    run_test()
