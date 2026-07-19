"""
Unit tests for HiddenItemsService and integrated vault commands.
"""

import os
import sys
import unittest
import sqlite3
import shutil
from datetime import datetime, timedelta

# Ensure codebase root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.core import CoreSystem
from ultron.core.event_bus import event_bus
from ultron.core.service_manager import service_manager
from ultron.services.hidden_items_service import HiddenItemsService, get_fixed_drives
from ultron.skills.registry import SkillRegistry
from ultron.skills.command_dispatcher import CommandDispatcher

class TestHiddenItems(unittest.TestCase):
    def setUp(self):
        self.db_name = f"test_hidden_items_{self._testMethodName}.db"
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass
                
        # Set up folders for testing
        self.test_dir = os.path.abspath(f"./test_vault_dir_{self._testMethodName}")
        self.protected_dir = os.path.abspath("C:/Windows/System32")
        
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
            
        # Initialize Core and Service
        self.core = CoreSystem()
        self.service = HiddenItemsService(db_path=self.db_name)
        self.service.initialize()
        self.service.start()
        service_manager.register_service("HiddenItemsService", self.service)
        
        # Dispatcher Setup
        self.memory = self.core.get_module("memory_manager")
        if not self.memory:
            from ultron.memory import MemoryManager
            self.memory = MemoryManager(self.db_name)
            
        self.skills = SkillRegistry(self.core, self.memory)
        self.skills.register_skill("CommandDispatcher", CommandDispatcher)
        self.core.register_module("skills_registry", self.skills)
        self.dispatcher = self.skills.get_skill("CommandDispatcher")
        
        # Bookkeeping events
        self.events_received = []
        event_bus.subscribe("HiddenItemAdded", self._collect_event)
        event_bus.subscribe("HiddenItemRestored", self._collect_event)
        event_bus.subscribe("HiddenItemMissing", self._collect_event)

    def tearDown(self):
        self.service.stop()
        from ultron.core.service_manager import service_manager
        if "HiddenItemsService" in service_manager._services:
            del service_manager._services["HiddenItemsService"]
        
        # Unsubscribe event handlers to prevent leak
        event_bus.unsubscribe("HiddenItemAdded", self._collect_event)
        event_bus.unsubscribe("HiddenItemRestored", self._collect_event)
        event_bus.unsubscribe("HiddenItemMissing", self._collect_event)
        
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass
        if os.path.exists(self.test_dir):
            try:
                self.service._set_hidden_attribute(self.test_dir, False)
                shutil.rmtree(self.test_dir)
            except Exception:
                pass

    def _collect_event(self, event):
        self.events_received.append(event)

    def test_hiding_and_restoring(self):
        """Test standard hiding, database logging, attributes setting, and restoring."""
        # 1. Hide item
        name = self.service.hide_item(self.test_dir, notes="Important test directory")
        self.assertEqual(name, os.path.basename(self.test_dir))
        
        # Check SQLite db record
        item = self.service.get_item_by_path(self.test_dir)
        self.assertIsNotNone(item)
        self.assertEqual(item["name"], os.path.basename(self.test_dir))
        self.assertEqual(item["status"], "hidden")
        self.assertEqual(item["type"], "folder")
        self.assertEqual(item["notes"], "Important test directory")
        
        # Verify event was published
        self.assertTrue(any(e.event_type == "HiddenItemAdded" for e in self.events_received))
        
        # 2. Check is_hidden helper
        self.assertTrue(self.service.is_hidden(self.test_dir))
        
        # 3. Unhide/Restore item
        restored_name = self.service.unhide_item(self.test_dir)
        self.assertEqual(restored_name, os.path.basename(self.test_dir))
        
        # Check SQLite updated record
        item_updated = self.service.get_item_by_path(self.test_dir)
        self.assertEqual(item_updated["status"], "restored")
        
        # Verify event was published
        self.assertTrue(any(e.event_type == "HiddenItemRestored" for e in self.events_received))

    def test_protected_safety_exclusions(self):
        """Test safety exclusions rejecting system folders or drive roots."""
        # Test folder in C:\Windows
        with self.assertRaises(PermissionError):
            self.service.hide_item("C:\\Windows\\System32")
            
        # Test C:\ drive root
        system_drive = os.environ.get("SystemDrive", "C:") + "\\"
        with self.assertRaises(PermissionError):
            self.service.hide_item(system_drive)

    def test_list_and_find_items(self):
        """Test listing, finding, and missing items status checks."""
        # Hide item
        self.service.hide_item(self.test_dir)
        
        # Find item fuzzy lookup
        matches = self.service.find_item("test_vault")
        self.assertTrue(len(matches) > 0)
        self.assertEqual(matches[0]["name"], os.path.basename(self.test_dir))
        
        # List items
        items = self.service.list_hidden_items()
        self.assertTrue(len(items) > 0)
        self.assertEqual(items[0]["status"], "hidden")
        
        # Test missing check (delete on disk and list again)
        shutil.rmtree(self.test_dir)
        items_after = self.service.list_hidden_items()
        self.assertEqual(items_after[0]["status"], "missing")
        
        # Verify event was published
        self.assertTrue(any(e.event_type == "HiddenItemMissing" for e in self.events_received))

    def test_restore_by_relative_dates(self):
        """Test bulk date-based unhide routines."""
        # Hide item
        self.service.hide_item(self.test_dir)
        
        # Verify today restore works
        restored = self.service.restore_by_date("today")
        self.assertEqual(restored, [os.path.basename(self.test_dir)])
        
        # Verify status is restored in db
        item = self.service.get_item_by_path(self.test_dir)
        self.assertEqual(item["status"], "restored")

    def test_command_dispatcher_integration(self):
        """Test command dispatcher routing and choices generation."""
        # Test Hide command execution
        res = self.dispatcher.execute({"command": f"hide folder {self.test_dir}"})
        self.assertTrue(res["success"])
        self.assertIn(f"{os.path.basename(self.test_dir)} has been hidden", res["response"])
        
        # Test Show / Restore command execution
        res_restore = self.dispatcher.execute({"command": f"restore {self.test_dir}"})
        self.assertTrue(res_restore["success"])
        self.assertIn(f"{os.path.basename(self.test_dir)} is visible again", res_restore["response"])

if __name__ == "__main__":
    unittest.main()
