"""
ULTRON Cognitive OS — Persistent Learning Memory.
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class LearningMemory:
    """Manages long-term learned command resolution mappings in SQLite."""
    def __init__(self, memory_manager):
        self.memory = memory_manager

    def get_mapping(self, phrase: str) -> Optional[Dict[str, Any]]:
        """Retrieves a learned mapping for a user phrase, if it exists."""
        phrase_clean = phrase.lower().strip()
        try:
            records = self.memory.list_records("learning", limit=1000)
            for r in records:
                if r["title"] == phrase_clean:
                    return json.loads(r["content"])
        except Exception:
            pass
        return None

    def learn(self, phrase: str, entity_name: str, confidence: float, source: str):
        """Creates or updates a confirmed resolution mapping."""
        phrase_clean = phrase.lower().strip()
        existing = self.get_mapping(phrase_clean)
        
        now_str = datetime.utcnow().isoformat()
        
        if existing:
            # Update launch count and metadata
            record_id = None
            try:
                records = self.memory.list_records("learning", limit=1000)
                for r in records:
                    if r["title"] == phrase_clean:
                        record_id = r["id"]
                        break
            except Exception:
                pass
                
            if record_id:
                existing["launch_count"] += 1
                existing["last_used"] = now_str
                existing["confidence"] = confidence
                existing["resolution_source"] = source
                existing["resolved_entity"] = entity_name
                
                self.memory.update_record(
                    "learning",
                    record_id,
                    {"content": json.dumps(existing)}
                )
        else:
            # Create new mapping record
            mapping = {
                "user_phrase": phrase_clean,
                "resolved_entity": entity_name,
                "confidence": confidence,
                "launch_count": 1,
                "last_used": now_str,
                "resolution_source": source
            }
            self.memory.create_record(
                "learning",
                title=phrase_clean,
                content=json.dumps(mapping),
                tags=["learning_memory", "resolved_app"]
            )
