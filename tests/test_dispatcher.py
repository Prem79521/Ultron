"""
Unit tests for the integrated CommandDispatcher.
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

class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_dispatcher.db"
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass
                
        self.memory = MemoryManager(self.db_name)
        self.core = CoreSystem()
        self.skills = SkillRegistry(self.core, self.memory)
        
        self.skills.register_skill("ApplicationSkill", ApplicationSkill)
        self.skills.register_skill("CommandDispatcher", CommandDispatcher)
        
        self.core.register_module("skills_registry", self.skills)
        self.dispatcher = self.skills.get_skill("CommandDispatcher")

    def tearDown(self):
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass

    def test_dispatcher_fuzzy_execute(self):
        # "open calculater" -> fuzzy matches prepopulated Calculator (100% or high score)
        res = self.dispatcher.execute({"command": "open calculater"})
        self.assertTrue(res["success"])
        self.assertEqual(res["response"], "Opening Calculator.")

if __name__ == "__main__":
    unittest.main()
