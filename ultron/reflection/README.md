# ULTRON Reflection Module

## Purpose
The Reflection module evaluates action outputs, identifies failures or syntax issues, determines if dynamic replanning is needed, and builds the final, UI-independent `CognitiveResponse`.

## Responsibilities
*   **Quality Audit**: Validates outputs against original task constraints.
*   **Correction Trigger**: If audit failure occurs, signals the Planner to revise the execution plan.
*   **Response Synthesis**: Synthesizes output texts or parameters into a clean client-ready package.

## Public Interfaces
*   `class CognitiveResponse`: Response container.
*   `class ReflectionEngine`: Verifier and output mapper.
    *   `async def evaluate_results(plan: ExecutionPlan, results: List[ExecutionResult]) -> CognitiveResponse`

## Design Notes
*   **Decoupled Output**: The response must not import audio-out systems or direct voice drivers; client interfaces receive this model and handle local playback.
