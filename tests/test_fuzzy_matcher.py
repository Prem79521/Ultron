"""
Unit tests for the fuzzy matching subsystem.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.core.cognitive_os.base_matcher import DifflibMatcher

class TestFuzzyMatcher(unittest.TestCase):
    def setUp(self):
        self.matcher = DifflibMatcher()

    def test_similarity_ratios(self):
        # High matching ratio
        self.assertGreaterEqual(self.matcher.ratio("chrome", "chorme"), 0.8)
        self.assertGreaterEqual(self.matcher.ratio("calculator", "calculater"), 0.8)
        self.assertGreaterEqual(self.matcher.ratio("photoshop", "photoshp"), 0.8)
        
        # Low matching ratio
        self.assertLess(self.matcher.ratio("chrome", "firefox"), 0.4)

    def test_get_matches(self):
        possibilities = ["Chrome", "Mozilla Firefox", "Microsoft Edge", "Brave Browser"]
        matches = self.matcher.get_matches("chorme", possibilities, cutoff=0.6)
        
        self.assertTrue(len(matches) > 0)
        self.assertEqual(matches[0][0], "Chrome")
        self.assertGreaterEqual(matches[0][1], 0.6)

if __name__ == "__main__":
    unittest.main()
