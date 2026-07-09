# ULTRON Execution Module

## Purpose
The Execution module processes normalized action steps, invokes external tools via the MCP protocol or local host shell executors, and returns structured result packets.

## Responsibilities
*   **Action Invocation**: Dispatches tool queries to the MCP server SSE link.
*   **Security Gating**: Verifies safety permissions prior to executing Warning or Critical actions.

## Public Interfaces
*   `class ExecutionResult`: Return structure tracking success state.
*   `class ExecutionEngine`: Action dispatcher.
    *   `async def execute_step(step: CognitiveStep) -> ExecutionResult`

## Design Notes
*   **Process Isolation**: Tools must be executed via asynchronous, non-blocking calls.
