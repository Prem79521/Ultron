"""
ULTRON Core Module — Central event routing, configuration management, and session lifecycle.
"""

from ultron.core.config_loader import config_loader, ConfigLoader
from ultron.core.logger import ultron_logger, UltronLogger
from ultron.core.event_bus import event_bus, EventBus, Event
from ultron.core.session import session_manager, SessionManager

class CoreSystem:
    """Consolidated orchestrator for general platform services."""
    def __init__(self):
        self.config = config_loader
        self.logger = ultron_logger
        self.events = event_bus
        self.session = session_manager
        
        self._modules = {}
        
        # Link logger to Event Bus for live debug overlays
        self.logger.set_event_bus(self.events)
        
        self.logger.info("SYSTEM", "Platform Core Services Initialized.")

    def register_module(self, name: str, instance) -> None:
        self._modules[name] = instance

    def get_module(self, name: str):
        return self._modules.get(name)


    def health(self) -> dict:
        """Runs health checks across all base subsystems."""
        checks = {
            "config": self.config.health(),
            "logger": self.logger.health(),
            "events": self.events.health(),
            "session": self.session.health()
        }
        
        all_healthy = all(c["status"] == "healthy" for c in checks.values())
        return {
            "status": "healthy" if all_healthy else "degraded",
            "details": checks
        }
