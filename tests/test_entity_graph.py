"""
Unit tests for the Entity Knowledge Graph.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.core.cognitive_os.entity_graph import EntityKnowledgeGraph, UltronEntity
from ultron.core.cognitive_os.base_matcher import DifflibMatcher

class TestEntityGraph(unittest.TestCase):
    def setUp(self):
        self.graph = EntityKnowledgeGraph()
        self.matcher = DifflibMatcher()

    def test_prepopulated_entities(self):
        # Verify default entities loaded on init
        self.assertIsNotNone(self.graph.get_entity("Downloads"))
        self.assertIsNotNone(self.graph.get_entity("Calculator"))
        self.assertIsNotNone(self.graph.get_entity("YouTube"))
        self.assertIsNotNone(self.graph.get_entity("Bluetooth"))

    def test_custom_entity(self):
        entity = UltronEntity(
            name="Visual Studio Code",
            category="application",
            aliases={"vscode": 1.0, "vs code": 1.0}
        )
        self.graph.add_entity(entity)
        self.assertEqual(self.graph.get_entity("Visual Studio Code").name, "Visual Studio Code")

    def test_weighted_alias_search(self):
        # We query using an alias with specific weights
        entity = UltronEntity(
            name="Google Chrome",
            category="application",
            aliases={"chrome": 1.0, "browser": 0.4, "google": 0.2}
        )
        self.graph.add_entity(entity)

        # "chrome" matches with high weight
        matches_chrome = self.graph.search("chrome", self.matcher, cutoff=0.5)
        self.assertTrue(len(matches_chrome) > 0)
        self.assertEqual(matches_chrome[0][0].name, "Google Chrome")
        self.assertGreaterEqual(matches_chrome[0][1], 0.9)

        # "browser" matches with medium weight
        matches_browser = self.graph.search("browser", self.matcher, cutoff=0.3)
        self.assertTrue(len(matches_browser) > 0)
        self.assertLess(matches_browser[0][1], 0.6)

if __name__ == "__main__":
    unittest.main()
