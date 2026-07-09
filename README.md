# ULTRON — Cognitive Agent Platform

> *"Build a modular, local-first AI Operating System for developers that evolves over time without requiring large-scale rewrites."*

ULTRON is an intelligent cognitive engineering partner designed to assist software engineers with development, architecture, automation, planning, research, and project management.

---

## Architecture Overview

```text
Microphone ──► STT (Sarvam Saaras v3)
                    │
                    ▼
              LLM (Gemini 2.5 Flash)  ◄──────► MCP Server (FastMCP / SSE)
                    │                              ├─ get_world_news
                    ▼                              ├─ open_world_monitor
              TTS (OpenAI nova)                    ├─ search_web
                    │                              └─ …more tools
                    ▼
              Speaker / LiveKit room
```

ULTRON is split into two cooperating services:
*   **MCP Server** (`uv run ultron`): A [FastMCP](https://github.com/jlowin/fastmcp) server hosting system utilities, web feed scraper tools, and dynamic resources over Server-Sent Events (SSE).
*   **Voice Agent** (`uv run ultron_voice`): A [LiveKit Agents](https://github.com/livekit/agents) voice pipeline coordinating the STT, LLM, and TTS models, querying the MCP server, and enforcing behavioral protocols in real time.

---

## Project Structure

```text
ultron-agent-platform/
├── server.py              # Entry point to run the FastMCP SSE server
├── agent_ultron.py        # Entry point to run the LiveKit voice agent
├── pyproject.toml         # Build backend and command configurations
├── CHANGELOG.md           # Log of project changes and version updates
├── docs/
│   ├── DECISIONS.md       # Architecture Decision Log (ADR)
│   └── VISION.md          # Long-term vision and core values
│
└── ultron/                # Core Package
    ├── config.py          # Configuration manager and user profile identity
    ├── tools/             # Stateless MCP tool definitions (web, system, utils)
    ├── resources/         # Exposes static or dynamic resources (ultron://info)
    │
    ├── prompts/           # Modular prompt Markdown files:
    │   ├── system.md      # Structural directives
    │   ├── personality.md # Strategic, dry-humored, peer personality
    │   ├── reasoning.md   # Logic loop and verification rules
    │   ├── memory.md      # Directives on context scopes
    │   ├── developer.md   # Clean coding guidelines
    │   └── safety.md      # Permission boundaries (Safe, Warning, Critical)
    │
    # --- Future Placeholder Modules ---
    ├── core/              # Global state and event router
    ├── planner/           # Task deconstructor and scheduler
    ├── memory/            # Split memory namespaces (conversation, projects, etc.)
    ├── automation/        # sub-processes and shell execution hooks
    ├── vision/            # Frame capture and UI element analysis
    ├── permissions/       # Safe, Warning, and Critical security gates
    ├── projects/          # Workspace awareness metadata
    └── plugins/           # Integrations registry (GitHub, Discord, Spotify)
```

---

## Quick Start (For Developers)

### 1. Prerequisites
*   Python ≥ 3.11
*   [`uv`](https://github.com/astral-sh/uv) (or pip/python environments)
*   A [LiveKit Cloud](https://cloud.livekit.io) project credentials

### 2. Setup
```bash
git clone https://github.com/SAGAR-TAMANG/friday-tony-stark-demo.git
cd friday-tony-stark-demo
# Install dependencies
pip install -e .
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in the keys:
```bash
cp .env.example .env
```
Add `DISPLAY_NAME=Prem` inside your `.env` to configure your User Identity System display name.

### 4. Running the Services

**Terminal 1 — MCP server** (start first)
```bash
uv run ultron
```

**Terminal 2 — Voice agent**
```bash
uv run ultron_voice
```
This joins the LiveKit room. Open the [LiveKit Agents Playground](https://agents-playground.livekit.io) and connect to your room.

---

## Command Map

| Command | Target | Purpose |
| --- | --- | --- |
| `uv run ultron` | `server:main` | Boots FastMCP SSE server on port 8000. |
| `uv run ultron_voice` | `agent_ultron:dev` | Launches LiveKit Voice Pipeline incorporating ULTRON's prompts and personality. |

---

## License
MIT

# Ultron
