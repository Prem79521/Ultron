# ULTRON Developer Guide

Welcome to the ULTRON developer documentation. This document covers contribution workflows, coding conventions, and architectural guidelines.

---

## 1. Core Architecture Principles
- **No Direct Coupling**: Subsystems must not import or instantiate other subsystems directly. Use the central Event Bus for communication.
- **Service-Oriented Design**: Background tasks must run inside lifecycle-governed loops (subclassing `UltronService`) and register with the Service Manager.
- **Thread Safety**: Never modify PySide6 widgets from a background thread. Schedule updates on the main thread via `QTimer.singleShot(0, callback)`.

---

## 2. Coding Conventions
- **Code Style**: Follow PEP8.
- **File Imports**: Do not import global references (like `hal_manager` or `wake_engine`) directly at the module level. Use getter functions (e.g. `get_hal_manager()`) inside methods to avoid import reference bugs.

---

## 3. How to Add a New Skill
1. Create your skill class inheriting from `UltronSkill` in a plugin entry folder or inside `ultron/skills/`.
2. Implement:
   - `execute(self, params: Dict[str, Any]) -> Dict[str, Any]`
   - `health(self) -> dict`
3. Register your skill class inside the registry:
   ```python
   skills.register_skill("MySkillName", MySkillClass(core, memory))
   ```

---

## 4. How to Create a Custom Plugin
1. Create a subdirectory under `/plugins/` (e.g. `plugins/my_plugin/`).
2. Add a `manifest.json`:
   ```json
   {
       "name": "My Custom Plugin",
       "version": "1.0.0",
       "entry_point": "plugin.py",
       "description": "Custom extensions."
   }
   ```
3. Implement a `register_plugin` callback inside `plugin.py` to add your custom skills to the registry automatically.
