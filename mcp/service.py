"""
ULTRON McpService — First-class Cognitive OS service wrapping the MCP server.
"""

import threading
import logging
import time
import os
import sys
from typing import Optional
from ultron.core.service_manager import UltronService

# Adjust sys.path immediately to prevent local 'mcp' folder from masking the installed 'mcp' library
mcp_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(mcp_dir)
if mcp_dir not in sys.path:
    sys.path.insert(0, mcp_dir)
sys.path = [p for p in sys.path if p != root_dir]

class McpService(UltronService):
    """Lifecycle service hosting the Model Context Protocol (MCP) server asynchronously."""
    
    def __init__(self):
        super().__init__("McpService")
        self.dependencies = []  # No strict boot dependencies, runs independently
        self.server_thread: Optional[threading.Thread] = None
        self.uvicorn_server = None
        self.mcp = None
        self._recent_events = []
        self._recent_events_lock = threading.Lock()
        self.logger = logging.getLogger("ultron-agent")

    def initialize(self):
        """Prepares the FastMCP instance and registers all tools/resources."""
        if self._lifecycle_stage == "initialized":
            return True
            
        super().initialize()
        
        try:
            # Import FastMCP now that sys.path is adjusted
            from mcp.server.fastmcp import FastMCP
            import server as mcp_server_module
            
            # Instantiate FastMCP server
            self.mcp = FastMCP(
                name="ULTRON-Cognitive-OS",
                instructions=(
                    "You are ULTRON, a cognitive intelligence platform. Use these tools "
                    "to inspect the codebase, git, logs, runtime services, EventBus, and UME memory."
                ),
            )
            
            # Dynamically register all modular tools and resources
            mcp_server_module.register_all_modules(self.mcp)
            
            # Hook into event bus to track live events
            self.subscribe_event("VOICE_STATE_CHANGED", self._on_system_event)
            self.subscribe_event("COMMAND_RECEIVED", self._on_system_event)
            self.subscribe_event("COMMAND_COMPLETED", self._on_system_event)
            self.subscribe_event("SERVICE_STARTED", self._on_system_event)
            self.subscribe_event("SERVICE_STOPPED", self._on_system_event)
            self.subscribe_event("APPLICATION_READY", self._on_system_event)
            self.subscribe_event("ERROR_OCCURRED", self._on_system_event)
            
            self.logger.info("McpService initialized: FastMCP server & EventBus subscribers configured.")
            return True
        except Exception as exc:
            self.record_failure(str(exc))
            self.logger.error(f"Failed to initialize McpService: {exc}", exc_info=True)
            return False

    def _on_system_event(self, event):
        """Callback to capture EventBus events in memory for resource tracking."""
        with self._recent_events_lock:
            self._recent_events.append({
                "event_type": event.event_type,
                "payload": event.payload,
                "timestamp": event.timestamp
            })
            if len(self._recent_events) > 100:
                self._recent_events.pop(0)

    def start(self) -> bool:
        """Launches the MCP server in a background thread running uvicorn SSE transport."""
        if not self.mcp:
            self.initialize()
            if not self.mcp:
                return False
                
        if self.is_active():
            return True
            
        import uvicorn
        
        # Starlette app is exposed on FastMCP via the 'sse_app()' method
        asgi_app = self.mcp.sse_app()
        port = int(os.environ.get("ULTRON_MCP_PORT", 8000))
        
        # Configure uvicorn server in a non-blocking configuration
        config = uvicorn.Config(
            app=asgi_app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            loop="asyncio"
        )
        self.uvicorn_server = uvicorn.Server(config)
        
        def _run():
            try:
                self.logger.info(f"McpService Thread: Starting uvicorn SSE server on port {port}...")
                self.uvicorn_server.run()
            except Exception as e:
                self.logger.error(f"McpService Server thread crashed: {e}", exc_info=True)
                self.record_failure(str(e))
                self.active = False
                self._lifecycle_stage = "error"
                
        self.server_thread = threading.Thread(
            target=_run,
            name="UltronMcpServerThread",
            daemon=True
        )
        
        # Call base start to mark active
        if super().start():
            self.server_thread.start()
            
            # Emit starting event
            from ultron.core.event_bus import event_bus
            event_bus.publish("MCP_SERVER_STARTED", {"port": port})
            return True
            
        return False

    def stop(self) -> bool:
        """Shuts down the background uvicorn server and cleans up threads."""
        self.logger.info("Stopping McpService...")
        
        if self.uvicorn_server:
            # Tell uvicorn to exit gracefully
            self.uvicorn_server.should_exit = True
            
        super().stop()
        
        # Emit stopped event
        from ultron.core.event_bus import event_bus
        event_bus.publish("MCP_SERVER_STOPPED", {})
        
        return True

    def get_recent_events(self) -> list:
        """Returns the list of recent EventBus events recorded by the service."""
        with self._recent_events_lock:
            return list(self._recent_events)
