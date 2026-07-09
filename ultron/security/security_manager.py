"""
ULTRON Security Manager — Enforces plugin sandboxing, permissions, and operator consents.
"""

import logging
from typing import Callable, Optional
from ultron.core.event_bus import event_bus

class UltronSecurityManager:
    """Consolidated controller ensuring sensitive commands obtain operator consent."""
    def __init__(self):
        self.logger = logging.getLogger("ultron-agent")
        self._consent_callback: Optional[Callable[[str, str], bool]] = None

    def set_consent_callback(self, callback: Callable[[str, str], bool]):
        self._consent_callback = callback

    def request_consent(self, action_type: str, description: str) -> bool:
        """Prompts the operator for explicit confirmation before execution."""
        self.logger.warning(f"SECURITY: Requesting consent for sensitive action '{action_type}': {description}")
        
        # Emit warning event
        event_bus.publish("SECURITY_ALERT", {"action": action_type, "description": description})
        
        if self._consent_callback:
            approved = self._consent_callback(action_type, description)
            self.logger.info(f"SECURITY: Consent result for '{action_type}': {approved}")
            return approved
            
        # Default fallback to Deny if no handler registered
        self.logger.error("SECURITY: No consent callback registered. Defaulting to DENY.")
        return False

# Global singleton instance
security_manager = UltronSecurityManager()
