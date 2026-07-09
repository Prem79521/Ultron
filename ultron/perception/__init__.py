"""
ULTRON Perception Module — Normalizes raw input streams into standardized request models.
"""

from enum import Enum
from typing import Dict, Any

class Modality(Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    SCREEN = "screen"

class CognitiveRequest:
    def __init__(self, session_id: str, modality: Modality, payload: bytes, metadata: Dict[str, Any] = None):
        self.session_id = session_id
        self.modality = modality
        self.payload = payload
        self.metadata = metadata or {}

class PerceptionEngine:
    def __init__(self, core_system):
        self.core = core_system

    async def normalize_text(self, session_id: str, text: str, metadata: Dict[str, Any] = None) -> CognitiveRequest:
        payload_bytes = text.encode("utf-8")
        return CognitiveRequest(
            session_id=session_id,
            modality=Modality.TEXT,
            payload=payload_bytes,
            metadata=metadata
        )

    async def normalize_audio(self, session_id: str, audio_data: bytes, metadata: Dict[str, Any] = None) -> CognitiveRequest:
        return CognitiveRequest(
            session_id=session_id,
            modality=Modality.VOICE,
            payload=audio_data,
            metadata=metadata
        )
