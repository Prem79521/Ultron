"""
ULTRON Task Manager — Tracks active, queued, and completed Cognitive OS tasks.
"""

import time
import logging
from typing import Dict, List, Any, Optional
from ultron.core.event_bus import event_bus

class UltronTask:
    def __init__(self, task_id: str, description: str):
        self.task_id = task_id
        self.description = description
        self.status = "Queued"
        self.error = ""
        self.start_time = 0.0
        self.end_time = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "status": self.status,
            "error": self.error,
            "duration_ms": int((self.end_time - self.start_time) * 1000) if self.end_time else 0
        }

class UltronTaskManager:
    """Core tracker monitoring queued and completed execution states."""
    def __init__(self):
        self._tasks: Dict[str, UltronTask] = {}
        self.logger = logging.getLogger("ultron-agent")

    def create_task(self, task_id: str, description: str) -> UltronTask:
        task = UltronTask(task_id, description)
        self._tasks[task_id] = task
        event_bus.publish("TASK_CREATED", {"task_id": task_id, "description": description})
        return task

    def start_task(self, task_id: str):
        task = self._tasks.get(task_id)
        if task:
            task.status = "Running"
            task.start_time = time.time()
            event_bus.publish("TASK_STARTED", {"task_id": task_id, "description": task.description})

    def complete_task(self, task_id: str):
        task = self._tasks.get(task_id)
        if task:
            task.status = "Completed"
            task.end_time = time.time()
            event_bus.publish("TASK_COMPLETED", {"task_id": task_id, "description": task.description})

    def fail_task(self, task_id: str, error: str):
        task = self._tasks.get(task_id)
        if task:
            task.status = "Failed"
            task.error = error
            task.end_time = time.time()
            event_bus.publish("TASK_FAILED", {"task_id": task_id, "description": task.description, "error": error})

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    def list_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tasks.values()]

# Global singleton
task_manager = UltronTaskManager()
