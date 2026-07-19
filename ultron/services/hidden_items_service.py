"""
ULTRON Hidden Items Manager Service — Secure, native file-hiding vault.
"""

import os
import sys
import time
import uuid
import ctypes
import sqlite3
import logging
import threading
import difflib
from datetime import datetime
from typing import List, Dict, Any, Optional

from ultron.core.service_manager import UltronService
from ultron.core.event_bus import event_bus

def get_fixed_drives() -> List[str]:
    """Lightweight native logical drives lookup on Windows."""
    drives = []
    if sys.platform != "win32":
        return ["/"] # Non-Windows fallback
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if bitmask & 1:
                drive_path = f"{letter}:\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                if drive_type == 3:  # DRIVE_FIXED
                    drives.append(drive_path)
            bitmask >>= 1
    except Exception:
        drives = ["C:\\"]
    return drives

def find_candidates(query: str, max_depth: int = 3, timeout: float = 2.0) -> List[str]:
    """Dynamic recursive crawler that maps possible file/folder matches with safety constraints."""
    query_clean = query.lower().strip()
    if not query_clean:
        return []
        
    candidates = []
    user_profile = os.environ.get("USERPROFILE", "C:\\Users\\default")
    
    # 1. Gather search roots
    roots = []
    for folder in ["Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music"]:
        path = os.path.join(user_profile, folder)
        if os.path.exists(path):
            roots.append(path)
            
    public_desktop = "C:\\Users\\Public\\Desktop"
    if os.path.exists(public_desktop):
        roots.append(public_desktop)
        
    pf = os.environ.get("ProgramFiles", "C:\\Program Files")
    if os.path.exists(pf):
        roots.append(pf)
    pf86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    if os.path.exists(pf86):
        roots.append(pf86)
        
    users_dir = "C:\\Users"
    if os.path.exists(users_dir):
        roots.append(users_dir)
        
    for drive in get_fixed_drives():
        if drive not in roots:
            roots.append(drive)
            
    # 2. Check exact matches directly in search roots first (very fast)
    exact_matches = []
    for root in roots:
        try:
            items = os.listdir(root)
            for item in items:
                if item.lower() == query_clean:
                    exact_matches.append(os.path.join(root, item))
        except Exception:
            continue
            
    if exact_matches:
        return list(set(exact_matches))
        
    # 3. Perform recursive lookup with strict time limits to prevent freezes
    start_time = time.time()
    for root in roots:
        if time.time() - start_time > timeout:
            break
            
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                if time.time() - start_time > timeout:
                    break
                    
                rel_depth = dirpath[len(root):].count(os.sep)
                if rel_depth > max_depth:
                    dirnames.clear()
                    continue
                    
                # Walk through sub-items
                for name in dirnames + filenames:
                    name_lower = name.lower()
                    
                    score = 0.0
                    if query_clean == name_lower:
                        score = 1.0
                    elif query_clean in name_lower:
                        score = 0.85 if name_lower.startswith(query_clean) else 0.8
                    else:
                        score = difflib.SequenceMatcher(None, query_clean, name_lower).ratio()
                        
                    if score >= 0.75:
                        full_path = os.path.join(dirpath, name)
                        candidates.append((full_path, score))
        except Exception:
            continue
            
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [c[0] for c in candidates]

