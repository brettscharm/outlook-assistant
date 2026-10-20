"""
Task Management Module for Outlook Assistant
Manages 'Your Tasks' (action items for you) and 'Others' Tasks' (waiting on someone else).
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TASKS_FILE = Path.home() / ".outlook_assistant_tasks.json"


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
            logger.error(f"Error loading tasks: {e}")

    return {
        "my_tasks": [
            {
                "id": str(uuid.uuid4()),
                "text": "Review weekly sprint agenda before team sync",
                "completed": False,
                "due_date": "Today",
                "source": "Calendar Sync",
                "created_at": datetime.now().isoformat(),
            }
        ],
        "others_tasks": [
            {
                "id": str(uuid.uuid4()),
                "text": "Waiting on budget spreadsheet from Finance",
                "assignee": "Finance Team",
                "completed": False,
                "due_date": "Tomorrow",
                "source": "Email Thread",
                "created_at": datetime.now().isoformat(),
            }
        ],
    }


def save_tasks(tasks: Dict[str, List[Dict[str, Any]]]):
    """Save tasks dictionary to disk."""
    try:
        with open(TASKS_FILE, "w") as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving tasks: {e}")


def add_task(
    task_type: str,
    text: str,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a new task to 'my_tasks' or 'others_tasks'."""
    tasks = load_tasks()
    key = "others_tasks" if task_type == "others" else "my_tasks"

    new_item = {
        "id": str(uuid.uuid4()),
        "text": text.strip(),
        "assignee": assignee.strip() if assignee else ("Me" if key == "my_tasks" else "Other"),
        "completed": False,
        "due_date": due_date or "Flexible",
        "source": source or "Manual",
        "created_at": datetime.now().isoformat(),
    }

    tasks[key].insert(0, new_item)
    save_tasks(tasks)
    return new_item


def toggle_task(task_id: str) -> bool:
    """Toggle completed status of a task."""
    tasks = load_tasks()
    for category in ["my_tasks", "others_tasks"]:
        for item in tasks[category]:
            if item.get("id") == task_id:
                item["completed"] = not item.get("completed", False)
                save_tasks(tasks)
                return True
    return False


def delete_task(task_id: str) -> bool:
    """Delete a task by ID."""
    tasks = load_tasks()
    for category in ["my_tasks", "others_tasks"]:
        orig_len = len(tasks[category])
        tasks[category] = [t for t in tasks[category] if t.get("id") != task_id]
        if len(tasks[category]) < orig_len:
            save_tasks(tasks)
            return True
    return False
