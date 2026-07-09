# ULTRON Core Module

## Purpose
The Core module is the central communication bus and orchestration controller of the ULTRON Cognitive Operating System. It manages the global application state, event routing, module lifecycle registration, and shared async services.

## Responsibilities
*   **Event Routing**: Dispatches messages and state change events between decoupled modules (e.g., Planner to Automation, Memory to LLM).
*   **State Lifecycle**: Manages startup, shutdown, worker pooling, and error mitigation services.
*   **Shared Services**: Exposes common features like the system configuration loader, centralized logging utilities, and network client connections.

## Public Interfaces
*   `class CoreSystem`: Central orchestration engine.
    *   `register_module(module_name: str, instance: Any) -> None`
    *   `dispatch_event(event_type: str, payload: Dict[str, Any]) -> None`
    *   `get_module(module_name: str) -> Any`
    *   `shutdown() -> None`

## Dependencies
*   None. (Strictly decoupled, low-level modules should inherit base classes from Core, but Core must remain independent of external module logic).

## Future Expansion
*   Implement a Pub/Sub event bus supporting concurrent thread dispatching.
*   Integrate centralized system signal handlers (`SIGINT`, `SIGTERM`) to initiate graceful worker shutdowns.

## Design Notes
*   **Single Responsibility**: Core is only responsible for routing and configuration. It must not contain domain-specific logic (e.g., how to search the web or how to translate text).
*   **Decoupling Principle**: Other modules communicate by dispatching events through Core or invoking defined interfaces rather than calling each other directly.
