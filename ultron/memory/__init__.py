"""
ULTRON Memory Engine (UME) — Central Memory Manager.
"""

import os
import uuid
from typing import Dict, Any, List, Optional
from ultron.memory.store import MemoryRecord, SqliteMemoryStore
from ultron.working_memory import WorkingMemoryStore

class LifecyclePolicy:
    """Configurable lifecycle policies for memory types."""
    def __init__(self, archive_after_inactivity: bool = False, persistent: bool = True):
        self.archive_after_inactivity = archive_after_inactivity
        self.persistent = persistent

class MemoryManager:
    """
    Centralized controller for UME.
    The Cognitive Core only interacts with memory through this interface.
    """
    def __init__(self, db_path: str = "ultron_memory.db"):
        self.db_path = db_path
        
        # Instantiate separate stores with separate tables
        self._stores = {
            "conversation": SqliteMemoryStore(db_path, "conversation_memory", "conversation"),
            "project": SqliteMemoryStore(db_path, "project_memory", "project"),
            "preference": SqliteMemoryStore(db_path, "preference_memory", "preference"),
            "knowledge": SqliteMemoryStore(db_path, "knowledge_memory", "knowledge"),
            "permission": SqliteMemoryStore(db_path, "permission_memory", "permission"),
            "log": SqliteMemoryStore(db_path, "log_memory", "log"),
            "session": SqliteMemoryStore(db_path, "session_memory", "session"),
            "voice_settings": SqliteMemoryStore(db_path, "voice_settings_memory", "voice_settings"),
            "provider_settings": SqliteMemoryStore(db_path, "provider_settings_memory", "provider_settings"),
            "plugin_settings": SqliteMemoryStore(db_path, "plugin_settings_memory", "plugin_settings"),
            "notification": SqliteMemoryStore(db_path, "notification_memory", "notification"),
            "voice_history": SqliteMemoryStore(db_path, "voice_history_memory", "voice_history"),
            "wake_history": SqliteMemoryStore(db_path, "wake_history_memory", "wake_history"),
            "diagnostics": SqliteMemoryStore(db_path, "diagnostics_memory", "diagnostics"),
            "app_cache": SqliteMemoryStore(db_path, "app_cache_memory", "app_cache"),
            "learning": SqliteMemoryStore(db_path, "learning_memory", "learning"),
            "working": WorkingMemoryStore()
        }
        
        # Define lifecycle policies
        self.policies = {
            "conversation": LifecyclePolicy(archive_after_inactivity=True, persistent=True),
            "project": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "preference": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "knowledge": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "permission": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "log": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "session": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "voice_settings": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "provider_settings": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "plugin_settings": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "notification": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "voice_history": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "wake_history": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "diagnostics": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "app_cache": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "learning": LifecyclePolicy(archive_after_inactivity=False, persistent=True),
            "working": LifecyclePolicy(archive_after_inactivity=False, persistent=False)
        }

    def _get_store(self, memory_type: str):
        store = self._stores.get(memory_type)
        if not store:
            raise ValueError(f"Invalid memory type: {memory_type}")
        return store

    # -----------------------------------------------------------------------
    # Public Unified CRUD Interfaces
    # -----------------------------------------------------------------------
    
    def create_record(
        self,
        memory_type: str,
        title: str,
        content: str,
        tags: List[str] = None,
        importance_score: int = 5,
        related_project: str = None,
        status: str = "active"
    ) -> str:
        store = self._get_store(memory_type)
        record_id = str(uuid.uuid4())
        
        record = MemoryRecord(
            record_id=record_id,
            memory_type=memory_type,
            title=title,
            content=content,
            tags=tags or [],
            importance_score=importance_score,
            related_project=related_project,
            status=status
        )
        
        store.create(record)
        
        # Keep only the latest 1000 entries for voice_history to prevent unlimited growth (Phase 5.3)
        if memory_type == "voice_history":
            try:
                records = store.list_records(limit=2000, offset=0)
                if len(records) > 1000:
                    sorted_recs = sorted(records, key=lambda r: r.created_at)
                    excess = len(sorted_recs) - 1000
                    for i in range(excess):
                        store.delete(sorted_recs[i].id)
            except Exception as e:
                logging.getLogger("ultron-agent").error(f"Error pruning voice history: {e}")
                
        self.on_memory_created(record.to_dict())
        return record_id

    def read_record(self, memory_type: str, record_id: str) -> Optional[Dict[str, Any]]:
        store = self._get_store(memory_type)
        record = store.read(record_id)
        return record.to_dict() if record else None

    def update_record(self, memory_type: str, record_id: str, updates: Dict[str, Any]) -> bool:
        store = self._get_store(memory_type)
        success = store.update(record_id, updates)
        if success:
            self.on_memory_updated(record_id)
        return success

    def delete_record(self, memory_type: str, record_id: str) -> bool:
        store = self._get_store(memory_type)
        success = store.delete(record_id)
        if success:
            self.on_memory_deleted(record_id)
        return success

    def list_records(self, memory_type: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        store = self._get_store(memory_type)
        records = store.list_records(limit, offset)
        return [r.to_dict() for r in records]

    def archive_record(self, memory_type: str, record_id: str) -> bool:
        store = self._get_store(memory_type)
        success = store.archive(record_id)
        if success:
            self.on_memory_archived(record_id)
        return success

    # -----------------------------------------------------------------------
    # Retrieval Strategy
    # -----------------------------------------------------------------------
    
    async def get_relevant_memories(self, query: str, related_project: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        UME Retrieval Strategy.
        Determines which stores to query, merges results, and ranks them by importance score.
        """
        all_matches: List[MemoryRecord] = []
        
        # Query conversation, project, preference, and knowledge stores
        stores_to_query = ["conversation", "preference", "knowledge"]
        if related_project:
            stores_to_query.append("project")
            
        for m_type in stores_to_query:
            store = self._stores[m_type]
            try:
                matches = store.search(query)
                # Filter by project if specified
                if related_project:
                    matches = [m for m in matches if m.related_project == related_project or m.related_project is None]
                all_matches.extend(matches)
            except Exception:
                pass
                
        # Rank by importance score descending
        all_sorted = sorted(all_matches, key=lambda r: r.importance_score, reverse=True)
        
        # De-duplicate by ID
        seen = set()
        deduped = []
        for rec in all_sorted:
            if rec.id not in seen:
                seen.add(rec.id)
                deduped.append(rec.to_dict())
                
        return deduped[:limit]

    # -----------------------------------------------------------------------
    # Memory Promotion
    # -----------------------------------------------------------------------
    
    def promote_working_entry(self, record_id: str, target_type: str, title: str = None) -> Optional[str]:
        """Promotes an entry from Working Memory to Project or Knowledge Memory."""
        if target_type not in ["project", "knowledge"]:
            raise ValueError("Can only promote Working Memory to project or knowledge stores")
            
        working_store: WorkingMemoryStore = self._stores["working"]
        record = working_store.read(record_id)
        if not record:
            return None
            
        # Delete from Working Memory
        working_store.delete(record_id)
        
        # Save into target store
        promoted_id = self.create_record(
            memory_type=target_type,
            title=title or record.title,
            content=record.content,
            tags=record.tags,
            importance_score=record.importance_score,
            related_project=record.related_project
        )
        self.on_memory_promoted(record_id, target_type)
        return promoted_id

    # -----------------------------------------------------------------------
    # Future Event Hooks Interfaces (Reserved)
    # -----------------------------------------------------------------------
    
    def on_memory_created(self, record: dict) -> None:
        """Fires when a memory is created."""
        from ultron.core.event_bus import event_bus
        event_bus.publish("MEMORY_UPDATED", {"action": "create", "record": record})

    def on_memory_updated(self, record_id: str) -> None:
        """Fires when a memory is updated."""
        from ultron.core.event_bus import event_bus
        event_bus.publish("MEMORY_UPDATED", {"action": "update", "id": record_id})

    def on_memory_deleted(self, record_id: str) -> None:
        """Fires when a memory is deleted."""
        from ultron.core.event_bus import event_bus
        event_bus.publish("MEMORY_UPDATED", {"action": "delete", "id": record_id})

    def on_memory_promoted(self, record_id: str, target_type: str) -> None:
        """Fires when a memory is promoted from working memory."""
        pass

    def on_memory_archived(self, record_id: str) -> None:
        """Fires when a memory is archived."""
        pass

def get_memory_manager():
    """Access the global memory manager instance."""
    from ultron.api.memory_api import memory_manager_ref
    return memory_manager_ref

from ultron.api.memory_api import set_memory_ref
