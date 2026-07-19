"""
Unit tests for the modular resolver chain pipeline.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.memory import MemoryManager
from ultron.core.cognitive_os.base_matcher import DifflibMatcher
from ultron.core.cognitive_os.entity_graph import EntityKnowledgeGraph, UltronEntity
from ultron.core.cognitive_os.learning_memory import LearningMemory
from ultron.core.cognitive_os.intent_engine import IntentEngine
from ultron.core.cognitive_os.resolver_chain import (
    LearningMemoryResolver, AliasResolver, ApplicationResolver,
    WebsiteResolver, WebSearchResolver, FailureResolver
)

class TestResolverPipeline(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_resolver.db"
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass
        
        self.mgr = MemoryManager(self.db_path)
        self.matcher = DifflibMatcher()
        self.graph = EntityKnowledgeGraph()
        self.learning = LearningMemory(self.mgr)
        self.intent_engine = IntentEngine()

        # Build Resolver Chain
        self.chain = LearningMemoryResolver(self.learning)
        r_alias = AliasResolver(self.matcher)
        r_app = ApplicationResolver(self.matcher)
        r_web = WebsiteResolver()
        r_search = WebSearchResolver()
        r_fail = FailureResolver()
        
        self.chain.set_next(r_alias).set_next(r_app).set_next(r_web).set_next(r_search).set_next(r_fail)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_direct_alias_resolution(self):
        # Setup specific Chrome entity in graph
        chrome = UltronEntity(
            name="Google Chrome",
            category="application",
            aliases={"chrome": 1.0, "google chrome": 1.0}
        )
        self.graph.add_entity(chrome)

        # 1. Exact match on alias
        intent = self.intent_engine.classify("open chrome")
        context = {"entity_graph": self.graph, "matcher": self.matcher}
        res = self.chain.resolve(intent, context)

        self.assertEqual(res["action"], "execute")
        self.assertEqual(res["entity"].name, "Google Chrome")
        self.assertEqual(res["source"], "alias_match")

    def test_fuzzy_confirmation_resolution(self):
        chrome = UltronEntity(
            name="Google Chrome",
            category="application",
            aliases={"chrome": 1.0}
        )
        self.graph.add_entity(chrome)

        # 2. Fuzzy match "chorme" should trigger confirmation tier (0.60 to 0.85 score)
        intent = self.intent_engine.classify("open chorme")
        context = {"entity_graph": self.graph, "matcher": self.matcher}
        res = self.chain.resolve(intent, context)

        self.assertEqual(res["action"], "confirm")
        self.assertEqual(res["entity"].name, "Google Chrome")
        self.assertEqual(res["source"], "alias_match_confirm")

    def test_web_search_resolution(self):
        intent = self.intent_engine.classify("search Python tutorials")
        context = {"entity_graph": self.graph, "matcher": self.matcher}
        res = self.chain.resolve(intent, context)

        self.assertEqual(res["action"], "execute")
        self.assertEqual(res["entity"].category, "search")
        self.assertEqual(res["entity"].metadata.get("query"), "Python tutorials")

if __name__ == "__main__":
    unittest.main()
