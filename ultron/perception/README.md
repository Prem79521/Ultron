# ULTRON Perception Module

## Purpose
The Perception module normalizes multiple input types (text, voice, and future modalities like images or video) into a unified internal request object (`CognitiveRequest`), keeping the reasoning pipeline independent of the user interface.

## Responsibilities
*   **Modality Normalization**: Captures raw input bytes and packages them into a clean internal data structure.
*   **Transcription Routing**: Triggers Speech-to-Text translation for voice audio packets during the normalization stage.

## Public Interfaces
*   `class Modality(Enum)`: Enumerate supported modality types.
*   `class CognitiveRequest`: Unified request data structure.
*   `class PerceptionEngine`: Normalizer pipeline.
    *   `async def normalize_text(text: str, metadata: dict) -> CognitiveRequest`
    *   `async def normalize_audio(audio_data: bytes, metadata: dict) -> CognitiveRequest`

## Design Notes
*   **No UI Dependency**: Perception must never import LiveKit, CLI libraries, or Web server handlers. It only receives raw payloads.
