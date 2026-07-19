"""
Unit tests for ULTRON OS Skills (Phase 1 / Phase 2 Integration)
"""

import os
import sys
import unittest
from typing import Dict, Any

# Ensure codebase root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.core import CoreSystem
from ultron.memory import MemoryManager
from ultron.skills.registry import SkillRegistry
from ultron.skills.command_dispatcher import CommandDispatcher
from ultron.skills.browser_skill import BrowserSkill
from ultron.skills.website_skill import WebsiteSkill
from ultron.skills.search_skill import SearchSkill
from ultron.skills.application_skill import ApplicationSkill
from ultron.skills.windows_skill import WindowsSkill
from ultron.core.cognitive_os.intent_engine import IntentEngine

class TestOSSkills(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_os_skills.db"
        self.memory = MemoryManager(self.db_name)
        self.core = CoreSystem()
        self.skills = SkillRegistry(self.core, self.memory)
        
        # Register new skills
        self.skills.register_skill("BrowserSkill", BrowserSkill)
        self.skills.register_skill("WebsiteSkill", WebsiteSkill)
        self.skills.register_skill("SearchSkill", SearchSkill)
        self.skills.register_skill("ApplicationSkill", ApplicationSkill)
        self.skills.register_skill("WindowsSkill", WindowsSkill)
        self.skills.register_skill("CommandDispatcher", CommandDispatcher)
        
        self.dispatcher = self.skills.get_skill("CommandDispatcher")
        self.intent_engine = IntentEngine()

    def tearDown(self):
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass

    def test_command_parser_via_intent_engine(self):
        # Open Application Intent
        res = self.intent_engine.classify("Open Chrome")
        self.assertEqual(res.intent, "OPEN_APPLICATION")
        self.assertEqual(res.entity, "Chrome")

        # Open Website Intent
        res = self.intent_engine.classify("Open YouTube")
        self.assertEqual(res.intent, "OPEN_WEBSITE")
        self.assertEqual(res.entity, "YouTube")

        # Google Search Intent
        res = self.intent_engine.classify("Search AI agents")
        self.assertEqual(res.intent, "WEB_SEARCH")
        self.assertEqual(res.entity, "AI agents")

        # YouTube Search Intent
        res = self.intent_engine.classify("Play Jarvis edit on YouTube")
        self.assertEqual(res.intent, "WEB_SEARCH")
        self.assertEqual(res.entity, "Play Jarvis edit")
        self.assertEqual(res.metadata.get("provider"), "youtube")

        # Folder Intent
        res = self.intent_engine.classify("Open Downloads")
        self.assertEqual(res.intent, "OPEN_FOLDER")
        self.assertEqual(res.entity, "Downloads")

        # Settings Intent
        res = self.intent_engine.classify("Open Wifi Settings")
        self.assertEqual(res.intent, "OPEN_SETTINGS")
        self.assertEqual(res.entity, "Wifi Settings")

        # App Intent
        res = self.intent_engine.classify("Open Calculator")
        self.assertEqual(res.intent, "OPEN_APPLICATION")
        self.assertEqual(res.entity, "Calculator")

    def test_browser_skill_error_handling(self):
        browser_skill = self.skills.get_skill("BrowserSkill")
        res = browser_skill.execute({"browser": "invalid_browser"})
        self.assertFalse(res["success"])
        self.assertIn("not supported", res["spoken_response"])

    def test_website_skill(self):
        website_skill = self.skills.get_skill("WebsiteSkill")
        res = website_skill.execute({"website": "youtube"})
        self.assertTrue(res["success"])
        self.assertEqual(res["spoken_response"], "Opening YouTube.")

    def test_search_skill(self):
        search_skill = self.skills.get_skill("SearchSkill")
        res = search_skill.execute({"action": "google_search", "query": "RTX 5060 benchmark"})
        self.assertTrue(res["success"])
        self.assertIn("Searching Google", res["spoken_response"])

    def test_application_skill(self):
        app_skill = self.skills.get_skill("ApplicationSkill")
        res = app_skill.execute({"app": "notepad"})
        self.assertTrue(res["success"])
        self.assertEqual(res["spoken_response"], "Opening Notepad.")

    def test_windows_skill_folders(self):
        win_skill = self.skills.get_skill("WindowsSkill")
        res = win_skill.execute({"action": "open_folder", "folder": "downloads"})
        self.assertIn("success", res)
        self.assertIn("spoken_response", res)

    def test_windows_skill_settings(self):
        win_skill = self.skills.get_skill("WindowsSkill")
        res = win_skill.execute({"action": "open_settings", "setting": "bluetooth"})
        self.assertTrue(res["success"])
        self.assertEqual(res["spoken_response"], "Opening Bluetooth Settings.")

    def test_dispatcher_integration(self):
        self.core.register_module("skills_registry", self.skills)
        res = self.dispatcher.execute({"command": "Can you open calculator?"})
        self.assertTrue(res["success"])
        self.assertEqual(res["response"], "Opening Calculator.")

if __name__ == "__main__":
    unittest.main()
