"""
Unit tests for Phase 4 Cognitive OS layers: Spell Correction, Shell Namespaces,
Workspace folders, Candidate Ranking, and System Power Actions.
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
from ultron.core.cognitive_os.entity_graph import UltronEntity
import ultron.core.voice_session_manager as vsm


class TestPhase4Resolver(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_phase4.db"
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
        
        # Instantiate voice session manager and register
        self.session_mgr = vsm.UltronVoiceSessionManager(None)
        vsm.voice_session_manager = self.session_mgr

        # Initialize pipeline
        self.dispatcher.execute({"command": "warmup"})

    def tearDown(self):
        vsm.voice_session_manager = None
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass

    def test_spell_corrector_typo_tolerance(self):
        # 1. Test verb correction
        corrected = self.dispatcher._spell_corrector.correct("opem chrome")
        self.assertEqual(corrected, "open chrome")

        # 2. Test system noun correction
        corrected_noun = self.dispatcher._spell_corrector.correct("open chorme")
        self.assertEqual(corrected_noun, "open chrome")

        # 3. Test multi-word and complex typos
        corrected_complex = self.dispatcher._spell_corrector.correct("open powrpoint")
        self.assertEqual(corrected_complex, "open powerpoint")

    def test_shell_namespace_resolution(self):
        # Resolve Recycle Bin
        res = self.dispatcher.execute({"command": "open recycle bin"})
        self.assertTrue(res["success"])
        self.assertIn("Recycle Bin", res["response"])
        self.assertEqual(res["results"][0]["task_id"], "folder")
        
        # Resolve Downloads
        res_downloads = self.dispatcher.execute({"command": "open downloads"})
        self.assertTrue(res_downloads["success"])
        self.assertIn("Downloads", res_downloads["response"])

    def test_workspace_folder_resolution(self):
        res = self.dispatcher.execute({"command": "open my folder"})
        self.assertTrue(res["success"])
        self.assertIn("project folder", res["response"].lower())
        self.assertEqual(res["results"][0]["task_id"], "folder")

    def test_system_power_command_resolution(self):
        res = self.dispatcher.execute({"command": "shutdown pc"})
        self.assertTrue(res["success"])
        self.assertIn("performing shutdown pc", res["response"].lower())

    def test_ranking_and_multiple_choices_dialog(self):
        # Inject multiple entities starting with/related to "nvidia" to trigger confirmation choices
        self.dispatcher._entity_graph.add_entity(UltronEntity(
            name="NVIDIA App",
            category="application",
            aliases={"nvidia app": 1.0, "nvidia": 0.8},
            executable="C:\\Windows\\notepad.exe"
        ))
        self.dispatcher._entity_graph.add_entity(UltronEntity(
            name="NVIDIA Control Panel",
            category="application",
            aliases={"nvidia control panel": 1.0, "nvidia": 0.8},
            executable="C:\\Windows\\notepad.exe"
        ))

        # Query "open nvidia"
        res = self.dispatcher.execute({"command": "open nvidia"})
        self.assertTrue(res["success"])
        # Should ask for multiple choice confirmation
        self.assertIn("Did you mean: 1. NVIDIA App, or 2. NVIDIA Control Panel", res["response"])
        self.assertIsNotNone(self.session_mgr.pending_confirmation)
        self.assertEqual(self.session_mgr.pending_confirmation["type"], "choices")
        self.assertEqual(len(self.session_mgr.pending_confirmation["choices"]), 2)

        # Confirm choice 1
        res_confirm = self.dispatcher.execute({"command": "one"})
        self.assertTrue(res_confirm["success"])
        self.assertIn("NVIDIA App", res_confirm["response"])
        self.assertIsNone(self.session_mgr.pending_confirmation)


if __name__ == "__main__":
    unittest.main()
