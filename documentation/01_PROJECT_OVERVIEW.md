# ULTRON Project Overview

## 1. What is ULTRON?
ULTRON is an offline-first Cognitive Desktop Operating System layer and assistant. It sits on top of standard native operating systems (Windows) and provides a unified intelligence layer. Unlike cloud-dependent AI assistants, ULTRON prioritizes native performance, local data privacy, and direct OS-level execution.

## 2. Long-term Vision
The ultimate vision for ULTRON is to serve as a complete **Cognitive Operating System**. Instead of users managing files, applications, and pipelines manually, ULTRON acts as an agentic controller. It manages developers' projects, automates complex system tasks, and executes local deep-learning inference pipelines on consumer hardware without external network requirements.

## 3. Current Development Phase
We are currently in **Phase 4.6 (Master Architectural Refinement and Future-proofing)**. 
During this phase, we transitioned ULTRON from a collection of scripts into a service-oriented architecture:
- Standardized state machine lifecycle.
- Isolated backend services from the PySide6 UI event loop.
- Integrated offline voice loops (SAPI5 listener + pyttsx3 text-to-speech) under strict hardware permission guards.
- Consolidated memory domains using a local SQLite storage model.

## 4. Design Philosophy
- **Local-First**: All data, configurations, and logs remain locally on the user's desktop. Zero data leaves the machine unless cloud sync is explicitly added as an opt-in client extension.
- **Service Decoupling**: Subsystems register as modular services governed by a service manager. They communicate exclusively via a central event bus to prevent tight coupling.
- **Hardware Agnosticism**: Standard adapters wrap native system calls (COM, audio devices), allowing simple cross-platform porting in the future.

## 5. Technology Stack
- **Programming Language**: Python (v3.10+)
- **Presentation Layer**: PySide6 (Qt for Python)
- **Local Storage Engine**: SQLite3
- **Audio Output (TTS)**: pyttsx3 (SAPI5 native SAPI.SpVoice engine on Windows)
- **Audio Input (STT)**: pywin32 (SAPI5 native SAPI.SpSharedRecoContext engine on Windows)
- **IPC & COM Integration**: pywin32, pythoncom

## 6. Folder Structure
```
c:\Users\craft\Desktop\Ultron\
├── assets/                  # App icon, themes, and graphics
│   └── icons/
│       └── ultron.ico       # Native application window icon
├── config/                  # Subsystem configuration files
│   ├── general.json
│   ├── memory.json
│   ├── skills.json
│   ├── ui.json
│   └── voice.json
├── documentation/           # System design docs and timelines
├── plugins/                 # Extensible manifests and custom classes
├── scratch/                 # Integration tests and scripts
├── ui/                      # PySide6 Qt GUI Desktop Layer
│   ├── application.py       # QApplication bootstrap
│   ├── boot_screen.py       # POST sequence screen
│   ├── main_window.py       # Main dashboard layout
│   ├── permission_dialog.py # First-run permission prompt
│   ├── security_dialogs.py  # User action consent prompt
│   ├── themes.py            # Styled palette sheets
│   └── waveform.py          # State-linked wave renderer
├── ultron/                  # Cognitive OS Backend Package
│   ├── api/                 # Decoupled service endpoints
│   ├── core/                # System kernels (State, Service, Bus)
│   ├── hal/                 # Hardware Abstraction adapters
│   ├── memory/              # SQLite database domain tables
│   ├── security/            # Consent and authorization managers
│   ├── skills/              # Cognitive action registries
│   └── voice/               # Speech listeners and synthesis providers
├── main.py                  # System main startup script
└── ultron_memory.db         # Local storage SQLite database
```

## 7. Coding Standards
- **Thread Safety**: Core background operations run in isolated python worker threads. Any UI widget modifications must be scheduled on the main event thread via `QTimer.singleShot(0, callback)`.
- **Interface Segregation**: Every background service must inherit from the `UltronService` base class and support unified `start()`, `stop()`, and `health()` lifecycles.
- **Event Bus Decoupling**: Modules should subscribe to events rather than direct calls. For example, rather than calling the radar widget directly, the widget subscribes to `"STATE_CHANGED"`.
