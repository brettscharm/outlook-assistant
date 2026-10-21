from .storage import read_json, write_json
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
    data=read_json(TASKS_FILE,{'my_tasks':[],'others_tasks':[]})
    return {'my_tasks':data.get('my_tasks',[]),'others_tasks':data.get('others_tasks',[])}


def save_tasks(tasks):
    write_json(TASKS_FILE,tasks)


def add_task(
    task_type: str,
    text: str,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
    source: Optional[Dict[str, Any]] = None,
    description: str = "",
) -> Dict[str, List[Dict[str, Any]]]:
    """Add a new task and return all updated tasks."""
    tasks = load_tasks()
    key = "my_tasks" if task_type == "my" else "others_tasks"

    if source:
        for items in tasks.values():
            if any(t.get("email_id")==source["email_id"] and " ".join(t["text"].lower().split())==" ".join(text.lower().split()) for t in items):
                return tasks

    from .config import read_config
    default_owner=(read_config().get("user_context",{}).get("full_name","").strip() or "Me") if key=="my_tasks" else "Owner unclear"
    new_item = {
        "id": str(uuid.uuid4()),
        "text": text.strip(),
        "description": str(description).strip()[:4000],
        "assignee": assignee.strip() if assignee else default_owner,
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
                item["lane_id"] = "done" if item["completed"] else "todo"
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
def edit_task(task_id, text, owner, kind, due_date, description=None):
    from datetime import date
    if not text.strip(): raise ValueError('Enter a task.')
    if kind not in ('my','others','unclear'): raise ValueError('Choose an owner group.')
    if due_date: date.fromisoformat(due_date)
    data=load_tasks()
    for group in ('my_tasks','others_tasks'):
        for item in data[group]:
            if item['id']==task_id:
                item.update(text=text.strip()[:2000],assignee=owner.strip()[:200] or 'Owner unclear',type=kind,due_date=due_date)
                if description is not None:item['description']=str(description).strip()[:4000]
                data[group].remove(item)
                data['my_tasks' if kind=='my' else 'others_tasks'].insert(0,item)
                save_tasks(data);return data
    raise ValueError('Task not found.')


DEFAULT_LANES=[{'id':'todo','name':'My Tasks'},{'id':'progress','name':'In Progress'},{'id':'done','name':'Done'}]
def board_lanes():
    from .config import read_config
    return read_config().get('task_lanes') or [dict(lane) for lane in DEFAULT_LANES]

def task_lane(task):
    if task.get('completed'):return 'done'
    lane=task.get('lane_id','todo')
    return lane if lane!='done' else 'todo'

@_serialized
def save_board_lanes(lanes):
    from .config import update_config
    if not isinstance(lanes,list) or not 2<=len(lanes)<=12:raise ValueError('Use between 2 and 12 lanes.')
    clean=[];ids=set()
    import re
    for lane in lanes:
        if not isinstance(lane,dict):raise ValueError('Invalid lane.')
        key=lane.get('id','');name=lane.get('name','')
        if not isinstance(key,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',key) or key in ids:raise ValueError('Invalid or duplicate lane.')
        if not isinstance(name,str) or not name.strip() or len(name.strip())>60:raise ValueError('Name each lane using up to 60 characters.')
        ids.add(key);clean.append({'id':key,'name':name.strip()})
    if not {'todo','done'}<=ids:raise ValueError('Keep the starting and completed lanes; you can rename them.')
    if any(task_lane(task) not in ids for rows in load_tasks().values() for task in rows):raise ValueError('Move tasks out of a lane before removing it.')
    update_config({'task_lanes':clean});return clean

@_serialized
def move_task(task_id,lane_id):
    if lane_id not in {lane['id'] for lane in board_lanes()}:raise ValueError('That lane no longer exists. Refresh the board.')
    data=load_tasks()
    for rows in data.values():
        for task in rows:
            if task['id']==task_id:
                task.update(lane_id=lane_id,completed=lane_id=='done')
                save_tasks(data);return data
    raise ValueError('Task not found.')
