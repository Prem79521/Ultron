# ULTRON Context Module

## Purpose
The Context module hydrates a normalized `CognitiveRequest` with the appropriate cognitive context (retrieving user preferences, active project metadata, and relevant memory vectors) prior to planning and reasoning.

## Responsibilities
*   **Context Hydration**: Queries supporting modules (Memory, Projects, Configurations) to assemble a rich metadata picture.
*   **User Profile Retrieval**: Resolves configured user display names and preferences.

## Public Interfaces
*   `class HydratedContext`: Contextual container model.
*   `class ContextHydrator`: Hydrates requests.
    *   `async def hydrate(request: CognitiveRequest) -> HydratedContext`

## Design Notes
*   **Stable Interface**: Direct database reads or workspace lookups must occur through memory and project interface calls rather than context doing direct I/O.
