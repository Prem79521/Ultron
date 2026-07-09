"""
ULTRON Context Module — Hydrates requests with workspace metadata, preferences, and session histories.
"""

from typing import Dict, Any, List, Optional
from ultron.perception import CognitiveRequest

class HydratedContext:
    def __init__(
        self,
        request: CognitiveRequest,
        user_name: str,
        preferences: Dict[str, Any] = None,
        project_metadata: Dict[str, Any] = None,
        memories: List[Dict[str, Any]] = None
    ):
        self.request = request
        self.user_name = user_name
        self.preferences = preferences or {}
        self.project_metadata = project_metadata or {}
        self.memories = memories or []

class ContextHydrator:
    def __init__(self, core_system, memory_manager=None):
        self.core = core_system
        self.memory = memory_manager

    async def hydrate(self, request: CognitiveRequest) -> HydratedContext:
        """Hydrates the normalized request with contextual records using UME retrieval strategies."""
        user_name = "Prem"  # Default fallback name
        preferences = {}
        project_metadata = {}
        memories = []

        if self.memory:
            # 1. Resolve configured user display name from Preference Memory
            pref_records = self.memory.list_records("preference", limit=10)
            for record in pref_records:
                if record["title"] == "display_name":
                    user_name = record["content"]
                preferences[record["title"]] = record["content"]
                
            # 2. Query Project metadata from Project Memory if project context exists
            project_id = request.metadata.get("related_project")
            if project_id:
                proj_record = self.memory.read_record("project", project_id)
                if proj_record:
                    project_metadata = proj_record
                    
            # 3. Retrieve relevant memories via UME retrieval strategy
            request_text = request.payload.decode("utf-8", errors="ignore")
            if request_text:
                memories = await self.memory.get_relevant_memories(
                    query=request_text,
                    related_project=project_id
                )
                
        return HydratedContext(
            request=request,
            user_name=user_name,
            preferences=preferences,
            project_metadata=project_metadata,
            memories=memories
        )
