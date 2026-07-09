"""
ULTRON Working Memory Module — Temporary task state in-memory store.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from ultron.memory.store import MemoryStore, MemoryRecord

class WorkingMemoryStore(MemoryStore):
    """In-memory dictionary implementation of the MemoryStore interface for active task states."""
    def __init__(self):
        self._records: Dict[str, MemoryRecord] = {}

    def create(self, record: MemoryRecord) -> str:
        self._records[record.id] = record
        return record.id

    def read(self, record_id: str) -> Optional[MemoryRecord]:
        record = self._records.get(record_id)
        if record:
            record.access_count += 1
            record.last_accessed_at = datetime.utcnow().isoformat()
        return record

    def update(self, record_id: str, updates: Dict[str, Any]) -> bool:
        record = self._records.get(record_id)
        if not record:
            return False
            
        for key, val in updates.items():
            if hasattr(record, key):
                setattr(record, key, val)
                
        record.updated_at = datetime.utcnow().isoformat()
        return True

    def delete(self, record_id: str) -> bool:
        if record_id in self._records:
            del self._records[record_id]
            return True
        return False

    def search(self, query: str, tags: List[str] = None) -> List[MemoryRecord]:
        results = []
        query_lower = query.lower()
        
        for record in self._records.values():
            in_title = query_lower in record.title.lower()
            in_content = query_lower in record.content.lower()
            
            if in_title or in_content:
                if tags:
                    if any(t in record.tags for t in tags):
                        results.append(record)
                else:
                    results.append(record)
        return results

    def list_records(self, limit: int = 100, offset: int = 0) -> List[MemoryRecord]:
        all_sorted = sorted(self._records.values(), key=lambda r: r.created_at, reverse=True)
        return all_sorted[offset : offset + limit]

    def archive(self, record_id: str) -> bool:
        return self.update(record_id, {"status": "archived"})

    def clear(self) -> None:
        """Flushes all current working memory records. Triggered when the current task completes."""
        self._records.clear()
