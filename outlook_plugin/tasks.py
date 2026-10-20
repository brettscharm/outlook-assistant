from .config import DATA_DIR
"""
Task Management Module for Outlook Assistant
Manages 'Your Tasks' (action items for you) and 'Others' Tasks' (waiting on someone else).
"""

import json
import os
import tempfile
import threading
_LOCK = threading.RLock()
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TASKS_FILE = DATA_DIR / ".outlook_assistant_tasks.json"


def load_tasks() -> Dict[str, List[Dict[str, Any]]]:
    """Load tasks from disk or return default template."""
    if TASKS_FILE.exists():
        try:
            with open(TASKS_FILE, "r") as f:
                data = json.load(f)
                return {
                    "my_tasks": data.get("my_tasks", []),
                    "others_tasks": data.get("others_tasks", []),
                }
        except Exception as e:
            raise RuntimeError("Saved tasks could not be read. The existing file has been preserved; restore it from a backup before continuing.") from e

    default_data = {'my_tasks': [], 'others_tasks': []}
    save_tasks(default_data)
    return default_data


def save_tasks(tasks: Dict[str, List[Dict[str, Any]]]):
    """Save tasks dictionary to disk."""
    fd, name = tempfile.mkstemp(dir=TASKS_FILE.parent, prefix='.outlook-tasks-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(tasks, stream)
        os.replace(name, TASKS_FILE)
    finally:
        if os.path.exists(name): os.unlink(name)


def add_task(
    task_type: str,
    text: str,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
    source: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Add a new task and return all updated tasks."""
    tasks = load_tasks()
    key = "my_tasks" if task_type == "my" else "others_tasks"

    if source:
        for items in tasks.values():
            if any(t.get("email_id")==source["email_id"] and " ".join(t["text"].lower().split())==" ".join(text.lower().split()) for t in items):
                return tasks

    new_item = {
        "id": str(uuid.uuid4()),
        "text": text.strip(),
        "assignee": assignee.strip() if assignee else ("Me" if key == "my_tasks" else "Other"),
        "completed": False,
        "due_date": due_date or "",
        "type": task_type,
        "created_at": datetime.now().isoformat(),
    }

    if source:
        new_item.update(source)
    tasks[key].insert(0, new_item)
    save_tasks(tasks)
    return tasks


def toggle_task(task_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Toggle completed status of a task and return all updated tasks."""
    tasks = load_tasks()
    for category in ["my_tasks", "others_tasks"]:
        for item in tasks[category]:
            if str(item.get("id")) == str(task_id):
                item["completed"] = not item.get("completed", False)
                save_tasks(tasks)
                return tasks
    return tasks


def delete_task(task_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Delete a task by ID and return all updated tasks."""
    tasks = load_tasks()
    for category in ["my_tasks", "others_tasks"]:
        tasks[category] = [t for t in tasks[category] if str(t.get("id")) != str(task_id)]
    save_tasks(tasks)
    return tasks


def _serialized(fn):
    def run(*args, **kwargs):
        with _LOCK: return fn(*args, **kwargs)
    return run

load_tasks = _serialized(load_tasks)
add_task = _serialized(add_task)
toggle_task = _serialized(toggle_task)
delete_task = _serialized(delete_task)


@_serialized
def edit_task(task_id, text, owner, kind, due_date):
    from datetime import date
    if not text.strip(): raise ValueError('Enter a task.')
    if kind not in ('my','others','unclear'): raise ValueError('Choose an owner group.')
    if due_date: date.fromisoformat(due_date)
    data=load_tasks()
    for group in ('my_tasks','others_tasks'):
        for item in data[group]:
            if item['id']==task_id:
                item.update(text=text.strip()[:2000],assignee=owner.strip()[:200] or 'Owner unclear',type=kind,due_date=due_date)
                data[group].remove(item)
                data['my_tasks' if kind=='my' else 'others_tasks'].insert(0,item)
                save_tasks(data);return data
    raise ValueError('Task not found.')
