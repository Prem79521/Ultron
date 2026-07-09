"""
ULTRON API Layer — Task API interface.
"""

from typing import Dict, Any, List
from ultron.core.task_manager import task_manager

def submit_task(task_id: str, description: str):
    task_manager.create_task(task_id, description)

def start_task(task_id: str):
    task_manager.start_task(task_id)

def complete_task(task_id: str):
    task_manager.complete_task(task_id)

def fail_task(task_id: str, error: str):
    task_manager.fail_task(task_id, error)

def list_active_tasks() -> List[Dict[str, Any]]:
    return [t for t in task_manager.list_tasks() if t["status"] in ["Running", "Queued"]]
