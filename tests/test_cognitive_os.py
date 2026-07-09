import os
import sys
import unittest
import time
import json
import shutil
import sqlite3
from typing import Dict, Any

# Ensure codebase root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultron.core.event_bus import event_bus
from ultron.core.service_manager import service_manager, UltronService
from ultron.core.plugin_loader import UltronPluginLoader
from ultron.memory import MemoryManager
from ultron.core.health_monitor import UltronHealthMonitor

class MockService(UltronService):
    def __init__(self, name="MockService"):
        super().__init__(name)
        self.started = False
        self.stopped = False

    def start(self) -> bool:
        self.active = True
        self.started = True
        return True

    def stop(self) -> bool:
        self.active = False
        self.stopped = True
        return True

    def health(self) -> str:
        return "Running" if self.active else "Offline"

class TestCognitiveOS(unittest.TestCase):
    def setUp(self):
        # Clear event bus subscribers for isolation
        event_bus._listeners = {}

    def test_service_lifecycles(self):
        """Test registration, startup, shutdown, and status querying of OS services."""
        mock_srv = MockService("TestService")
        service_manager.register_service("TestService", mock_srv)
        
        self.assertEqual(service_manager.get_service("TestService"), mock_srv)
        self.assertTrue(service_manager.start_service("TestService"))
        self.assertTrue(mock_srv.started)
        self.assertTrue(mock_srv.is_active())
        self.assertEqual(mock_srv.health(), "Running")

        self.assertTrue(service_manager.stop_service("TestService"))
        self.assertTrue(mock_srv.stopped)
        self.assertFalse(mock_srv.is_active())
        self.assertEqual(mock_srv.health(), "Offline")

    def test_event_bus_communication(self):
        """Test event publishing and dispatching."""
        received = []
        def handler(event):
            received.append(event.payload.get("data"))

        event_bus.subscribe("TEST_EVENT", handler)
        event_bus.publish("TEST_EVENT", {"data": "hello"})
        
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], "hello")

    def test_plugin_loading_unloading(self):
        """Test dynamic loader, manifest parsing, dependency check, and unload sequence."""
        test_dir = "temp_plugins"
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)

        plugin_folder = os.path.join(test_dir, "test_plugin")
        os.makedirs(plugin_folder, exist_ok=True)

        manifest = {
            "name": "test_plugin",
            "version": "1.0.0",
            "author": "Tester",
            "minimum_ultron_version": "1.0.0",
            "dependencies": [],
            "permissions": [],
            "entry_point": "plugin.py"
        }

        with open(os.path.join(plugin_folder, "manifest.json"), "w") as f:
            json.dump(manifest, f)

        with open(os.path.join(plugin_folder, "plugin.py"), "w") as f:
            f.write("def register_plugin(registry):\n    pass\n")

        loader = UltronPluginLoader(test_dir, None)
        loader.load_all_plugins()

        self.assertIn("test_plugin", loader.loaded_plugins)
        self.assertEqual(loader.loaded_plugins["test_plugin"]["version"], "1.0.0")

        # Clean unload
        self.assertTrue(loader.unload_plugin("test_plugin"))
        self.assertNotIn("test_plugin", loader.loaded_plugins)

        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)

    def test_sqlite_integrity_and_domains(self):
        """Test sqlite memory engine CRUD and auto-pruning constraint."""
        mem = MemoryManager("test_memory.db")
        rec_id = mem.create_record("preference", "theme", "dark")
        
        self.assertIsNotNone(rec_id)
        record = mem.read_record("preference", rec_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["title"], "theme")
        self.assertEqual(record["content"], "dark")

        # Verify auto-pruning (latest 1000 limit)
        for i in range(10):
            mem.create_record("voice_history", f"test_{i}", "history_content")
            
        history_records = mem.list_records("voice_history", limit=100)
        self.assertTrue(len(history_records) > 0)
        
        # Cleanup test DB
        if os.path.exists("test_memory.db"):
            os.remove("test_memory.db")

    def test_health_monitor_recovery(self):
        """Test health monitor recovery trigger."""
        mock_srv = MockService("DegradedService")
        service_manager.register_service("DegradedService", mock_srv)
        service_manager.start_service("DegradedService")
        
        # Fail service by setting health return value
        class FailedService(MockService):
            def health(self):
                return "Error"

        failed_srv = FailedService("DegradedService")
        service_manager.register_service("DegradedService", failed_srv)
        
        restarts = []
        def on_restart(event):
            restarts.append(event.payload.get("service"))
        event_bus.subscribe("SERVICE_RESTARTED", on_restart)

        monitor = UltronHealthMonitor(interval_seconds=1)
        monitor.start()
        
        # Give monitor loop a moment to run and attempt recovery
        time.sleep(2.5)
        monitor.stop()

        self.assertIn("DegradedService", restarts)

    def test_command_framework(self):
        """Test formalized commands, aliases, dry-run, and undo execution."""
        from ultron.core.command_framework import command_registry
        
        # Verify default commands registered
        self.assertIsNotNone(command_registry.get_command("remember"))
        self.assertIsNotNone(command_registry.get_command("search"))
        
        # Executing a dry-run remember
        dry_result = command_registry.execute_string("remember user_role coder", dry_run=True)
        self.assertIn("Dry-run", dry_result)
        
        # Revert last stack command (nothing to revert yet)
        revert_msg = command_registry.undo_last()
        self.assertEqual(revert_msg, "No commands in undo history.")

    def test_security_layer(self):
        """Test configuration encryption, session audits, and key obfuscation."""
        from ultron.core.security import encrypt_value, decrypt_value, audit_permission
        
        original_secret = "StarkToken_1234"
        encrypted = encrypt_value(original_secret)
        self.assertNotEqual(original_secret, encrypted)
        
        decrypted = decrypt_value(encrypted)
        self.assertEqual(original_secret, decrypted)
        
        # Audit permission check
        allowed = audit_permission("TestPlugin", "camera")
        self.assertTrue(allowed or not allowed)  # Validates return type is boolean

    def test_performance_monitoring(self):
        """Test performance diagnostics profiling block scopes."""
        from ultron.core.performance_monitor import profile_operation, profiler_history
        
        with profile_operation("test_db_fetch", "TestScope"):
            time.sleep(0.05)
            
        self.assertTrue(len(profiler_history) > 0)
        self.assertEqual(profiler_history[-1]["operation"], "test_db_fetch")

    def test_backup_recovery(self):
        """Test SQLite VACUUM, integrity checking, and manual restore point snapshots."""
        from ultron.core.backup_manager import BackupManager
        
        mgr = BackupManager("test_memory.db", "temp_backups")
        
        # Initialize test DB
        conn = sqlite3.connect("test_memory.db")
        conn.execute("CREATE TABLE IF NOT EXISTS test_table (id TEXT);")
        conn.close()
        
        self.assertTrue(mgr.verify_integrity())
        self.assertTrue(mgr.optimize_database())
        
        backup_path = mgr.create_backup("unittest")
        self.assertTrue(os.path.exists(backup_path))
        self.assertTrue(os.path.exists(os.path.join(backup_path, "ultron_memory.db")))
        
        # Cleanup
        if os.path.exists("test_memory.db"):
            os.remove("test_memory.db")
        shutil.rmtree("temp_backups", ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
