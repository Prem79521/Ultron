"""
ULTRON Backup and Recovery Manager — Performs SQLite backups, schema verification, and compression.
"""

import os
import shutil
import time
import sqlite3
import logging
from typing import List

class BackupManager:
    """Orchestrates database vacuuming, integrity checks, and manual/automated restore points."""
    def __init__(self, db_path: str = "ultron_memory.db", backup_dir: str = "backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.logger = logging.getLogger("ultron-agent")
        if not os.path.exists(self.backup_dir):
            try:
                os.makedirs(self.backup_dir)
            except Exception:
                pass

    def verify_integrity(self) -> bool:
        """Runs SQLite integrity verification queries."""
        if not os.path.exists(self.db_path):
            return False
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            conn.close()
            return result[0] == "ok" if result else False
        except Exception as e:
            self.logger.error(f"Database integrity check failed: {e}")
            return False

    def optimize_database(self) -> bool:
        """Executes database VACUUM and ANALYZE optimization steps."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM;")
            conn.execute("ANALYZE;")
            conn.close()
            self.logger.info("SQLite database optimization completed (VACUUM & ANALYZE).")
            return True
        except Exception as e:
            self.logger.error(f"Failed to optimize database: {e}")
            return False

    def create_backup(self, label: str = "auto") -> str:
        """Creates a snapshot copy of the database, configuration files, and active settings."""
        if not os.path.exists(self.db_path):
            return ""
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_folder = os.path.join(self.backup_dir, f"backup_{label}_{timestamp}")
        
        try:
            os.makedirs(backup_folder, exist_ok=True)
            # Copy database
            shutil.copy(self.db_path, os.path.join(backup_folder, "ultron_memory.db"))
            # Copy config dir if exists
            if os.path.exists("config"):
                shutil.copytree("config", os.path.join(backup_folder, "config"), dirs_exist_ok=True)
                
            self.logger.info(f"Database and settings backup successfully created: {backup_folder}")
            return backup_folder
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return ""

    def restore_from_backup(self, backup_folder: str) -> bool:
        """Restores database and configuration folders from a specified backup path."""
        db_backup = os.path.join(backup_folder, "ultron_memory.db")
        if not os.path.exists(db_backup):
            self.logger.error(f"Backup file missing: {db_backup}")
            return False
            
        try:
            # Copy database back
            shutil.copy(db_backup, self.db_path)
            # Copy config back if present
            config_backup = os.path.join(backup_folder, "config")
            if os.path.exists(config_backup):
                shutil.copytree(config_backup, "config", dirs_exist_ok=True)
                
            self.logger.info(f"Successfully restored system settings from backup: {backup_folder}")
            return True
        except Exception as e:
            self.logger.error(f"Restoration failed: {e}")
            return False

    def list_backups(self) -> List[str]:
        """Lists folders available inside backup directory."""
        if not os.path.exists(self.backup_dir):
            return []
        try:
            return [os.path.join(self.backup_dir, d) for d in os.listdir(self.backup_dir) 
                    if os.path.isdir(os.path.join(self.backup_dir, d))]
        except Exception:
            return []
