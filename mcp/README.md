# ULTRON Model Context Protocol (MCP) Server

The ULTRON MCP Server integrates first-class Model Context Protocol support into the ULTRON Cognitive OS. It enables standard-compliant MCP AI clients (e.g. Cursor, Claude Desktop, or the built-in LiveKit Voice Agent) to inspect, reason about, and control the ULTRON repository, runtime services, EventBus registry, and memory database.

---

## Architecture Overview

The MCP layer is integrated as a native, first-class `UltronService` within the OS service loop. It utilizes a Server-Sent Events (SSE) server running on a background thread.

```text
  [MCP Client (Claude/Cursor)]
              │
              ▼ (SSE connection: port 8000)
       [McpService] (First-class UltronService)
        ├── Dynamic Auto-Loader (loads mcp/tools/* & mcp/resources/*)
        ├── EventBus Subscriber (monitors live system messages)
        └── Fallback Memory Manager (resolves database without GUI)
```

---

## Exposed Features

### 1. Filesystem & Code Analysis Tools
- `list_directory(path)`: List directory files and folders safely within the workspace.
- `read_file(path, start_line, end_line)`: Read file contents securely.
- `grep_search(query, path)`: Run high-performance searches using native `git grep`.
- `symbol_search(query)`: Extract Python classes, functions, and method signatures using Python's standard `ast` compiler.

### 2. Git Version Control Tools
- `git_status()`: Get active working directory changes.
- `git_diff()`: Get active unstaged code diffs.
- `git_log(limit)`: Check git history.
- `get_repo_metadata()`: Retrieve branch names, commit hashes, messages, and remote URL locations.

### 3. Documentation & Configurations
- `list_documentation()`: Lists documents in `docs/` and `documentation/`.
- `read_documentation(filename)`: Reads a specific documentation page.
- `read_logs(lines)`: Returns tail lines of `ultron.log`.
- `get_project_config()`: Exposes configurations (`voice.json`, `.env`) with redacted sensitive API keys and secrets.

### 4. Cognitive OS Runtime Control
- `get_runtime_state()`: Exposes active service status, EventBus health metrics, memory usage, and voice session states.
- `get_event_logs(limit)`: Exposes EventBus history.
- `publish_system_event(event_type, payload)`: Publishes an event to the EventBus, allowing the AI client to trigger voice notices or UI updates.
- `control_service(service_name, action)`: Starts, stops, or restarts specific Cognitive OS modules.

### 5. Domain-Specific Memory Tools (UME)
- `get_valid_memory_types()`: List valid memory stores.
- `list_memory_records(memory_type, limit)`: Fetch records from UME domains (`project`, `preference`, `knowledge`, `conversation`, `permission`).
- `search_memories(query, related_project)`: Search database records ranked by importance score.
- `create_memory_record(memory_type, title, content, ...)`: Insert new memory entries.
- `update_memory_record(memory_type, id, updates)`: Update memory entries.
- `delete_memory_record(memory_type, id)`: Remove memory entries.

---

## Exposed Resources

The server registers these resources under standard URI schemas:
- **SQLite Database**:
  - `sqlite://ultron_memory.db/schema` — Exposes schema specifications of all tables.
  - `sqlite://ultron_memory.db/{table_name}` — Exposes records inside a table (read-only, whitelisted tables).
- **Workspace Documentation**:
  - `docs://list` — Directory registry of markdown pages.
  - `docs://{filename}` — Exposes specific documentation page content.
- **Configurations**:
  - `config://voice.json` — Voice settings (sanitized).
  - `config://env` — Environment settings (sanitized).
- **Runtime Diagnostics**:
  - `ultron://runtime/state` — Live markdown diagnostic dashboard of all services.
  - `ultron://runtime/events` — Live EventBus history.

---

## Installation & Running

The server requires `fastmcp`, `uvicorn`, and `psutil`.

### 1. Running inside the Desktop Application (Service Mode)
By default, when starting ULTRON via `python main.py` or the PowerShell script, `McpService` will launch automatically. It starts an SSE server on port `8000` (or `ULTRON_MCP_PORT` env setting).

### 2. Running Standalone (CLI Mode)
To run the server independently:
```bash
python mcp/server.py
```
This boots FastMCP over SSE at `http://127.0.0.1:8000/sse`.

---

## Extensibility: Adding Tools and Resources

The MCP server is designed to be extensible from day one. You do not need to register tools manually.

1. **Add Tools**: Create a `.py` file under `mcp/tools/` (e.g. `mcp/tools/custom.py`). Define a `register(mcp)` function:
   ```python
   def register(mcp):
       @mcp.tool()
       def custom_tool(arg: str) -> str:
           """Describe the tool here."""
           return f"Result: {arg}"
   ```
2. **Add Resources**: Create a `.py` file under `mcp/resources/` (e.g. `mcp/resources/custom.py`). Define a `register(mcp)` function:
   ```python
   def register(mcp):
       @mcp.resource("custom://info")
       def custom_info() -> str:
           """Describe the resource here."""
           return "Resource Content"
   ```

At startup, the dynamic auto-loader scans the directories, imports all packages, and registers them onto the FastMCP server.

---

## Client Configurations

To connect external tools, add the following configuration:

### Claude Desktop Configuration
Add this to your `claude_desktop_config.json` (located at `%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "ultron-cognitive-os": {
      "command": "python",
      "args": ["c:/Users/craft/Desktop/Ultron/mcp/server.py"]
    }
  }
}
```

### Cursor Configuration
1. Go to **Settings** -> **Features** -> **MCP**.
2. Click **+ Add New MCP Server**.
3. Fill details:
   - **Name**: `ultron`
   - **Type**: `command`
   - **Command**: `python c:/Users/craft/Desktop/Ultron/mcp/server.py`
