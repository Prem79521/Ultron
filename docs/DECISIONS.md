# ULTRON Architecture Decision Log (ADR)

This document records the key architectural decisions made during the design and evolution of the ULTRON Cognitive Operating System.

---

## Decision #001: Independent Planner Module

### Context
The LLM should not handle orchestrational task breakdown, scheduling, or execution monitoring directly within its system prompt instructions.

### Decision
The Planner will be designed as an independent module (`ultron/planner/`) separate from the LLM connector. The LLM will provide reasoning capabilities, but task parsing, state machines, and delegation will be managed by code-level orchestration.

### Alternatives Considered
1. **Monolithic Prompting**: Instructing the LLM to plan and execute in a single massive prompt sequence. *Rejected due to context window limits, high latency, and lack of deterministic execution control.*

### Consequences
*   **Pros**: Supports multiple LLM backends (Gemini, OpenAI, Groq) seamlessly, ensures deterministic task tracking, and facilitates robust error recovery.
*   **Cons**: Requires a formal internal event/state router between the LLM and the Planner.

### Date
2026-07-05

---

## Decision #002: Modular and Decoupled Directory Structure

### Context
To grow the codebase without running into circular dependencies or bloated modules, we need a directory structure that isolates responsibilities.

### Decision
Create independent submodules within the core package namespace (`ultron/`):
*   `core/` for event dispatching and life cycle management.
*   `planner/` for task composition and control.
*   `memory/` (split into `conversation`, `projects`, `preferences`, `knowledge`, `long_term`).
*   `automation/` for execution utilities.
*   `vision/` for multi-modal context.
*   `permissions/` for safe/warning/critical gating.
*   `projects/` for codebase/context metadata awareness.
*   `plugins/` for external integrations.

### Alternatives Considered
1. **Tool-Centric Design**: Keeping all functionality under the standard MCP `tools/` namespace. *Rejected because capabilities like persistent memory and planning are core architectural components, not just stateless tools.*

### Consequences
*   **Pros**: Simplifies code maintenance, enforces Single Responsibility, and allows contributors to scale individual subsystems independently.
*   **Cons**: Introduces initial directory scaffolding complexity.

### Date
2026-07-05

---

## Decision #003: User Identity System

### Context
Hardcoding user names (e.g. "Prem") in system prompts restricts multi-user scalability and local deployment flexibility.

### Decision
Implement a configurable User Profile system loaded from environment variables or custom configuration settings (`DISPLAY_NAME`), with a graceful neutral fallback (e.g. "my friend", or omitting name references) if no profile exists.

### Alternatives Considered
1. **Hardcoded Strings**: Placing "Prem" in system prompts and greetings. *Rejected due to poor scalability.*

### Consequences
*   **Pros**: Easy multi-user scaling, clean localization, and configuration-driven personalization.
*   **Cons**: Small configuration overhead.

### Date
2026-07-05

---

## Decision #004: Extensible Greeting Engine

### Context
A static, hardcoded session greeting does not account for user context (time of day, return time, holiday, active project, absence).

### Decision
Implement an extensible greeting engine based on a Strategy pattern. Additional greeting strategies (TimeOfDay, Absence, ProjectContext) can be added as modules without altering the core initialization sequence.

### Alternatives Considered
1. **Static greeting mapping**: Hardcoded if-else statements inside the LiveKit agent event handlers. *Rejected because it violates the Open-Closed Principle.*

### Consequences
*   **Pros**: Allows dynamic, contextual greetings based on complex real-time variables.
*   **Cons**: Slightly more complex module registry setup for greetings.

### Date
2026-07-05
