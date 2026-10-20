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

    default_data = {
        "my_tasks": [
            {
                "id": str(uuid.uuid4()),
                "text": "Review weekly engineering update",
                "completed": False,
                "due_date": "Today",
                "assignee": "Me",
                "created_at": datetime.now().isoformat(),
            }
        ],
        "others_tasks": [
            {
                "id": str(uuid.uuid4()),
                "text": "Waiting on budget approval",
                "assignee": "Finance",
                "completed": False,
                "due_date": "Tomorrow",
                "created_at": datetime.now().isoformat(),
            }
        ],
    }
    save_tasks(default_data)
    return default_data


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
) -> Dict[str, List[Dict[str, Any]]]:
    """Add a new task and return all updated tasks."""
    tasks = load_tasks()
    key = "others_tasks" if task_type == "others" else "my_tasks"

    new_item = {
        "id": str(uuid.uuid4()),
        "text": text.strip(),
        "assignee": assignee.strip() if assignee else ("Me" if key == "my_tasks" else "Other"),
        "completed": False,
        "due_date": due_date or "Flexible",
        "created_at": datetime.now().isoformat(),
    }

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
