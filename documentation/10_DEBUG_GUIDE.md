# ULTRON Debugging Guide

This guide describes how to debug the core subsystems of the ULTRON Cognitive OS.

---

## 1. Debugging SAPI5 Speech Recognition
- **Symptom**: System does not respond to voice commands.
- **Verification Steps**:
  1. Open the **Settings** panel and check if **Enable Microphone Input** is selected.
  2. Open the **Tools** panel and verify if the `Voice Recognition` service is listed as `"Running"`.
  3. If listed as `"Error"`, SAPI5 was unable to initialize the COM interface. Check if Windows Speech Recognition is enabled on your machine.
  4. Ensure `pythoncom.CoInitialize()` is called inside the listener thread before accessing COM objects.

---

## 2. Debugging state transitions
- **Symptom**: Animations are frozen or state-loops are locked.
- **Verification Steps**:
  1. Toggle the Developer Console (`Ctrl+Shift+D`) to watch `"STATE_CHANGED"` logs.
  2. Ensure background threads do not modify UI widgets directly. All visual updates must run via `QTimer.singleShot(0, callback)`.
  3. Verify that TTS completion publishes `"VoiceStopped"` to transition the state back to `"Listening"`.

---

## 3. Debugging Service Lifecycles
- **Symptom**: Service watchdog attempts restarts endlessly.
- **Verification Steps**:
  1. Open the log files or Developer Console to find `"Watchdog audited service... STATUS: Degraded"` warning logs.
  2. If a service crashes continuously (e.g. 3 attempts), the Health Monitor stops it. Investigate whether the SAPI5 audio device was disconnected.

---

## 4. Debugging memory databases
- **Symptom**: Settings or projects do not persist upon restart.
- **Verification Steps**:
  1. Run `sqlite3 ultron_memory.db` from terminal to verify tables exist.
  2. Ensure write calls catch database locks and serialize executions to prevent SQLITE_BUSY crashes.
