"""
MCP Memory Tools — Exposes first-class domain-specific UME (Ultron Memory Engine) capabilities.
"""

from typing import List, Dict, Any, Optional

def _get_or_create_memory_manager():
    """Accesses the active MemoryManager or initializes a fallback for standalone mode."""
    from ultron.memory import get_memory_manager, MemoryManager
    from ultron.api.memory_api import set_memory_ref
    
    mgr = get_memory_manager()
    if not mgr:
        # Fallback for standalone MCP server process
        mgr = MemoryManager(db_path="ultron_memory.db")
        set_memory_ref(mgr)
    return mgr

VALID_MEMORY_TYPES = [
    "conversation", "project", "preference", "knowledge", 
    "permission", "log", "session", "voice_settings", 
    "provider_settings", "plugin_settings", "notification", 
    "voice_history", "wake_history", "diagnostics"
]

def register(mcp):

    @mcp.tool()
    def get_valid_memory_types() -> List[str]:
        """Get the list of valid memory types / domains supported by the memory engine."""
        return VALID_MEMORY_TYPES

    @mcp.tool()
    def list_memory_records(memory_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List records from a specific memory domain (e.g. 'project', 'preference', 'knowledge').
        Returns list of memory records.
        """
        if memory_type not in VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory type. Must be one of: {VALID_MEMORY_TYPES}")
            
        try:
            mgr = _get_or_create_memory_manager()
            return mgr.list_records(memory_type, limit=limit)
        except Exception as exc:
            return [{"error": f"Failed to list memories: {exc}"}]

    @mcp.tool()
    def search_memories(query: str, related_project: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for relevant memory records across conversation, preference, knowledge, and project domains.
        Ranks matching records based on UME ranking and importance scores.
        """
        try:
            mgr = _get_or_create_memory_manager()
            # search is async in UME
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            if loop.is_running():
                # We are in an async context, we must create a task or run it
                import nest_asyncio
                nest_asyncio.apply()
                
            memories = loop.run_until_complete(
                mgr.get_relevant_memories(query, related_project=related_project, limit=limit)
            )
            return memories
        except Exception as exc:
            return [{"error": f"Failed to search memories: {exc}"}]

    @mcp.tool()
    def create_memory_record(
        memory_type: str,
        title: str,
        content: str,
        tags: List[str] = None,
        importance_score: int = 5,
        related_project: str = None,
        status: str = "active"
    ) -> str:
        """
        Create a new memory record in the specified UME domain.
        Returns the generated UUID of the created record.
        """
        if memory_type not in VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory type. Must be one of: {VALID_MEMORY_TYPES}")
            
        try:
            mgr = _get_or_create_memory_manager()
            record_id = mgr.create_record(
                memory_type=memory_type,
                title=title,
                content=content,
                tags=tags,
                importance_score=importance_score,
                related_project=related_project,
                status=status
            )
            return record_id
        except Exception as exc:
            return f"Error creating memory record: {exc}"

    @mcp.tool()
    def update_memory_record(memory_type: str, record_id: str, updates: Dict[str, Any]) -> str:
        """
        Update an existing memory record.
        Updates should be a dictionary of fields to modify (e.g. {'content': 'new text'}).
        """
        if memory_type not in VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory type. Must be one of: {VALID_MEMORY_TYPES}")
            
        try:
            mgr = _get_or_create_memory_manager()
            # Avoid updating internal immutable keys directly
            safe_updates = {k: v for k, v in updates.items() if k not in ["id", "memory_type", "created_at"]}
            success = mgr.update_record(memory_type, record_id, safe_updates)
            return "SUCCESS" if success else "FAILED (Record not found or update error)"
        except Exception as exc:
            return f"Error updating record: {exc}"

    @mcp.tool()
    def delete_memory_record(memory_type: str, record_id: str) -> str:
        """Delete a memory record from a specific domain by UUID."""
        if memory_type not in VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory type. Must be one of: {VALID_MEMORY_TYPES}")
            
        try:
            mgr = _get_or_create_memory_manager()
            success = mgr.delete_record(memory_type, record_id)
            return "SUCCESS" if success else "FAILED (Record not found or deletion error)"
        except Exception as exc:
            return f"Error deleting record: {exc}"
