# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-07-06

### Added
*   Windows integration launch scripts [run_ultron.bat](file:///c:/Users/craft/Desktop/Ultron/run_ultron.bat) and [run_ultron.ps1](file:///c:/Users/craft/Desktop/Ultron/run_ultron.ps1) supporting virtual environment activation and auto-pausing on execution failures.
*   Desktop shortcut generator utility [scripts/create_desktop_shortcut.py](file:///c:/Users/craft/Desktop/Ultron/scripts/create_desktop_shortcut.py) targeting local desktops with minimized launch flags to prevent terminal spawns.
*   Generated premium multi-resolution [assets/icons/ultron.ico](file:///c:/Users/craft/Desktop/Ultron/assets/icons/ultron.ico) and integrated taskbar AppUserModelID process grouping via ctypes inside [main.py](file:///c:/Users/craft/Desktop/Ultron/main.py).
*   Implemented PySide6 (Qt) Native Desktop UI module in the `ui/` folder, featuring a frameless, matte-black main window, title bar window controls, and UI state system.

*   GPU-accelerated boot sequence controller [ui/boot_screen.py](file:///c:/Users/craft/Desktop/Ultron/ui/boot_screen.py) executing real subsystem health validations on configurations, memory, skills, and audio components.
*   Custom QPainter-drawn glowing scarlet red wave [ui/waveform.py](file:///c:/Users/craft/Desktop/Ultron/ui/waveform.py) reacting dynamically to speech status.
*   Real-time debugging console logger [ui/developer_console.py](file:///c:/Users/craft/Desktop/Ultron/ui/developer_console.py) mapped to `Ctrl+Shift+D` shortcut.
*   Centralized configuration JSON mappings under the `config/` directory.
*   Dynamic Skill Registry [ultron/skills/registry.py](file:///c:/Users/craft/Desktop/Ultron/ultron/skills/registry.py) loading built-in scripts and future plugins.
*   Implemented 5 native developer execution skills:
    *   `ProjectManagerSkill`: Restores workspace settings from UME and seeds mock ROWDY project configurations.
    *   `FileSystemSkill`: Validates path existence, directory structures, and file operations.
    *   `TerminalSkill`: Executes shell commands and spawns PowerShell windows targeting the project directories on Windows.
    *   `BrowserSkill`: Launches links, searches, and local projects.
    *   `CommandDispatcher`: Coordinates step-by-step pipeline flows (Perception → Context → Planner → Reasoning → Execution → Reflection) and emits log events.
*   Lightweight internal pub/sub [ultron/core/event_bus.py](file:///c:/Users/craft/Desktop/Ultron/ultron/core/event_bus.py).
*   Session lifecycle management `SessionManager` in [ultron/core/session.py](file:///c:/Users/craft/Desktop/Ultron/ultron/core/session.py).
*   Offline speech provider interface and `Pyttsx3VoiceProvider` implementation in [ultron/voice/__init__.py](file:///c:/Users/craft/Desktop/Ultron/ultron/voice/__init__.py) running on independent background threads.
*   Unified root-level application entry point [main.py](file:///c:/Users/craft/Desktop/Ultron/main.py) coordinating initializations.

## [1.2.0] - 2026-07-05


### Added
*   Created workspace agents rule configuration [.agents/AGENTS.md](file:///c:/Users/craft/Desktop/Ultron/.agents/AGENTS.md) establishing Local-First Design rules.
*   Functional local-first UME (ULTRON Memory Engine) implementation in [ultron/memory/store.py](file:///c:/Users/craft/Desktop/Ultron/ultron/memory/store.py) and [ultron/memory/__init__.py](file:///c:/Users/craft/Desktop/Ultron/ultron/memory/__init__.py).

*   Standardized `MemoryRecord` data layout supporting UUID generation, timestamps, access tracking, importance scoring, and versioning.
*   Independent SQLite tables (`conversation_memory`, `project_memory`, `preference_memory`, `knowledge_memory`) with index optimizations on query targets (`tags`, `related_project`, `updated_at`, `importance_score`).
*   In-memory task-state store `WorkingMemoryStore` under [ultron/working_memory/__init__.py](file:///c:/Users/craft/Desktop/Ultron/ultron/working_memory/__init__.py).
*   Configurable lifecycle policies (`LifecyclePolicy`) mapping persistence scopes.
*   Cognitive Core integration in [ultron/context/__init__.py](file:///c:/Users/craft/Desktop/Ultron/ultron/context/__init__.py) for profile names and project hydration, and in [ultron/reflection/__init__.py](file:///c:/Users/craft/Desktop/Ultron/ultron/reflection/__init__.py) for task results logging and working memory reset.
*   Working Memory promotion interface resolving transitions from transient to persistent memory stores.
*   UME Integration verification test script [scratch/verify_memory.py](file:///c:/Users/craft/Desktop/Ultron/scratch/verify_memory.py).

## [1.1.0] - 2026-07-05


### Added
*   Decoupled Cognitive Core architecture specification in [docs/COGNITIVE_CORE.md](file:///c:/Users/craft/Desktop/Ultron/docs/COGNITIVE_CORE.md).
*   Cognitive pipeline module directories and public interfaces skeleton code:
    *   `perception/`: Modality Normalization engines (`Modality`, `CognitiveRequest`).
    *   `context/`: Semantic hydration wrapper interface (`HydratedContext`, `ContextHydrator`).
    *   `planner/`: Plan deconstruction interface (`ExecutionPlan`, `Task`, `CognitivePlanner`).
    *   `reasoning/`: Action evaluation interface (`ActionType`, `CognitiveStep`, `ReasoningEngine`).
    *   `execution/`: Tool/action execution interface (`ExecutionResult`, `ExecutionEngine`).
    *   `reflection/`: Output verification and response compilation interface (`CognitiveResponse`, `ReflectionEngine`).
*   Reserved architecture extension points (README templates and interface declarations) for future cognitive systems:
    *   `events/`: Event telemetry and messaging bus interface.
    *   `intent/`: Semantic intent classification interface.
    *   `world_state/`: Environment state tracking and snapshotting interface.
    *   `skills/`: High-level domain capability interface.
    *   `working_memory/`: Active task variable scratchpad interface.
    *   `learning/`: Pattern optimization and correction feedback engine interface.

## [1.0.0] - 2026-07-05


### Added
*   Modular prompt architecture under `ultron/prompts/` (including `system.md`, `personality.md`, `reasoning.md`, `memory.md`, `developer.md`, and `safety.md`).
*   Architecture Decision Log ([`docs/DECISIONS.md`](file:///c:/Users/craft/Desktop/Ultron/docs/DECISIONS.md)) to record critical design records.
*   Project Vision Document ([`docs/VISION.md`](file:///c:/Users/craft/Desktop/Ultron/docs/VISION.md)) articulating project purpose and success criteria.
*   Scaffolding placeholders for future modules (`core/`, `planner/`, `memory/`, `automation/`, `vision/`, `permissions/`, `projects/`, `plugins/`) with individual architecture design `README.md` files.
*   Configurable user profile system enabling dynamic user names (e.g. `DISPLAY_NAME`) with graceful fallback.
*   Extensible, Strategy-pattern greeting engine supporting contextual parameters (Time of Day, Absence, Project, Holiday).

### Changed
*   Transitioned the codebase package from `friday/` to `ultron/`.
*   Refactored the voice assistant implementation ([`agent_ultron.py`](file:///c:/Users/craft/Desktop/Ultron/agent_ultron.py)) to remove legacy fictional character branding and implement the professional partner personality framework.
*   Updated MCP URI schema endpoints from `friday://info` to `ultron://info` ([`ultron/resources/data.py`](file:///c:/Users/craft/Desktop/Ultron/ultron/resources/data.py)).
*   Renamed build script references and CLI command mappings in [`pyproject.toml`](file:///c:/Users/craft/Desktop/Ultron/pyproject.toml) to support `ultron` and `ultron_voice`.
*   Swapped HTTP client request User-Agent strings to use `Ultron-AI/1.0` ([`ultron/tools/web.py`](file:///c:/Users/craft/Desktop/Ultron/ultron/tools/web.py)).

### Removed
*   Legacy hardcoded name strings ("Prem").
*   Fictional character personality requirements and combat assistant instructions.
