# ULTRON Projects Module

## Purpose
The Projects module manages metadata and contextual tracking for developers' active repositories and development projects.

## Responsibilities
*   **Context Management**: Maintains logs of current build statuses, pending task items, and recent git history.
*   **Workspace Mapping**: Indexes project structures, files, imports, and documentation references.
*   **Metadata Storage**: Keeps track of compiler, package, and environment configurations.

## Public Interfaces
*   `class ProjectManager`: Track context.
    *   `def set_active_project(path: str) -> None`
    *   `def get_project_status() -> Dict[str, Any]`
    *   `def index_workspace() -> None`

## Dependencies
*   `ultron.core` for global configuration loading.
*   `ultron.memory` to store and retrieve indexed projects data.

## Future Expansion
*   Implement automatic detection of active work tasks via git branch name changes.
*   Integrate build compiler feedback (e.g. tracking linting or syntax errors dynamically).

## Design Notes
*   **Metadata Decoupling**: Project-specific knowledge resides in `memory/projects/`, while the execution and parsing code belongs in this module.
