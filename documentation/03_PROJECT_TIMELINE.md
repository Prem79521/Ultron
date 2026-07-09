# ULTRON Project Timeline

This document outlines the development phases, milestone objectives, work completed, and engineering lessons learned during the construction of ULTRON.

---

## Phase 1 — Verification & Basic Startup (Master Verification Mode)
- **Objectives**: Validate Python, PySide6, and audio dependencies. Confirm core entry-point scripts exist.
- **Completed Work**:
  - Validated module layout structures.
  - Setup core database files (`ultron_memory.db`).
- **Lessons Learned**: Initial setups had module importing discrepancies. Standard python path imports must be managed cleanly using virtual environments.

---

## Phase 2 — Runtime Debugging (UI Stabilization)
- **Objectives**: Diagnose why UI windows failed to display, solve coordinate/focus glitches, and capture all stdout/stderr channels.
- **Completed Work**:
  - Re-anchored window coordinates.
  - Removed focus overrides that hid the windows off-screen.
  - Integrated PySide6 thread logging to capture standard outputs safely.
- **Lessons Learned**: Direct updates to PySide6 widgets from background threads cause runtime lockups on Windows. All UI modifications must run on the Qt main event loop via single-shot timers or signals.

---

## Phase 3 — Desktop Shortcut & Custom Assets
- **Objectives**: Create native Windows shortcuts, bat files, and custom minimal red/black geometric icons.
- **Completed Work**:
  - Generated desktop shortcuts targeting `python main.py` using pywin32 shell libraries.
  - Designed premium Matte Black and Scarlet geometric icons.
- **Lessons Learned**: Paths must always be absolute when generating desktop shortcuts. Target working directories must match the project root folder.

---

## Phase 4 — Wake Engine & Hardware permissions
- **Objectives**: Connect the offline voice loop, SAPI5 listener, permissions prompt dialog, and inactivity standbys.
- **Completed Work**:
  - Implemented the SAPI5 speech listener thread.
  - Created the checkboxes permissions wizard.
  - Standardized the Sleeping state wake triggers.
- **Lessons Learned**: SAPI5 COM context requires thread initialization using `pythoncom.CoInitialize()`.

---

## Phase 4.5 — Stabilization & Bug Elimination
- **Objectives**: Eliminate imports redundancy, resolve pyttsx3 conflicts on Windows threads, and remove placeholder mock codes.
- **Completed Work**:
  - Refactored voice provider with thread locks.
  - Fixed database write locks.
- **Lessons Learned**: SQLite writes in multiple threads require database file serialization or thread-safe database connections.

---

## Phase 4.6 — Service-Oriented Architecture (Current Phase)
- **Objectives**: Decouple components into a professional Cognitive OS architecture. Implement Service Manager, State Manager singletons, and Event Bus.
- **Completed Work**:
  - Created StateManager, ServiceManager, HealthMonitor, and CommandQueue.
  - Decoupled widgets via Event Bus subscriptions.
  - Added live Diagnostics and Settings toggles.
- **Lessons Learned**: Python module-level variable imports suffer from reference bindings issues. Exporting getter functions (e.g. `get_hal_manager()`) ensures reference accuracy.
