"""
Unit and benchmark tests for Phase 2.5 Cognitive Operating System.
"""

import os
import sys
import time
import random
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.core.cognitive_os.entity_graph import EntityKnowledgeGraph, UltronEntity
from ultron.core.cognitive_os.base_matcher import DifflibMatcher
from ultron.core.cognitive_os.intent_engine import IntentEngine
from ultron.core.cognitive_os.alias_generator import generate_aliases
from ultron.core.cognitive_os.resolver_chain import (
    ExactAliasResolver, FuzzyAliasResolver, LearningMemoryResolver,
    DynamicSearchResolver, WebsiteResolver, WebSearchResolver, FailureResolver
)
from ultron.core.cognitive_os.learning_memory import LearningMemory
from ultron.memory import MemoryManager

class TestCognitiveOSPhase2(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_phase2_cascading.db"
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass
                
        self.memory = MemoryManager(self.db_name)
        self.graph = EntityKnowledgeGraph()
        self.matcher = DifflibMatcher()
        self.intent_engine = IntentEngine()
        self.learning = LearningMemory(self.memory)

        from ultron.core.cognitive_os.app_indexer import WindowsAppIndexer
        self.indexer = WindowsAppIndexer(self.memory)

        # Setup cascading resolver chain
        self.chain = LearningMemoryResolver(self.learning)
        r_exact = ExactAliasResolver()
        r_fuzzy = FuzzyAliasResolver(self.matcher)
        r_search_win = DynamicSearchResolver(self.indexer)
        r_web = WebsiteResolver()
        r_search = WebSearchResolver()
        r_fail = FailureResolver()
        
        self.chain.set_next(r_exact).set_next(r_fuzzy).set_next(r_search_win).set_next(r_web).set_next(r_search).set_next(r_fail)

        # Prepopulate Entity Graph with test entities and their generated aliases
        test_apps = [
            "Google Chrome", "Microsoft Edge", "Visual Studio Code", 
            "Spider-Man Remastered", "Grand Theft Auto V", "Minecraft"
        ]
        for app in test_apps:
            aliases = generate_aliases(app)
            self.graph.add_entity(UltronEntity(
                name=app,
                category="application",
                aliases=aliases
            ))

    def tearDown(self):
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass

    def test_cascading_resolutions(self):
        commands = [
            "open chrome", "open chorme", "open chrom", 
            "open spider man", "open spiderman", 
            "open gta", "open vscode", "open code"
        ]
        
        context = {"entity_graph": self.graph, "matcher": self.matcher}
        
        for cmd in commands:
            intent = self.intent_engine.classify(cmd)
            res = self.chain.resolve(intent, context)
            
            # Assert that each resolves successfully (either executing immediately or confirming)
            self.assertTrue(res["success"])
            self.assertIn(res["action"], ["execute", "confirm"])
            self.assertNotEqual(res["action"], "fail")

    def test_alias_weights(self):
        aliases = generate_aliases("Google Chrome")
        self.assertEqual(aliases.get("chrome"), 1.0)
        self.assertEqual(aliases.get("google chrome"), 1.0)
        self.assertEqual(aliases.get("chorme"), 0.9)
        self.assertEqual(aliases.get("google"), 0.2)

    def test_performance_benchmark(self):
        """Benchmark 1000 lookups to verify < 2ms average retrieval latency target."""
        for i in range(50):
            app_name = f"Application {i}"
            aliases = {f"app {i}": 1.0, f"application {i}": 1.0, f"shortcut {i}": 0.8}
            self.graph.add_entity(UltronEntity(
                name=app_name,
                category="application",
                aliases=aliases
            ))

        queries = []
        for _ in range(1000):
            idx = random.randint(0, 49)
            queries.append(f"app {idx}")

        times = []
        for q in queries:
            start = time.perf_counter()
            results = self.graph.search(q, self.matcher, cutoff=0.5)
            dur = (time.perf_counter() - start) * 1000 # in ms
            times.append(dur)
            self.assertTrue(len(results) > 0)

        avg_time = sum(times) / len(times)
        self.assertLess(avg_time, 2.0)

if __name__ == "__main__":
    unittest.main()
