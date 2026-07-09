"""
ULTRON Memory Engine (UME) — SQLite-backed structured memory store implementation.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

class MemoryRecord:
    """Standardized memory record format supporting future ranking and semantic retrieval."""
    def __init__(
        self,
        record_id: str,
        memory_type: str,
        title: str,
        content: str,
        tags: List[str] = None,
        importance_score: int = 5,
        created_at: str = None,
        updated_at: str = None,
        last_accessed_at: str = None,
        access_count: int = 0,
        related_project: str = None,
        status: str = "active",
        version: int = 1
    ):
        self.id = record_id
        self.memory_type = memory_type
        self.title = title
        self.content = content
        self.tags = tags or []
        self.importance_score = importance_score
        
        now_str = datetime.utcnow().isoformat()
        self.created_at = created_at or now_str
        self.updated_at = updated_at or now_str
        self.last_accessed_at = last_accessed_at or now_str
        
        self.access_count = access_count
        self.related_project = related_project
        self.status = status
        self.version = version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_type": self.memory_type,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "importance_score": self.importance_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
            "related_project": self.related_project,
            "status": self.status,
            "version": self.version
        }

class MemoryStore:
    """Interface for stable memory stores (storage-agnostic)."""
    def create(self, record: MemoryRecord) -> str:
        raise NotImplementedError

    def read(self, record_id: str) -> Optional[MemoryRecord]:
        raise NotImplementedError

    def update(self, record_id: str, updates: Dict[str, Any]) -> bool:
        raise NotImplementedError

    def delete(self, record_id: str) -> bool:
        raise NotImplementedError

    def search(self, query: str, tags: List[str] = None) -> List[MemoryRecord]:
        raise NotImplementedError

    def list_records(self, limit: int = 100, offset: int = 0) -> List[MemoryRecord]:
        raise NotImplementedError

    def archive(self, record_id: str) -> bool:
        raise NotImplementedError

class SqliteMemoryStore(MemoryStore):
    """SQLite implementation of the MemoryStore interface with indexing optimization."""
    def __init__(self, db_path: str, table_name: str, memory_type: str):
        self.db_path = db_path
        self.table_name = table_name
        self.memory_type = memory_type
        self._init_db()

    def _get_connection(self):
        import contextlib
        @contextlib.contextmanager
        def connection_context():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
        return connection_context()


    def _init_db(self):
        """Initializes tables and creates optimized indexes for faster lookups."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create separate table for this memory store type
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    importance_score INTEGER DEFAULT 5,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_accessed_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    related_project TEXT,
                    status TEXT DEFAULT 'active',
                    version INTEGER DEFAULT 1
                )
            """)
            
            # Optimize with query indexes
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_tags ON {self.table_name}(tags)")
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_project ON {self.table_name}(related_project)")
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_updated ON {self.table_name}(updated_at)")
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_importance ON {self.table_name}(importance_score)")
            conn.commit()

    def create(self, record: MemoryRecord) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            tags_json = json.dumps(record.tags)
            cursor.execute(f"""
                INSERT INTO {self.table_name} (
                    id, title, content, tags, importance_score, created_at, 
                    updated_at, last_accessed_at, access_count, related_project, status, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id, record.title, record.content, tags_json, record.importance_score,
                record.created_at, record.updated_at, record.last_accessed_at, record.access_count,
                record.related_project, record.status, record.version
            ))
            conn.commit()
        return record.id

    def read(self, record_id: str) -> Optional[MemoryRecord]:
        now_str = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Update access metadata first
            cursor.execute(f"""
                UPDATE {self.table_name} 
                SET last_accessed_at = ?, access_count = access_count + 1 
                WHERE id = ?
            """, (now_str, record_id))
            conn.commit()
            
            # Fetch the updated row
            cursor.execute(f"""
                SELECT * FROM {self.table_name} WHERE id = ?
            """, (record_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            return self._row_to_record(row)


    def update(self, record_id: str, updates: Dict[str, Any]) -> bool:
        if not updates:
            return False
        
        now_str = datetime.utcnow().isoformat()
        updates["updated_at"] = now_str
        
        query_parts = []
        params = []
        for key, val in updates.items():
            if key == "tags":
                val = json.dumps(val)
            query_parts.append(f"{key} = ?")
            params.append(val)
            
        params.append(record_id)
        query = f"UPDATE {self.table_name} SET {', '.join(query_parts)} WHERE id = ?"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            conn.commit()
            success = cursor.rowcount > 0
        return success

    def delete(self, record_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (record_id,))
            conn.commit()
            success = cursor.rowcount > 0
        return success

    def search(self, query: str, tags: List[str] = None) -> List[MemoryRecord]:
        """Performs simple local text and tags filtering search."""
        sql = f"SELECT * FROM {self.table_name} WHERE (title LIKE ? OR content LIKE ?)"
        params = [f"%{query}%", f"%{query}%"]
        
        records = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            
            for row in rows:
                record = self._row_to_record(row)
                if tags:
                    # Filter tags locally if specified
                    if any(t in record.tags for t in tags):
                        records.append(record)
                else:
                    records.append(record)
        return records

    def list_records(self, limit: int = 100, offset: int = 0) -> List[MemoryRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM {self.table_name} ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
            return [self._row_to_record(row) for row in rows]

    def archive(self, record_id: str) -> bool:
        return self.update(record_id, {"status": "archived"})

    def _row_to_record(self, row) -> MemoryRecord:
        try:
            tags = json.loads(row["tags"]) if row["tags"] else []
        except Exception:
            tags = []
            
        return MemoryRecord(
            record_id=row["id"],
            memory_type=self.memory_type,
            title=row["title"],
            content=row["content"],
            tags=tags,
            importance_score=row["importance_score"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_accessed_at=row["last_accessed_at"],
            access_count=row["access_count"],
            related_project=row["related_project"],
            status=row["status"],
            version=row["version"]
        )
