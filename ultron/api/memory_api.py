"""
ULTRON API Layer — Memory API interface.
"""

from typing import Dict, Any, List, Optional

# Loaded globally at boot
memory_manager_ref = None

def set_memory_ref(memory_manager):
    global memory_manager_ref
    memory_manager_ref = memory_manager

def save_record(memory_type: str, title: str, content: str) -> Optional[str]:
    if memory_manager_ref:
        return memory_manager_ref.create_record(memory_type, title, content)
    return None

def query_records(memory_type: str, limit: int = 100) -> List[Dict[str, Any]]:
    if memory_manager_ref:
        return memory_manager_ref.list_records(memory_type, limit=limit)
    return []
