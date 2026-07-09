"""
ULTRON UI Diagnostic Script — Active status checking of Qt windows and event loops.
"""

import sys
import os
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Add workspace directory to python path
sys.path.insert(0, os.getcwd())

from ultron.core import CoreSystem
from ultron.memory import MemoryManager
from ultron.skills import SkillRegistry, register_all_skills
from ultron.voice import Pyttsx3VoiceProvider
from ui.application import UltronUIApplication

def run_diagnostics():
    core = CoreSystem()
    db_path = core.config.get("memory", "db_path", "ultron_memory.db")
    memory = MemoryManager(db_path=db_path)
    
    skills = SkillRegistry(core, memory)
    register_all_skills(skills)
    core.register_module("skills_registry", skills)
    
    voice = Pyttsx3VoiceProvider()
    core.session.initialize_session(core.events)
    
    ui_app = UltronUIApplication(core, memory, voice, skills)
    
    # Setup diagnostic timer to run after entering the event loop
    def check_status():
        print("\n=== UI DIAGNOSTIC RUN ===")
        print(f"QApplication active: {QApplication.instance() is not None}")
        
        # Check boot screen status
        boot = ui_app.boot_screen
        if boot:
            print("--- Boot Screen ---")
            print(f"Created: True")
            print(f"Is Visible: {boot.isVisible()}")
            print(f"Is Hidden: {boot.isHidden()}")
            print(f"Geometry: {boot.geometry()}")
            print(f"Opacity: {boot.windowOpacity()}")
            print(f"Window State: {boot.windowState()}")
        else:
            print("Boot Screen: NOT CREATED")
            
        # Check main window status
        main_win = ui_app.main_window
        if main_win:
            print("--- Main Window ---")
            print(f"Created: True")
            print(f"Is Visible: {main_win.isVisible()}")
            print(f"Is Hidden: {main_win.isHidden()}")
            print(f"Geometry: {main_win.geometry()}")
            print(f"Opacity: {main_win.windowOpacity()}")
            print(f"Window State: {main_win.windowState()}")
        else:
            print("Main Window: NOT YET CREATED")
            
        print("=========================\n")
        
        # Let's exit after checking
        QApplication.quit()

    # Trigger diagnostics after 6 seconds (to allow boot sequence completion)
    QTimer.singleShot(6000, check_status)
    
    # Run loop
    sys.exit(ui_app.start())

if __name__ == "__main__":
    run_diagnostics()
