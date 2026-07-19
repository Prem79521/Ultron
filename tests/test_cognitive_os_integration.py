"""
Integration tests for the ULTRON Cognitive Operating System (Phase 2).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.core import CoreSystem
from ultron.memory import MemoryManager
from ultron.skills.registry import SkillRegistry
from ultron.skills.command_dispatcher import CommandDispatcher
from ultron.skills.application_skill import ApplicationSkill
from ultron.skills.website_skill import WebsiteSkill
import ultron.core.voice_session_manager as vsm

class TestCognitiveOSIntegration(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_integration.db"
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass
                
        self.memory = MemoryManager(self.db_name)
        self.core = CoreSystem()
        self.skills = SkillRegistry(self.core, self.memory)
        
        self.skills.register_skill("ApplicationSkill", ApplicationSkill)
        self.skills.register_skill("WebsiteSkill", WebsiteSkill)
        self.skills.register_skill("CommandDispatcher", CommandDispatcher)
        self.core.register_module("skills_registry", self.skills)
        
        self.dispatcher = self.skills.get_skill("CommandDispatcher")
        
        # Instantiate a dummy Voice Session Manager and register globally
        self.session_mgr = vsm.UltronVoiceSessionManager(None)
        vsm.voice_session_manager = self.session_mgr

        # Warmup dispatcher to initialize graph and inject hermetic mock Chrome app
        self.dispatcher.execute({"command": "warmup"})
        from ultron.core.cognitive_os.entity_graph import UltronEntity
        self.dispatcher._entity_graph.add_entity(UltronEntity(
            name="Google Chrome",
            category="application",
            aliases={"google chrome": 1.0, "chorme": 0.8},
            executable="C:\\Windows\\notepad.exe"
        ))

    def tearDown(self):
        vsm.voice_session_manager = None
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass

    def test_confirmation_and_learning_flow(self):
        # 1. First run: "open chorme" (Fuzzy match)
        # Should result in a confirmation prompt
        res = self.dispatcher.execute({"command": "open chorme"})
        self.assertTrue(res["success"])
        self.assertIn("confirm", res["results"][0]["task_id"])
        self.assertIsNotNone(self.session_mgr.pending_confirmation)
        self.assertEqual(self.session_mgr.pending_confirmation["entity"].name, "Google Chrome")
        
        # 2. Second run: reply "yes" to confirm the action
        res_confirm = self.dispatcher.execute({"command": "yes"})
        self.assertTrue(res_confirm["success"])
        self.assertEqual(res_confirm["response"], "Opening Google Chrome.")
        self.assertIsNone(self.session_mgr.pending_confirmation)

        # 3. Third run: "open chorme" again
        # Because we learned this mapping, it should open instantly without confirmation!
        res_instant = self.dispatcher.execute({"command": "open chorme"})
        self.assertTrue(res_instant["success"])
        self.assertEqual(res_instant["response"], "Opening Google Chrome.")
        # Make sure it did not ask for confirmation
        self.assertNotEqual(res_instant["results"][0]["task_id"], "confirm")
        self.assertEqual(res_instant["results"][0]["task_id"], "application") # resolves via learned category

if __name__ == "__main__":
    unittest.main()
