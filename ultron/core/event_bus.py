"""
ULTRON Event Bus — Central messaging system facilitating decoupled communications with priority and tracing.
"""

import time
import threading
import logging
from typing import Dict, Any, List, Callable, Tuple

class Event:
    def __init__(self, event_type: str, payload: Any = None):
        self.event_type = event_type
        self.payload = payload
        self.timestamp = time.time()

class EventBus:
    def __init__(self):
        # Store subscribers as a list of (callback, priority) tuples
        self._subscribers: Dict[str, List[Tuple[Callable[[Event], None], int]]] = {}
        self._sticky_events: Dict[str, Event] = {}
        self._event_history: List[Dict[str, Any]] = []
        self._publish_counts: Dict[str, int] = {}
        self._publish_timestamps: List[float] = []
        self._lock = threading.RLock()
        self.logger = logging.getLogger("ultron-agent")

    def subscribe(self, event_type: str, callback: Callable[[Event], None], priority: int = 0):
        """Registers a listener callback for a specific event type. Higher priority runs first."""
        cnt = 0
        sticky_event = None
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            # Prevent duplicate subscriptions
            already_subscribed = any(sub[0] == callback for sub in self._subscribers[event_type])
            if already_subscribed:
                return
                
            self._subscribers[event_type].append((callback, priority))
            # Sort by priority descending
            self._subscribers[event_type].sort(key=lambda item: item[1], reverse=True)
            cnt = len(self._subscribers[event_type])
            
            # Immediately trigger if sticky event exists
            if event_type in self._sticky_events:
                sticky_event = self._sticky_events[event_type]

        self.logger.info(f"Registered: {event_type} Subscriber Count: {cnt}")
        if sticky_event:
            try:
                callback(sticky_event)
            except Exception:
                pass

    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]):
        """Unregisters a listener callback for a specific event type."""
        cnt = -1
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    sub for sub in self._subscribers[event_type] if sub[0] != callback
                ]
                cnt = len(self._subscribers[event_type])
                if cnt == 0:
                    del self._subscribers[event_type]
        if cnt >= 0:
            self.logger.info(f"Unregistered: {event_type} Subscriber Count: {cnt}")

    def publish(self, event_type: str, payload: Any = None, sticky: bool = False, delay: float = 0.0):
        """Publishes an event to the bus. Supports delays and sticky states."""
        event = Event(event_type, payload)

        # Single lock acquisition for all bookkeeping
        with self._lock:
            self._publish_counts[event_type] = self._publish_counts.get(event_type, 0) + 1
            now = time.time()
            self._publish_timestamps.append(now)
            # Trim timestamps older than 1 second
            while self._publish_timestamps and self._publish_timestamps[0] < now - 1.0:
                self._publish_timestamps.pop(0)
            if sticky:
                self._sticky_events[event_type] = event
            # Bounded history ring-buffer
            self._event_history.append({"event_type": event_type, "payload": payload, "timestamp": event.timestamp})
            if len(self._event_history) > 100:
                self._event_history.pop(0)

        if delay > 0.0:
            timer = threading.Timer(delay, self._dispatch, args=[event])
            timer.daemon = True
            timer.start()
        else:
            self._dispatch(event)

    def get_publish_count(self, event_type: str) -> int:
        """Returns the publish frequency of a given event type."""
        with self._lock:
            return self._publish_counts.get(event_type, 0)

    def get_events_per_second(self) -> int:
        """Returns the total number of events published in the last 1 second."""
        with self._lock:
            now = time.time()
            while self._publish_timestamps and self._publish_timestamps[0] < now - 1.0:
                self._publish_timestamps.pop(0)
            return len(self._publish_timestamps)

    def _dispatch(self, event: Event):
        with self._lock:
            listeners = list(self._subscribers.get(event.event_type, []))

        # Debug-only audit trace (guarded — zero cost in production INFO level)
        if self.logger.isEnabledFor(logging.DEBUG) and event.event_type in (
            "WAKE_DETECTED", "VOICE_STATE_CHANGED", "COMMAND_RECEIVED",
            "COMMAND_COMPLETED", "VoiceStarted", "VoiceStopped",
        ):
            self.logger.debug(
                "EventBus dispatch: %s -> %d listener(s)", event.event_type, len(listeners)
            )

        for callback, _ in listeners:
            try:
                callback(event)
            except Exception as e:
                self.logger.warning(f"Error in EventBus listener callback: {e}")

    def publish_local(self, event_type: str, payload: Any = None):
        """Publishes a local event without logging handlers or delays."""
        self.publish(event_type, payload)

    def replay_history(self):
        """Developer tool: Replays history of recorded events to active subscribers."""
        with self._lock:
            history = list(self._event_history)
        for item in history:
            event = Event(item["event_type"], item["payload"])
            self._dispatch(event)

    def get_subscriber_count(self) -> int:
        """Returns total number of registered subscriber callbacks across all event types."""
        with self._lock:
            return sum(len(subs) for subs in self._subscribers.values())

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._event_history)

    def health(self) -> dict:
        return {
            "status": "healthy",
            "details": f"Active subscriptions: {len(self._subscribers)} | Sticky events: {len(self._sticky_events)}"
        }

    def log_subscribers(self):
        """Prints all registered EventBus subscribers for startup verification."""
        self.logger.info("=== EVENT BUS REGISTERED SUBSCRIBERS ===")
        with self._lock:
            for event_type, subs in self._subscribers.items():
                self.logger.info(f"Event: '{event_type}'")
                for callback, priority in subs:
                    name = "unknown"
                    if hasattr(callback, "__self__") and hasattr(callback.__self__, "__class__"):
                        name = f"{callback.__self__.__class__.__name__}.{callback.__name__}"
                    elif hasattr(callback, "__name__"):
                        name = callback.__name__
                    self.logger.info(f"  -> {name} (priority={priority})")

# Global instance
event_bus = EventBus()

def get_event_bus() -> EventBus:
    """Dynamic accessor — avoids stale module-level binding (BUG-01)."""
    return event_bus
