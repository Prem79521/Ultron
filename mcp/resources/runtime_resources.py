"""
MCP Runtime Resources — Exposes live service states and EventBus history.
"""

import os
import psutil
import datetime
from typing import Dict, Any

def register(mcp):

    @mcp.resource("ultron://runtime/state")
    def runtime_state_resource() -> str:
        """Returns the current execution state of the Cognitive OS in markdown format."""
        report = ["# ULTRON Cognitive OS Runtime State\n"]
        
        # 1. Services
        report.append("## Active Subsystem Services")
        try:
            from ultron.core.service_manager import service_manager
            report.append("| Service Name | Status | Health | Active | Uptime | Restarts |")
            report.append("| --- | --- | --- | --- | --- | --- |")
            for name in service_manager.list_services():
                srv = service_manager.get_service(name)
                if srv:
                    uptime_str = f"{srv.uptime():.1f}s" if hasattr(srv, "uptime") else "-"
                    restarts = srv.restart_count() if hasattr(srv, "restart_count") else 0
                    report.append(f"| {name} | {srv.status()} | {srv.health()} | {srv.is_active()} | {uptime_str} | {restarts} |")
        except Exception as exc:
            report.append(f"Failed to query services: {exc}")
            
        report.append("")
        
        # 2. EventBus
        report.append("## Event Messaging Bus")
        try:
            from ultron.core.event_bus import event_bus
            health = event_bus.health()
            report.append(f"- **Status**: {health.get('status')}")
            report.append(f"- **Detail**: {health.get('details')}")
            report.append(f"- **Total History Log**: {len(event_bus.get_history())} events")
        except Exception as exc:
            report.append(f"Failed to query EventBus: {exc}")
            
        report.append("")
        
        # 3. System Resources
        report.append("## System Resources")
        try:
            proc = psutil.Process(os.getpid())
            mem_info = proc.memory_info()
            report.append(f"- **Process ID (PID)**: {os.getpid()}")
            report.append(f"- **CPU Usage (Process / System)**: {proc.cpu_percent()}% / {psutil.cpu_percent()}%")
            report.append(f"- **Memory Usage (RSS)**: {mem_info.rss / (1024 * 1024):.2f} MB")
            report.append(f"- **System Memory Usage**: {psutil.virtual_memory().percent}%")
            report.append(f"- **Diagnostic Time**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as exc:
            report.append(f"Failed to query system resources: {exc}")
            
        return "\n".join(report)

    @mcp.resource("ultron://runtime/events")
    def runtime_events_resource() -> str:
        """Returns the last 50 events captured on the EventBus in markdown list format."""
        report = ["# ULTRON Event Bus History (Last 50 events)\n"]
        try:
            from ultron.core.event_bus import event_bus
            history = event_bus.get_history()
            if not history:
                return "# ULTRON Event Bus History\n\nNo events recorded yet."
                
            sliced = history[-50:]
            for idx, item in enumerate(reversed(sliced), 1):
                ts = datetime.datetime.fromtimestamp(item["timestamp"]).strftime("%H:%M:%S.%f")[:-3]
                payload_str = str(item["payload"])
                if len(payload_str) > 150:
                    payload_str = payload_str[:147] + "..."
                report.append(f"{idx}. `[{ts}]` **{item['event_type']}** — Payload: `{payload_str}`")
        except Exception as exc:
            report.append(f"Error querying EventBus history: {exc}")
            
        return "\n".join(report)
