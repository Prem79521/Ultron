# ULTRON Planner Module

## Purpose
The Planner module deconstructs hydrated user objectives into a sequence of dependent tasks (an `ExecutionPlan`), enabling ULTRON to coordinate multi-step workflows.

## Responsibilities
*   **Decomposition**: Analyzes `HydratedContext` payloads and breaks them down into task steps.
*   **Replanning**: Modifies active execution plans dynamically based on reflection self-correction inputs.

## Public Interfaces
*   `class Task`: Individual execution block.
*   `class ExecutionPlan`: Container mapping dependencies and objective schemas.
*   `class CognitivePlanner`: Core planning coordinator.
    *   `async def create_plan(context: HydratedContext) -> ExecutionPlan`
    *   `async def revise_plan(plan: ExecutionPlan, failed_task_id: str, error: str) -> ExecutionPlan`

## Design Notes
*   **Interface Separation**: The planner operates purely on semantic schemas and plan structures; it does not invoke model prompts or run CLI commands directly.