class HiddenItemsService(UltronService):
    """Authoritative Cognitive OS service responsible for secure file/folder vault storage."""
    
    def __init__(self, db_path: Optional[str] = None):
        super().__init__("HiddenItemsService")
        # Fallback path resolve
        if not db_path:
            from ultron.core.config_loader import config_loader
            db_path = config_loader.get("memory", "db_path", "ultron_memory.db")
        self.db_path = db_path
        self.logger = logging.getLogger("ultron-agent")

    def initialize(self) -> bool:
        """Create database tables and secure local properties."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hidden_items (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    original_path TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL,
                    hidden_timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT
                )
            """)
            conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to initialize hidden_items table: {e}")
            self.record_failure(str(e))
            return False
            
        self._lifecycle_stage = "initialized"
        return True

    def start(self) -> bool:
        self.active = True
        self._start_time = time.time()
        self._lifecycle_stage = "started"
        self.ready()
        return True

    def stop(self) -> bool:
        self.active = False
        self._lifecycle_stage = "stopped"
        return True

    def _set_hidden_attribute(self, path: str, hide: bool = True) -> bool:
        """Sets or clears standard Win32 file attribute flags via kernel32 ctypes."""
        if sys.platform != "win32":
            self.logger.warning(f"OS is {sys.platform}. Simulating attribute action for path '{path}'.")
            return True
            
        FILE_ATTRIBUTE_HIDDEN = 0x02
        FILE_ATTRIBUTE_NORMAL = 0x80
        
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
            if attrs == -1:
                return False
                
            if hide:
                new_attrs = attrs | FILE_ATTRIBUTE_HIDDEN
            else:
                new_attrs = attrs & ~FILE_ATTRIBUTE_HIDDEN
                if new_attrs == 0:
                    new_attrs = FILE_ATTRIBUTE_NORMAL
                    
            ret = ctypes.windll.kernel32.SetFileAttributesW(path, new_attrs)
            return bool(ret)
        except Exception as e:
            self.logger.error(f"Win32 API attribute call failure: {e}")
            return False

    def _is_protected(self, path: str) -> bool:
        """Verifies if path contains components that are critical to OS operations."""
        from ultron.core.config_loader import config_loader
        dev_mode = config_loader.get("general", "developer_mode", False)
        if dev_mode:
            return False
            
        norm = os.path.abspath(path).lower()
        system_drive = os.environ.get("SystemDrive", "C:").lower()
        
        # Protected folder basenames/components
        protected = ["windows", "program files", "program files (x86)", "system32", "boot", "recovery", "drivers"]
        
        parts = norm.replace("\\", "/").split("/")
        for p in parts:
            if p in protected:
                return True
                
        # Protect raw drive roots
        if norm.rstrip("\\") == system_drive or len(norm.rstrip("\\")) <= 3:
            return True
            
        return False

    def get_item_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """Retrieves matching vault item record by original filepath."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hidden_items WHERE original_path = ?", (path,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        finally:
            conn.close()
        return None

    def hide_item(self, path: str, notes: Optional[str] = None) -> str:
        """Hides file/folder on disk, updates local table, and publishes event."""
        path = os.path.abspath(path)
        name = os.path.basename(path)
        
        if self._is_protected(path):
            raise PermissionError("That location is protected.")
            
        if not os.path.exists(path):
            raise FileNotFoundError("That location does not exist.")
            
        existing = self.get_item_by_path(path)
        if existing and existing["status"] == "hidden":
            self._set_hidden_attribute(path, True)
            raise ValueError("Already hidden.")
            
        success = self._set_hidden_attribute(path, True)
        if not success:
            raise PermissionError("Access denied or permission error setting hidden attribute.")
            
        item_type = "folder" if os.path.isdir(path) else "file"
        timestamp = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            if existing:
                cursor.execute("""
                    UPDATE hidden_items
                    SET status = 'hidden', hidden_timestamp = ?, notes = ?
                    WHERE original_path = ?
                """, (timestamp, notes, path))
                item_id = existing["id"]
            else:
                item_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO hidden_items (id, name, original_path, type, hidden_timestamp, status, notes)
                    VALUES (?, ?, ?, ?, ?, 'hidden', ?)
                """, (item_id, name, path, item_type, timestamp, notes))
            conn.commit()
        finally:
            conn.close()
            
        self.logger.info(f"Hidden item added: {path}")
        event_bus.publish("HiddenItemAdded", {
            "id": item_id,
            "name": name,
            "original_path": path,
            "type": item_type,
            "hidden_timestamp": timestamp,
            "status": "hidden",
            "notes": notes
        })
        return name

    def unhide_item(self, path: str) -> str:
        """Restores file/folder visibility and updates status in vault DB."""
        path = os.path.abspath(path)
        existing = self.get_item_by_path(path)
        
        if not existing:
            # Try searching by name
            matches = self.find_item(path)
            if matches:
                existing = matches[0]
                path = existing["original_path"]
            else:
                raise ValueError("Item not found in database.")
                
        if not os.path.exists(path):
            self._update_status(existing["id"], "missing")
            event_bus.publish("HiddenItemMissing", {
                "id": existing["id"],
                "name": existing["name"],
                "original_path": path
            })
            raise FileNotFoundError("That folder no longer exists.")
            
        success = self._set_hidden_attribute(path, False)
        if not success:
            raise PermissionError("Access denied or permission error removing hidden attribute.")
            
        self._update_status(existing["id"], "restored")
        self.logger.info(f"Hidden item restored: {path}")
        
        event_bus.publish("HiddenItemRestored", {
            "id": existing["id"],
            "name": existing["name"],
            "original_path": path,
            "status": "restored"
        })
        return existing["name"]

    def list_hidden_items(self) -> List[Dict[str, Any]]:
        """Queries the vault table, checking actual item existences synchronously."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        items = []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hidden_items")
            rows = cursor.fetchall()
            for row in rows:
                item = dict(row)
                if item["status"] == "hidden" and not os.path.exists(item["original_path"]):
                    item["status"] = "missing"
                    self._update_status(item["id"], "missing")
                    event_bus.publish("HiddenItemMissing", {
                        "id": item["id"],
                        "name": item["name"],
                        "original_path": item["original_path"]
                    })
                items.append(item)
        finally:
            conn.close()
        return items

    def find_item(self, name: str) -> List[Dict[str, Any]]:
        """Queries DB table for items whose name fuzzy matches name."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        name_clean = name.lower().strip()
        matched = []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hidden_items")
            rows = cursor.fetchall()
            for row in rows:
                item = dict(row)
                row_name = item["name"].lower()
                
                score = 0.0
                if name_clean == row_name:
                    score = 1.0
                elif name_clean in row_name:
                    score = 0.85 if row_name.startswith(name_clean) else 0.8
                else:
                    score = difflib.SequenceMatcher(None, name_clean, row_name).ratio()
                    
                if score >= 0.75:
                    item["match_score"] = score
                    matched.append(item)
        finally:
            conn.close()
            
        matched.sort(key=lambda x: x.get("match_score", 0.0), reverse=True)
        return matched

    def open_hidden_item(self, name: str):
        """Temporarily unhides the target file/folder and launches Explorer."""
        matches = self.find_item(name)
        hidden_matches = [m for m in matches if m["status"] == "hidden"]
        if not hidden_matches:
            raise ValueError("Item not found or not currently hidden.")
            
        item = hidden_matches[0]
        path = item["original_path"]
        
        if not os.path.exists(path):
            self._update_status(item["id"], "missing")
            event_bus.publish("HiddenItemMissing", {
                "id": item["id"],
                "name": item["name"],
                "original_path": path
            })
            raise FileNotFoundError("That folder no longer exists.")
            
        self._set_hidden_attribute(path, False)
        
        import subprocess
        try:
            if os.path.isdir(path):
                subprocess.Popen(f'explorer "{path}"', shell=True)
            else:
                subprocess.Popen(f'explorer /select,"{path}"', shell=True)
        except Exception as e:
            self.logger.error(f"Failed to open Explorer for hidden item: {e}")
            
        self.logger.info(f"Hidden item opened: {path}")
        event_bus.publish("HiddenItemOpened", {
            "id": item["id"],
            "name": item["name"],
            "original_path": path
        })
        
        # Start securing background thread
        def re_secure():
            time.sleep(10.0)
            if os.path.exists(path):
                latest = self.get_item_by_path(path)
                if latest and latest["status"] == "hidden":
                    self._set_hidden_attribute(path, True)
                    self.logger.info(f"Hidden item re-secured: {path}")
                    
        threading.Thread(target=re_secure, daemon=True).start()

    def is_hidden(self, path: str) -> bool:
        item = self.get_item_by_path(path)
        return item is not None and item["status"] == "hidden"

    def restore_by_date(self, day: str) -> List[str]:
        """Restores multiple hidden items matching relative dates (today, yesterday, or everything)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        restored_names = []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hidden_items WHERE status = 'hidden'")
            rows = cursor.fetchall()
            
            now = datetime.utcnow()
            for row in rows:
                item = dict(row)
                ts_str = item["hidden_timestamp"]
                try:
                    ts = datetime.fromisoformat(ts_str)
                    delta_hours = (now - ts).total_seconds() / 3600.0
                except Exception:
                    delta_hours = 999.0
                    
                match = False
                if day == "today" and delta_hours <= 24.0:
                    match = True
                elif day == "yesterday" and 24.0 < delta_hours <= 48.0:
                    match = True
                elif day == "everything":
                    match = True
                    
                if match:
                    path = item["original_path"]
                    if os.path.exists(path):
                        self._set_hidden_attribute(path, False)
                        cursor.execute("UPDATE hidden_items SET status = 'restored' WHERE id = ?", (item["id"],))
                        restored_names.append(item["name"])
                        event_bus.publish("HiddenItemRestored", {
                            "id": item["id"],
                            "name": item["name"],
                            "original_path": path,
                            "status": "restored"
                        })
                    else:
                        cursor.execute("UPDATE hidden_items SET status = 'missing' WHERE id = ?", (item["id"],))
                        event_bus.publish("HiddenItemMissing", {
                            "id": item["id"],
                            "name": item["name"],
                            "original_path": path
                        })
            conn.commit()
        finally:
            conn.close()
            
        if restored_names:
            self.logger.info(f"Restored {len(restored_names)} items hidden {day}")
        return restored_names

    def delete_record(self, item_id: str) -> bool:
        """Deletes item record from SQLite database history."""
        conn = sqlite3.connect(self.db_path)
        success = False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM hidden_items WHERE id = ?", (item_id,))
            conn.commit()
            success = cursor.rowcount > 0
        finally:
            conn.close()
        if success:
            event_bus.publish("HiddenItemDeleted", {"id": item_id})
        return success

    def _update_status(self, item_id: str, status: str):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE hidden_items SET status = ? WHERE id = ?", (status, item_id))
            conn.commit()
        finally:
            conn.close()
