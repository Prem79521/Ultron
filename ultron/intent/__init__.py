"""
ULTRON Intent Module — Semantic intent classification and entity parsing interfaces.
"""

from typing import Dict, Any, List
from ultron.perception import CognitiveRequest

class IntentModel:
    def __init__(self, category: str, confidence: float, entities: Dict[str, Any] = None):
        self.category = category
        self.confidence = confidence
        self.entities = entities or {}

class IntentParser:
    def __init__(self, core_system):
        self.core = core_system

    async def parse_intent(self, request: CognitiveRequest) -> IntentModel:
        return IntentModel("unknown", 0.0)
