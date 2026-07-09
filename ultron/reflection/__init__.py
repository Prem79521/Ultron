"""
ULTRON Reflection Module — Output verification, selective persistence, and response compilation.
"""

from typing import Dict, Any, List, Optional
from ultron.planner import ExecutionPlan
from ultron.execution import ExecutionResult

class CognitiveResponse:
    def __init__(self, session_id: str, text_content: str, audio_content: Optional[bytes] = None, metadata: Dict[str, Any] = None):
        self.session_id = session_id
        self.text_content = text_content
        self.audio_content = audio_content
        self.metadata = metadata or {}

class PersistencePolicy:
    """Decides whether a memory record should be persisted based on length and relevance."""
    def should_persist(self, text: str) -> bool:
        if not text:
            return False
        cleaned = text.strip()
        # Don't persist empty, extremely short (e.g. system noise or trivial acknowledgements), or repetitive lines
        if len(cleaned) < 15:
            return False
        if cleaned.lower() in ["noop", "ok", "ack", "system active"]:
            return False
        return True

class ReflectionEngine:
    def __init__(self, core_system, memory_manager=None):
        self.core = core_system
        self.memory = memory_manager
        self.policy = PersistencePolicy()

    async def evaluate_results(self, session_id: str, plan: ExecutionPlan, results: List[ExecutionResult]) -> CognitiveResponse:
        """Audits plan completion, updates UME conversation stores selectively, and resets working memory."""
        # Compile response text based on execution outputs
        compiled_outputs = []
        for res in results:
            if res.success:
                compiled_outputs.append(str(res.output))
            elif res.error_message:
                compiled_outputs.append(f"Error: {res.error_message}")
                
        response_text = "\n".join(compiled_outputs) or "Task completed."
        
        if self.memory:
            # 1. Selective Persistence check prior to saving conversation logs
            if self.policy.should_persist(response_text):
                self.memory.create_record(
                    memory_type="conversation",
                    title=f"Interaction turn: {session_id[:8]}",
                    content=f"Objective: {plan.objective}\nResult: {response_text}",
                    tags=["conversation", "interaction"],
                    importance_score=6
                )
                
            # 2. Reset Working Memory store upon completion of task execution
            working_store = self.memory._stores.get("working")
            if working_store and hasattr(working_store, "clear"):
                working_store.clear()
                
        return CognitiveResponse(
            session_id=session_id,
            text_content=response_text
        )
