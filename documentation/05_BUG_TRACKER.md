# ULTRON Bug Tracker

This document tracks bugs found during development, testing, and runtime integration phases.

---

## Resolved Integration Bugs (v1.0 Release Cycle)

### Bug ID: BUG-01
- **Title**: SAPI5 thread import binding reference error
- **Description**: Accessing `hal_manager` or `wake_engine` imported globally at the module level resolved to `None` since they were initialized after the imports completed.
- **Severity**: Critical (crashed MainWindow initialization).
- **Files Involved**:
  - `ui/main_window.py`
  - `ui/application.py`
  - `ultron/voice/recognition.py`
- **Root Cause**: Python's module-level binding behavior does not automatically refresh variable references assigned *after* the import statements are run.
- **Resolution**: Implemented dynamic getter accessors (`get_hal_manager()`, `get_wake_engine()`, `get_ai_core()`) inside core managers to resolve references dynamically.
- **Status**: Resolved.

### Bug ID: BUG-02
- **Title**: Skill Registry attribute crash in live diagnostics
- **Description**: Main window threw `AttributeError: 'UltronMainWindow' object has no attribute 'skills'` when refreshing the diagnostics display.
- **Severity**: High (caused diagnostics loop to crash).
- **Files Involved**:
  - `ui/main_window.py`
- **Root Cause**: `self.skills` was never assigned to `UltronMainWindow` during instantiation.
- **Resolution**: Refactored the diagnostics generator to resolve the registry via the core module registry: `self.core.get_module("skills_registry")`.
- **Status**: Resolved.

### Bug ID: BUG-03
- **Title**: Standby speech wakes up State Manager
- **Description**: Speaking the standby notice ("Returning to standby.") caused the state to transition back to `Listening` because the voice stop event listener unconditionally mapped `VoiceStopped` to `Listening`.
- **Severity**: High (blocked the sleep cycle timeout).
- **Files Involved**:
  - `ultron/core/state_manager.py`
- **Root Cause**: Lacked guard checks in voice start/stop listeners to recognize when the system had transitioned to `Sleeping`.
- **Resolution**: Added condition checks inside the state manager:
  - Only transition to `Speaking` if current state is not `Sleeping`.
  - Only transition to `Listening` if current state is `Speaking`.
- **Status**: Resolved.

---

## Known Limitations / Open Items

### Bug ID: BUG-04
- **Title**: SAPI5 voice engine is Windows-only
- **Description**: Running ULTRON on macOS or Linux will cause COM dispatch calls to fail.
- **Severity**: Medium (blocking cross-platform portability).
- **Files Involved**:
  - `ultron/voice/recognition.py`
  - `ultron/voice/__init__.py`
- **Possible Cause**: SAPI5 is a Microsoft SAPI component.
- **Status**: Unresolved / Open. (Treated as an expected platform limitation. Stubs or OS checks will be added in a future roadmap phase).
