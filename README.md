# ULTRON — Cognitive Operating System

> *"Build a modular, local-first AI Operating System for developers that evolves over time without requiring large-scale rewrites."*

ULTRON is an intelligent cognitive engineering partner designed to assist software engineers with development, architecture, automation, planning, research, and project management. It runs as a local-first desktop application with offline speech processing, hardware abstraction, dynamic service management, and modular Model Context Protocol (MCP) support.

---

## Architecture Overview

```text
                                [Desktop GUI (PySide6)]
                                          │
    Microphone ──► Vosk / SAPI Speech ────┼────► EventBus ──► McpService (SSE: 8000)
                   Recognition Service    │       │
                                          ▼       ▼
    Speaker    ◄── pyttsx3 TTS Service ◄──┴── UME Memory (SQLite)
```

ULTRON is composed of cooperating layers:
*   **Desktop Runtime** (`python main.py`): A PySide6 desktop dashboard executing Power-On Self-Test (POST) boots, rendering radar/waveform visualizers, hosting local speech recognition (Vosk/SAPI), local text-to-speech (pyttsx3), an offline EventBus, and the SQLite-based UME Memory Engine.
*   **MCP Service** (`mcp/`): A first-class background service integrated with the EventBus and MemoryManager, exposing codebase inspection, git control, log access, and UME memory CRUD tools to external AI clients.
*   **Voice Agent** (`python agent_ultron.py`): A LiveKit voice pipeline wrapping offline models and cloud provider interfaces to collaborate with the local application via the MCP server.

---

## Project Structure

```text
ultron-agent-platform/
├── server.py              # Entry point to run the MCP server (delegates to mcp/server.py)
├── agent_ultron.py        # Entry point to run the LiveKit voice agent
├── pyproject.toml         # Build backend and command configurations
├── CHANGELOG.md           # Log of project changes and version updates
├── docs/
│   ├── COGNITIVE_CORE.md  # Cognitive Core pipeline stages
│   ├── DECISIONS.md       # Architecture Decision Log (ADR)
│   └── VISION.md          # Long-term vision and core values
│
├── mcp/                   # Modular Model Context Protocol package
│   ├── README.md          # Installation, tools, resources, security, and client configs
│   ├── server.py          # FastMCP server loading tools and resources dynamically
│   ├── service.py         # First-class UltronService wrapper running uvicorn SSE
│   ├── tools/             # Modular tools: fs, git, docs, runtime, memory
│   └── resources/         # Modular resources: db, docs, config, runtime
│
└── ultron/                # Core Cognitive OS Packages
    ├── core/              # Boot Manager, Service Manager, EventBus, State, AI Core, tasks
    ├── memory/            # SQLite-based UME (Ultron Memory Engine) domains
    ├── hal/               # Hardware Abstraction Layer permissions (microphone, speaker)
    └── voice/             # Voice system refactor: SAPI dictation, Vosk recognition, wake
```

---

## Quick Start (For Developers)

### 1. Prerequisites
*   Python &ge; 3.11 (tested on Python 3.11 to 3.14)
*   [`uv`](https://github.com/astral-sh/uv) (optional, standard Python environment and pip work out-of-the-box)
*   **Speech Recognition Model**: For offline Vosk recognition, place the downloaded Vosk model folder (e.g. `vosk-model-small-en-us-0.15`) inside a `models/` directory in the project root.

### 2. Setup
Clone the repository and install the dependencies:
```bash
git clone https://github.com/Prem79521/Ultron.git
cd Ultron
pip install -r requirements.txt  # Or use standard pip installer
```

### 3. Running the Services

You can run the MCP server standalone or load the full Desktop application dashboard.

#### Launching the Desktop OS Application (Recommended)
This runs the full PySide6 interface and registers the MCP server as a background service on port 8000:
- **Windows**: Run `run_ultron.bat` or `./run_ultron.ps1` in PowerShell.
- **Manual**: `python main.py`

#### Launching the standalone MCP Server
This runs only the MCP server without launching the PySide6 desktop dashboard:
- **Command**: `python server.py`
- Exposes Server-Sent Events (SSE) on port `8000`.

---

## Command Map

| Command | Target | Purpose |
| --- | --- | --- |
| `python main.py` | `main:main` | Boots the full PySide6 Desktop GUI and launches the background MCP service. |
| `python server.py` | `server:main` | Boots the standalone MCP SSE server on port 8000. |
| `python agent_ultron.py` | `agent_ultron:main` | Launches the LiveKit Voice pipeline agent which connects to the local MCP service. |

---

## License
MIT
