# ULTRON Memory Module

## Purpose
The Memory module manages context persistence across the ULTRON system. It is structured into multiple decoupled subsystems to handle active chat sessions, user preferences, codebase awareness, documentation libraries, and long-term persistent recall.

## Responsibilities
*   **Conversation Memory (`conversation/`)**: Maintains the immediate sliding-window context of the current voice or text interaction.
*   **Project Memory (`projects/`)**: Tracks active workspace metadata, code structures, and task history specific to the open repository.
*   **Preferences Memory (`preferences/`)**: Manages personalized configurations, preferred tools, and communication styles.
*   **Knowledge Memory (`knowledge/`)**: Stores and indexes documentation files, APIs, and research materials using vector indices.
*   **Long-Term Memory (`long_term/`)**: Manages persistent episodic records and conceptual associations across sessions.

## Public Interfaces
*   `class MemoryManager`: Central entry point for read/write requests.
    *   `async def store(category: str, key: str, value: Any) -> None`
    *   `async def retrieve(category: str, query: str) -> List[Any]`
    *   `async def clear(category: str) -> None`

## Dependencies
*   `ultron.core` for state sync and alerts.

## Future Expansion
*   Integrate a local Vector Database (e.g. SQLite-VSS, or Qdrant/Chroma wrappers) for indexing knowledge and long-term segments.
*   Incorporate summarization routines to compress conversation histories dynamically.

## Design Notes
*   **Decoupled Schemas**: Each memory type is stored in its own namespace directory to allow independent schema updates and modular caching.
