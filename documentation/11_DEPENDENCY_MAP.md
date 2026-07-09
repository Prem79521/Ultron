# ULTRON Dependency Map

This document lists the dependencies between ULTRON modules.

---

## 1. System Module Dependency Graph

```mermaid
graph TD
    main.py --> UI_App[ui/application.py]
    main.py --> CoreSystem[ultron/core/__init__.py]
    main.py --> MemoryManager[ultron/memory/__init__.py]
    main.py --> SkillRegistry[ultron/skills/registry.py]
    main.py --> TTS[ultron/voice/__init__.py]
    
    UI_App --> MainWindow[ui/main_window.py]
    MainWindow --> HAL[ultron/hal/hal_manager.py]
    MainWindow --> ServiceManager[ultron/core/service_manager.py]
    
    AICore[ultron/core/ai_core.py] --> Queue[ultron/core/command_queue.py]
    AICore --> Dispatcher[ultron/skills/command_dispatcher.py]
    
    Listener[ultron/voice/recognition.py] --> HAL
    TTS --> HAL
```

---

## 2. Dependency Analysis

### Tight Coupling Identification
- **HAL Dependency**: Subsystems (Microphone, Speaker, Recognition, settings widgets) query hardware authorization status directly from the HAL manager.
- **Solution**: Decoupled using dynamic accessors (`get_hal_manager()`), preventing circular import errors at startup.

---

## 3. Future Improvements
- **IPC Event Routing**: For future multi-process scaling, replace in-memory Event Bus lists with local network sockets or named pipes.
- **Dynamic Skill Loading**: Decouple dispatcher checks from specific class imports, allowing the Skill Registry to resolve task execution dynamically using plugins.
