"""
ULTRON Session Manager — Handles session lifecycle, current active projects, and clean shutdown hooks.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

class SessionManager:
    def __init__(self):
        self.session_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.active_project: Optional[str] = None
        self.is_active: bool = False
        self._event_bus = None

    def initialize_session(self, event_bus=None) -> str:
        self._event_bus = event_bus
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.utcnow()
        self.is_active = True
        
        if self._event_bus:
            self._event_bus.publish("ApplicationStarted", {"session_id": self.session_id})
            
        return self.session_id

    def set_active_project(self, project_name: str):
        self.active_project = project_name
        if self._event_bus:
            self._event_bus.publish("ProjectLoaded", {"project": project_name})

    def shutdown(self):
        """Triggers clean shutdown releases and notifies the subsystems."""
        self.is_active = False
        if self._event_bus:
            self._event_bus.publish("ApplicationShutdown", {"session_id": self.session_id})

    def health(self) -> dict:
        status = "healthy" if self.is_active else "degraded"
        return {
            "status": status,
            "details": f"Active Session: {self.session_id} | Uptime: {self.get_uptime()}"
        }

    def get_uptime(self) -> str:
        if not self.start_time:
            return "00:00:00"
        diff = datetime.utcnow() - self.start_time
        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

# Global instance
session_manager = SessionManager()
