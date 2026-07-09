"""
ULTRON Notification Center — Aggregates and broadcasts system alert messages.
"""

import time
import logging
from typing import Dict, List, Any
from ultron.core.event_bus import event_bus

from ultron.core.service_manager import UltronService

class UltronNotificationCenter(UltronService):
    """Consolidated broker receiving events and routing notifications to listeners."""
    def __init__(self):
        super().__init__("NotificationService")
        self.notifications: List[Dict[str, Any]] = []
        self.logger = logging.getLogger("ultron-agent")
        self._subscribe_to_system_events()

    def start(self) -> bool:
        self.active = True
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

    def _subscribe_to_system_events(self):
        # Auto-generate notifications from Event Bus messages
        event_bus.subscribe("DEVICE_CONNECTED", lambda e: self.notify("Hardware", "Device Connected", e.payload.get("device")))
        event_bus.subscribe("DEVICE_DISCONNECTED", lambda e: self.notify("Hardware", "Device Disconnected", e.payload.get("device")))
        event_bus.subscribe("SERVICE_RESTARTED", lambda e: self.notify("System", "Service Restored", f"Subsystem '{e.payload.get('service')}' was automatically restarted."))
        event_bus.subscribe("PLUGIN_LOADED", lambda e: self.notify("Plugins", "Plugin Installed", f"Plugin '{e.payload.get('plugin')}' is now active."))
        event_bus.subscribe("ERROR_OCCURRED", lambda e: self.notify("Security", "System Alert", e.payload.get("message")))

    def notify(self, category: str, title: str, message: str):
        notif = {
            "timestamp": time.strftime("%H:%M:%S"),
            "category": category.upper(),
            "title": title,
            "message": message
        }
        self.notifications.append(notif)
        if len(self.notifications) > 100:
            self.notifications.pop(0)
            
        # Log it
        self.logger.info(f"[NOTIFICATION] [{notif['category']}] {title}: {message}")
        # Notify Event Bus
        event_bus.publish("NOTIFICATION_RECEIVED", notif)
        event_bus.publish("NOTIFICATION", notif)

    def get_recent_notifications(self) -> List[Dict[str, Any]]:
        return self.notifications

# Global singleton
notification_center = UltronNotificationCenter()
