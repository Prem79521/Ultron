"""
Unit tests for the application indexer and persistent cache lifecycle.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.memory import MemoryManager
from ultron.core.cognitive_os.app_indexer import WindowsAppIndexer
from ultron.core.cognitive_os.entity_graph import EntityKnowledgeGraph

class TestAppIndexer(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_app_cache.db"
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass
        self.mgr = MemoryManager(self.db_path)
        self.indexer = WindowsAppIndexer(self.mgr, cache_expiry_seconds=2)
        self.graph = EntityKnowledgeGraph()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_cache_rebuild_and_load(self):
        # Empty cache should require rebuild
        self.assertTrue(self.indexer.should_rebuild_cache())

        # Rebuild cache (creates empty or mock scanning records)
        self.indexer.rebuild_cache()
        self.assertFalse(self.indexer.should_rebuild_cache())

        # Load cache into graph
        self._mock_cache_records()
        self.indexer.load_cache(self.graph)
        
        # Verify mocked entity resolved
        entity = self.graph.get_entity("Mock Test App")
        self.assertIsNotNone(entity)
        self.assertEqual(entity.category, "application")

    def _mock_cache_records(self):
        # Directly insert one mock record to bypass dry systems scans
        import json
        from datetime import datetime
        app_data = {
            "name": "Mock Test App",
            "executable": "C:\\Mock\\test.exe",
            "publisher": "MockCorp",
            "install_path": "C:\\Mock",
            "aliases": {"mock": 1.0, "test app": 0.8},
            "category": "application",
            "indexed_at": datetime.utcnow().isoformat()
        }
        self.mgr.create_record(
            "app_cache",
            title="mock test app",
            content=json.dumps(app_data),
            tags=["application", "cached_app"]
        )

if __name__ == "__main__":
    unittest.main()
