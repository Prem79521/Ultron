"""
ULTRON Command Queue — Manages FIFO command dispatching to enforce sequential execution.
"""

import queue
import threading
import logging
from typing import Callable
from ultron.core.event_bus import event_bus
from ultron.core.state_manager import state_manager

class UltronCommandQueue:
    """Consolidated queue pipeline consuming commands on a daemon worker thread."""
    def __init__(self, execution_handler: Callable[[str], None]):
        self.queue = queue.Queue()
        self.handler = execution_handler
        self.logger = logging.getLogger("ultron-agent")
        self.worker_thread = None
        self.running = False

    def start(self):
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("Command Queue consumer thread active.")

    def stop(self):
        self.running = False
        # Enqueue None to break blocking get
        self.queue.put(None)

    def enqueue(self, command_text: str):
        if not command_text.strip():
            return
            
        self.logger.info(f"Enqueueing directive: '{command_text}'")
        self.queue.put(command_text)
        event_bus.publish("QUEUE_COUNT_CHANGED", {"count": self.get_count()})

    def get_count(self) -> int:
        # Subtract active processing command if any (we approximate using queue size)
        return self.queue.qsize()

    def _worker_loop(self):
        while self.running:
            try:
                command = self.queue.get()
                if command is None:
                    break
                    
                # Publish event that we started processing the command
                event_bus.publish("COMMAND_RECEIVED", {"command": command})
                event_bus.publish("QUEUE_COUNT_CHANGED", {"count": self.get_count()})
                
                # Execute the command handler
                self.handler(command)
                
                # Signal task done
                self.queue.task_done()
                event_bus.publish("COMMAND_COMPLETED", {"command": command})
                event_bus.publish("QUEUE_COUNT_CHANGED", {"count": self.get_count()})
                
            except Exception as e:
                self.logger.error(f"Error in Command Queue worker thread: {e}")
                state_manager.set_state("Error")
