"""
Unit tests for the alias generator subsystem.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.core.cognitive_os.alias_generator import generate_aliases

class TestAliasGenerator(unittest.TestCase):
    def test_chrome_aliases(self):
        aliases = generate_aliases("Google Chrome")
        self.assertEqual(aliases.get("chrome"), 1.0)
        self.assertEqual(aliases.get("google chrome"), 1.0)
        self.assertEqual(aliases.get("browser"), 0.4)
        self.assertEqual(aliases.get("google"), 0.2)

    def test_vscode_aliases(self):
        aliases = generate_aliases("Visual Studio Code")
        self.assertEqual(aliases.get("vscode"), 1.0)
        self.assertEqual(aliases.get("vs code"), 1.0)
        self.assertEqual(aliases.get("code"), 0.8)
        self.assertEqual(aliases.get("visual studio"), 0.6)

    def test_spiderman_aliases(self):
        aliases = generate_aliases("Spider-Man Remastered")
        self.assertEqual(aliases.get("spiderman"), 1.0)
        self.assertEqual(aliases.get("spider man"), 1.0)
        self.assertEqual(aliases.get("spiderman remastered"), 1.0)
        self.assertEqual(aliases.get("spider man game"), 0.7)

if __name__ == "__main__":
    unittest.main()
