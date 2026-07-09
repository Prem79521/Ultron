"""
ULTRON Service Manager — Manages background systems as lifecycle services.
"""

import time
import logging
from typing import Dict, List, Optional

class UltronService:
    """Base class for all background Cognitive OS services with strict lifecycle enforcement."""
    def __init__(self, name: str):
        self.name = name
        self.active = False
        self.dependencies: List[str] = []
        self._start_time = 0.0
        self._restart_count = 0
        self._last_failure: Optional[str] = None
        self._subscribed_events = []
        self._lifecycle_stage = "created"

    def subscribe_event(self, event_type: str, callback):
        from ultron.core.event_bus import event_bus
        event_bus.subscribe(event_type, callback)
        self._subscribed_events.append((event_type, callback))

    def register(self):
        self._lifecycle_stage = "registered"
        return True

    def initialize(self):
        if self._lifecycle_stage != "registered":
            self.register()
        self._lifecycle_stage = "initialized"
        return True

    def start(self) -> bool:
        if self._lifecycle_stage in ["started", "ready"]:
            logging.getLogger("ultron-agent").warning(f"Duplicate startup attempt detected for service '{self.name}'. Blocked.")
            return False
            
        self.active = True
        self._start_time = time.time()
        self._lifecycle_stage = "started"
        return True

    def ready(self):
        self._lifecycle_stage = "ready"
        return True

    def stop(self) -> bool:
        self.active = False
        self._lifecycle_stage = "stopped"
        from ultron.core.event_bus import event_bus
        for event_type, callback in self._subscribed_events:
            try:
                event_bus.unsubscribe(event_type, callback)
            except Exception:
                pass
        self._subscribed_events.clear()
        return True

    def cleanup(self):
        self._lifecycle_stage = "cleaned"
        return True

    def is_active(self) -> bool:
        return self.active or self._lifecycle_stage in ["started", "ready"]

    def restart(self) -> bool:
        self._restart_count += 1
        self.stop()
        self.cleanup()
        self.initialize()
        return self.start()

    def status(self) -> str:
        return self._lifecycle_stage.upper()

    def health(self) -> str:
        return "Running" if self.is_active() else "Offline"

    def uptime(self) -> float:
        if self.is_active() and self._start_time > 0:
            return time.time() - self._start_time
        return 0.0

    def restart_count(self) -> int:
        return self._restart_count

    def last_failure(self) -> Optional[str]:
        return self._last_failure

    def record_failure(self, error_message: str):
        self._last_failure = error_message

class UltronServiceManager:
    """Manages starts, stops, health queries, and recoveries of OS services with dependency awareness."""
    def __init__(self):
        self._services: Dict[str, UltronService] = {}
        self._startup_order: List[str] = []
        self.logger = logging.getLogger("ultron-agent")

    def register_service(self, name: str, service: UltronService):
        self._services[name] = service
        if hasattr(service, "register"):
            service.register()
        self.logger.info(f"Registered service: {name}")

    def get_service(self, name: str) -> Optional[UltronService]:
        return self._services.get(name)

    def start_service(self, name: str) -> bool:
        service = self.get_service(name)
        if service:
            is_act = service.is_active() if hasattr(service, "is_active") else getattr(service, "active", False)
            if is_act:
                self.logger.warning(f"Duplicate startup attempt detected for service '{name}'. Blocked.")
                return True
                
            # Resolve dependencies first
            deps = getattr(service, "dependencies", [])
            for dep in deps:
                dep_srv = self.get_service(dep)
                if dep_srv:
                    dep_act = dep_srv.is_active() if hasattr(dep_srv, "is_active") else getattr(dep_srv, "active", False)
                    if not dep_act:
                        self.logger.info(f"Starting dependency '{dep}' for service '{name}'")
                        self.start_service(dep)
            try:
                stage = getattr(service, "_lifecycle_stage", None)
                if stage in ["created", "registered"] and hasattr(service, "initialize"):
                    service.initialize()
                success = service.start()
                if success:
                    if hasattr(service, "_lifecycle_stage"):
                        service._lifecycle_stage = "started"
                    if hasattr(service, "ready"):
                        service.ready()
                    self.logger.info(f"Service started: {name}")
                    if name not in self._startup_order:
                        self._startup_order.append(name)
                    from ultron.core.event_bus import event_bus
                    event_bus.publish("SERVICE_STARTED", {"service": name})
                return success
            except Exception as e:
                if hasattr(service, "record_failure"):
                    service.record_failure(str(e))
                self.logger.error(f"Failed to start service {name}: {e}")
                from ultron.core.event_bus import event_bus
                event_bus.publish("ERROR_OCCURRED", {"message": f"Service failed to start: {name}", "error": str(e)})
        return False

    def stop_service(self, name: str) -> bool:
        service = self.get_service(name)
        if service:
            try:
                success = service.stop()
                if success:
                    if hasattr(service, "_lifecycle_stage"):
                        service._lifecycle_stage = "stopped"
                    if hasattr(service, "cleanup"):
                        service.cleanup()
                    self.logger.info(f"Service stopped: {name}")
                    from ultron.core.event_bus import event_bus
                    event_bus.publish("SERVICE_STOPPED", {"service": name})
                return success
            except Exception as e:
                self.logger.error(f"Failed to stop service {name}: {e}")
        return False

    def restart_service(self, name: str) -> bool:
        self.logger.info(f"Restarting service: {name}")
        self.stop_service(name)
        return self.start_service(name)

    def start_all(self):
        """Topologically resolves startup ordering based on service dependencies."""
        visited = set()
        temp_mark = set()
        order = []

        def visit(name):
            if name in temp_mark:
                return
            if name not in visited:
                temp_mark.add(name)
                srv = self.get_service(name)
                if srv:
                    for dep in srv.dependencies:
                        visit(dep)
                temp_mark.remove(name)
                visited.add(name)
                order.append(name)

        for name in list(self._services.keys()):
            visit(name)

        self.logger.info(f"Resolved service startup order: {order}")
        for name in order:
            self.start_service(name)

    def stop_all(self):
        """Stops all services in reverse order of their startup for clean teardown."""
        order = list(reversed(self._startup_order))
        if not order:
            order = list(self._services.keys())
        self.logger.info(f"Teardown order: {order}")
        for name in order:
            self.stop_service(name)

    def list_services(self) -> List[str]:
        return list(self._services.keys())

# Global singleton
service_manager = UltronServiceManager()
