# ULTRON Reasoning Module

## Purpose
The Reasoning module evaluates individual tasks in the execution plan, determines the appropriate execution strategy (e.g. LLM instruction, tool call, prompt template), and packages them for the execution stage.

## Responsibilities
*   **Action Determination**: Maps task text descriptions to concrete executable formats.
*   **Prompt Formulation**: Resolves, structures, and variables-hydrate markdown prompts (such as those in `prompts/`).

## Public Interfaces
*   `class ActionType(Enum)`: Options: `LLM_PROMPT`, `TOOL_CALL`, `NOOP`.
*   `class CognitiveStep`: Packages action target parameters.
*   `class ReasoningEngine`: Evaluator pipeline.
    *   `async def evaluate_task(task: Task, context: HydratedContext) -> List[CognitiveStep]`

## Design Notes
*   **Provider Agnostic**: Reasoning operates on model-independent abstract interfaces. It does not speak directly to Google or OpenAI API servers; it prepares instructions.
