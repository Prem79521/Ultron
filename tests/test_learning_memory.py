"""
Unit tests for the learning memory store.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.memory import MemoryManager
from ultron.core.cognitive_os.learning_memory import LearningMemory

class TestLearningMemory(unittest.TestCase):
    def setUp(self):
        # Initialize an in-memory or custom temp db for clean test context
        self.db_path = "test_learning_memory.db"
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass
        self.mgr = MemoryManager(self.db_path)
        self.learning = LearningMemory(self.mgr)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_learn_and_retrieve(self):
        # Mapping does not exist initially
        self.assertIsNone(self.learning.get_mapping("open spiderman"))

        # Learn a mapping
        self.learning.learn("open spiderman", "Spider-Man Remastered", 0.85, "alias_match_confirm")
        
        # Verify it was successfully written and retrieved
        mapping = self.learning.get_mapping("open spiderman")
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping["resolved_entity"], "Spider-Man Remastered")
        self.assertEqual(mapping["launch_count"], 1)

        # Re-learning increments count
        self.learning.learn("open spiderman", "Spider-Man Remastered", 0.90, "direct_match")
        mapping = self.learning.get_mapping("open spiderman")
        self.assertEqual(mapping["launch_count"], 2)
        self.assertEqual(mapping["confidence"], 0.90)

if __name__ == "__main__":
    unittest.main()
