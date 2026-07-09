# ULTRON API Reference

This document catalogs public classes and signatures for the ULTRON Cognitive OS.

---

## 1. Core OS Layer

### `StateManager` (Singleton)
Manages the central system state machine.
- **Methods**:
  - `state` (property) -> `str`: Returns current state.
  - `set_state(state: str)`: Transitions system state. Raises `ValueError` if the state is invalid. Publishes `"STATE_CHANGED"`.

### `UltronServiceManager` (Singleton)
Coordinates background service loops.
- **Methods**:
  - `register_service(name: str, service: UltronService)`: Adds service to registry.
  - `get_service(name: str) -> Optional[UltronService]`: Queries registered service.
  - `start_service(name: str) -> bool`: Starts the service thread.
  - `stop_service(name: str) -> bool`: Stops the service thread.
  - `start_all()`: Starts all registered services.
  - `stop_all()`: Gracefully stops all registered services.

### `UltronService` (Base Class)
Abstract interface defining background service behaviors.
- **Methods**:
  - `start() -> bool`: Initializes service thread. Must return `True` on success.
  - `stop() -> bool`: Stops the service.
  - `health() -> str`: Returns status string (e.g. `"Running"`, `"Offline"`).

---

## 2. Hardware Abstraction Layer

### `UltronHALManager`
Validates hardware device permissions and connectivity states.
- **Methods**:
  - `check_devices() -> Dict[str, bool]`: Queries mic, speaker, and camera presence.
  - `is_allowed(device: str) -> bool`: Reads authorizations from database.
  - `save_permission(device: str, allowed: bool)`: Writes permission choices to database.

---

## 3. Cognitive Core Layer

### `UltronAICore`
Orchestrates prompt planners, command queues, and TTS outputs.
- **Methods**:
  - `execute_command(command_text: str)`: Pushes commands to FIFO queue worker.

### `UltronCommandQueue`
Sequential queue worker loop.
- **Methods**:
  - `enqueue(item: str)`: Adds item to processing queue.
  - `start()`: Launches worker processing thread.
  - `stop()`: Halts worker processing thread.

---

## 4. Voice Subsystems

### `SapiSpeechListener` (Inherits `UltronService`)
Listens for voice wake words and commands.
- **Methods**:
  - `start() -> bool`: Checks permissions and launches SAPI5 listener.
  - `stop() -> bool`: Halts loop.
  - `health() -> str`: Returns `"Running"` or `"Error"`.

### `Pyttsx3VoiceProvider` (Inherits `UltronService`)
Text-to-speech feedback synthesis engine.
- **Methods**:
  - `speak(text: str)`: Asynchronously runs TTS voice synthesizer in a background thread.
