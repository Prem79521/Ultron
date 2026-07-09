"""
ULTRON Health Monitor — Monitors background service lifecycles and performs auto-recovery.
"""

import time
import threading
import logging
from ultron.core.service_manager import service_manager, UltronService
from ultron.core.event_bus import event_bus

class UltronHealthMonitor(UltronService):
    """Watchdog thread responsible for active service monitoring and event logging with supervision."""
    def __init__(self, interval_seconds: int = 5):
        super().__init__("HealthMonitorService")
        self.interval = interval_seconds
        self.restart_counts = {}
        self.last_restart_time = {}
        self.failure_history = {}
        self.logger = logging.getLogger("ultron-agent")
        self.thread = None

    def start(self) -> bool:
        self.active = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.logger.info("Health Monitor service started.")
        return True

    def stop(self) -> bool:
        self.active = False
        return True

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def health(self) -> str:
        return "Running" if self.active else "Offline"

    def status(self) -> str:
        return "Running" if self.active else "Offline"

    def configure(self, config: dict):
        pass

    def _monitor_loop(self):
        while self.active:
            time.sleep(self.interval)
            try:
                for name in service_manager.list_services():
                    service = service_manager.get_service(name)
                    if not service:
                        continue
                        
                    # Check health status
                    h_status = service.health()
                    is_active = service.is_active() if hasattr(service, "is_active") else getattr(service, "active", False)
                    if h_status == "Error" or (is_active and h_status == "Offline"):
                        self.logger.warning(f"Health Monitor detected degraded service: {name}. Status: {h_status}")
                        self._attempt_recovery(name)
            except Exception as e:
                self.logger.error(f"Health Monitor loop exception: {e}")

    def _attempt_recovery(self, name: str):
        last_attempt = self.last_restart_time.get(name, 0.0)
        retries = self.restart_counts.get(name, 0)
        backoff_delay = min(60, 2 ** retries)
        
        if time.time() - last_attempt < backoff_delay:
            return

        if retries < 5:
            self.restart_counts[name] = retries + 1
            self.last_restart_time[name] = time.time()
            self.logger.info(f"Attempting recovery restart of '{name}' (Retry {retries + 1}/5, backoff {backoff_delay}s)...")
            
            failure_record = {
                "timestamp": time.time(),
                "error": "Service status degraded",
                "retry": retries + 1
            }
            if name not in self.failure_history:
                self.failure_history[name] = []
            self.failure_history[name].append(failure_record)
            
            success = service_manager.restart_service(name)
            if success:
                event_bus.publish("SERVICE_RESTARTED", {"service": name})
                self.logger.info(f"Service '{name}' successfully recovered.")
            else:
                self.logger.error(f"Recovery restart of '{name}' failed.")
        else:
            self.logger.error(f"Service '{name}' has exceeded maximum restart attempts (5). Recovery halted.")
            event_bus.publish("ERROR_OCCURRED", {
                "message": f"Service '{name}' failed and could not be recovered. Operating in degraded mode.",
                "service": name
            })

# Global instance
health_monitor = UltronHealthMonitor()
