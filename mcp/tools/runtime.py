"""
MCP Runtime Tools — Expose and control the active ULTRON Cognitive OS runtime.
"""

import sys
import os
import psutil
import datetime
from typing import Dict, Any, List

def register(mcp):

    @mcp.tool()
    def get_runtime_state() -> Dict[str, Any]:
        """
        Get the current execution state of the ULTRON Cognitive OS.
        Includes service statuses, EventBus health, CPU/memory usage, and active voice session.
        """
        state = {}
        
        # 1. System Services Status
        try:
            from ultron.core.service_manager import service_manager
            services_info = []
            for name in service_manager.list_services():
                srv = service_manager.get_service(name)
                if srv:
                    services_info.append({
                        "name": name,
                        "status": srv.status(),
                        "health": srv.health(),
                        "active": srv.is_active(),
                        "uptime_seconds": round(srv.uptime(), 2) if hasattr(srv, "uptime") else 0,
                        "restarts": srv.restart_count() if hasattr(srv, "restart_count") else 0,
                        "last_failure": srv.last_failure() if hasattr(srv, "last_failure") else None
                    })
            state["services"] = services_info
        except Exception as exc:
            state["services"] = {"error": f"Failed to retrieve services: {exc}"}

        # 2. EventBus Health
        try:
            from ultron.core.event_bus import event_bus
            state["event_bus"] = event_bus.health()
            state["event_bus"]["total_history_count"] = len(event_bus.get_history())
        except Exception as exc:
            state["event_bus"] = {"error": str(exc)}

        # 3. Voice Session State
        try:
            from ultron.core.voice_session_manager import get_voice_session_manager
            mgr = get_voice_session_manager()
            if mgr:
                state["voice_session"] = {
                    "state": mgr.state.name,
                    "is_sleeping": mgr.state.name == "SLEEPING",
                    "is_listening": mgr.state.name == "LISTENING"
                }
            else:
                state["voice_session"] = {"state": "OFFLINE", "details": "VoiceSessionManager not instantiated"}
        except Exception as exc:
            state["voice_session"] = {"error": str(exc)}

        # 4. System Resources
        try:
            proc = psutil.Process(os.getpid())
            mem_info = proc.memory_info()
            state["system_resources"] = {
                "process_pid": os.getpid(),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "process_cpu_percent": proc.cpu_percent(),
                "process_memory_rss_mb": round(mem_info.rss / (1024 * 1024), 2),
                "system_memory_used_percent": psutil.virtual_memory().percent,
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as exc:
            state["system_resources"] = {"error": str(exc)}

        return state

    @mcp.tool()
    def get_event_logs(limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve the recent event logs/history from the EventBus."""
        try:
            from ultron.core.event_bus import event_bus
            history = event_bus.get_history()
            sliced = history[-limit:] if history else []
            formatted = []
            for item in sliced:
                formatted.append({
                    "event_type": item["event_type"],
                    "payload_preview": str(item["payload"])[:200] + "..." if len(str(item["payload"])) > 200 else item["payload"],
                    "timestamp": datetime.datetime.fromtimestamp(item["timestamp"]).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                })
            return formatted[::-1]  # Return newest first
        except Exception as exc:
            return [{"error": str(exc)}]

    @mcp.tool()
    def publish_system_event(event_type: str, payload: Dict[str, Any] = None) -> str:
        """
        Publish an event onto the ULTRON EventBus.
        Allows the MCP client to trigger system state changes or execute UI notifications.
        """
        try:
            from ultron.core.event_bus import event_bus
            event_bus.publish(event_type, payload or {})
            return f"Event '{event_type}' successfully published with payload: {payload}"
        except Exception as exc:
            return f"Failed to publish event: {exc}"

    @mcp.tool()
    def control_service(service_name: str, action: str) -> str:
        """
        Control the lifecycle of a system service.
        Action must be one of: 'start', 'stop', 'restart'.
        """
        if action not in ["start", "stop", "restart"]:
            return f"Invalid action '{action}'. Must be 'start', 'stop', or 'restart'."
            
        try:
            from ultron.core.service_manager import service_manager
            srv = service_manager.get_service(service_name)
            if not srv:
                return f"Service '{service_name}' not found."
                
            if action == "start":
                success = service_manager.start_service(service_name)
            elif action == "stop":
                success = service_manager.stop_service(service_name)
            elif action == "restart":
                success = service_manager.restart_service(service_name)
                
            return f"Action '{action}' on service '{service_name}': {'SUCCESS' if success else 'FAILED or BLOCKED'} (Current Status: {srv.status()})"
        except Exception as exc:
            return f"Error executing service control action: {exc}"
