"""
ULTRON Conversation Manager — Manages interaction history, follow-up chains, and session contexts.
"""

import logging
from typing import List, Dict, Any
from ultron.core.event_bus import event_bus

class UltronConversationManager:
    """Manages active session context variables and chat histories."""
    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.history: List[Dict[str, str]] = []
        self.logger = logging.getLogger("ultron-agent")
        self._subscribe_events()

    def _subscribe_events(self):
        event_bus.subscribe("COMMAND_COMPLETED", self.on_turn_completed)

    def add_turn(self, query: str, response: str):
        turn = {"query": query, "response": response}
        self.history.append(turn)
        if len(self.history) > 20:
            self.history.pop(0)

    def get_history(self) -> List[Dict[str, str]]:
        return self.history

    def clear_context(self):
        self.history.clear()
        self.logger.info("Conversation context cleared.")

    def on_turn_completed(self, event):
        # We can extract command and final response if available
        pass

# Global instance initialized at boot
conversation_manager = None

def init_conversation_manager(memory_manager) -> UltronConversationManager:
    global conversation_manager
    conversation_manager = UltronConversationManager(memory_manager)
    return conversation_manager
