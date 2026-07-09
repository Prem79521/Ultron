# ULTRON Automation Module

## Purpose
The Automation module provides the interface layer to execute shell commands, manage processes, automate keyboard and mouse events, and interface with host APIs.

## Responsibilities
*   **Command Execution**: Executes local system operations within a controlled subprocess environment.
*   **File Operations**: Handles secure creation, editing, mapping, and copying of workspace directories.
*   **Desktop/System Automation**: Houses scripts to launch apps, capture screen coordinates, or orchestrate GUI events.

## Public Interfaces
*   `class SystemExecutor`: Runs shell environments safely.
    *   `async def execute_command(command: str) -> Dict[str, Any]`
    *   `async def edit_file(path: str, edits: List[Any]) -> bool`

## Dependencies
*   `ultron.core` for logging commands.
*   `ultron.permissions` to validate execution levels.

## Future Expansion
*   Implement containerized tool isolation (e.g. running scripts inside Docker/Sandbox namespaces) to secure the host filesystem.
*   Introduce dynamic UI automation libraries (e.g., PyAutoGUI or browser controllers).

## Design Notes
*   **Permissions Gate**: All automation commands must check with the Permission Manager prior to spawning a shell process.
