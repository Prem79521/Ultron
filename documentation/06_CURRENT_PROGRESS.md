# ULTRON Current Progress

This document lists the status of all codebase components.

---

## 1. What's Finished & Stable

The core OS layer is complete and fully integrated:
- **Event Bus**: Decoupled, thread-safe in-memory publish-subscribe hub.
- **Service Manager**: Governs lifecycle loops (Speech, Wake, recognition).
- **Boot Manager**: Sequential POST bootscreen with 12 validation steps.
- **State Manager**: Central state machine tracking: `Sleeping`, `Listening`, `Thinking`, `Executing`, `Speaking`, `Error`, and `Shutdown`.
- **Command Queue**: FIFO queue worker thread executing one directive at a time.
- **Memory Engine**: Domain tables configured in local SQLite engine (`ultron_memory.db`).
- **Permissions Wizard**: First-run checkbox overlay saving selections to database.
- **Diagnostics Grid**: Real-time tools display updated on a 1-second interval loop.
- **Settings Toggles**: Checkboxes that write permissions and start/stop voice services dynamically.

---

## 2. What's Partially Working

- **Built-in Skills**: Built-in actions (FileSystem, Browser, Terminal) exist but run stub actions. For example, Browser opens the desktop browser window, but doesn't capture web page contents yet.
- **Plugin Loader**: Scans the `plugins/` directory, checks manifests, and dynamically imports modules, but manifest schemas are still basic.

---

## 3. What's Under Development

- **Local LLM Providers**: Interfaces exist (`ultron/core/llm_manager.py`), but they are currently configured with mock completions. Integration with local engines (Ollama, ONNX) is planned.
- **Local Vision feeds**: The `VisionManager` exists, but camera captures are mocked.

---

## 4. What Should Never Be Modified

To preserve system stability, do not edit:
- **Core Event Bus interface (`event_bus.py`)**: All subsystems rely on this exact structure.
- **State Machine transitions (`state_manager.py`)**: Transitions are linked to voice and wake loops. Modifying them without matching events will break standby cycles.
- **COM Initialization bindings (`recognition.py`)**: Do not remove `pythoncom.CoInitialize()` and `PumpWaitingMessages()` as they are required for SAPI5 events on Windows.
