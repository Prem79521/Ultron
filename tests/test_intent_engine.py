"""
Unit tests for the Intent Engine.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.core.cognitive_os.intent_engine import IntentEngine

class TestIntentEngine(unittest.TestCase):
    def setUp(self):
        self.engine = IntentEngine()

    def test_open_application_intent(self):
        res1 = self.engine.classify("open chrome")
        self.assertEqual(res1.intent, "OPEN_APPLICATION")
        self.assertEqual(res1.entity, "chrome")

        res2 = self.engine.classify("launch chrome")
        self.assertEqual(res2.intent, "OPEN_APPLICATION")
        self.assertEqual(res2.entity, "chrome")

    def test_web_search_intent(self):
        res1 = self.engine.classify("search rtx 5060 on google")
        self.assertEqual(res1.intent, "WEB_SEARCH")
        self.assertEqual(res1.entity, "search rtx 5060")
        self.assertEqual(res1.metadata.get("provider"), "google")

        res2 = self.engine.classify("google Python tutorials")
        self.assertEqual(res2.intent, "WEB_SEARCH")
        self.assertEqual(res2.entity, "Python tutorials")

    def test_open_website_intent(self):
        res1 = self.engine.classify("open google")
        self.assertEqual(res1.intent, "OPEN_WEBSITE")
        self.assertEqual(res1.entity, "google")

        res2 = self.engine.classify("open gmail")
        self.assertEqual(res2.intent, "OPEN_WEBSITE")
        self.assertEqual(res2.entity, "gmail")

        res3 = self.engine.classify("go to github.com")
        self.assertEqual(res3.intent, "OPEN_WEBSITE")
        self.assertEqual(res3.entity, "github.com")

    def test_open_folder_intent(self):
        res1 = self.engine.classify("open downloads")
        self.assertEqual(res1.intent, "OPEN_FOLDER")
        self.assertEqual(res1.entity, "Downloads")

        res2 = self.engine.classify("open documents folder")
        self.assertEqual(res2.intent, "OPEN_FOLDER")
        self.assertEqual(res2.entity, "Documents")

if __name__ == "__main__":
    unittest.main()
