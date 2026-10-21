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


def validate_co_owners(value):
    if not isinstance(value,list) or len(value)>20:raise ValueError('Add up to 20 co-owners.')
    result=[]
    for person in value:
        if not isinstance(person,str) or len(person)>200 or any(ord(c)<32 for c in person):raise ValueError('Use a name or email address for each co-owner.')
        person=person.strip()
        if person and person.casefold() not in [p.casefold() for p in result]:result.append(person)
    return result


def add_task(
    task_type: str,
    text: str,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
    source: Optional[Dict[str, Any]] = None,
    description: str = "",
    request_id: Optional[str] = None,
    source_type: Optional[str] = None,
    source_url: str = "",
    priority: str = "none",
    project_id: str = "",
    color: str = "none",
    deadline=None,
    co_owners=None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Add a new task and return all updated tasks."""
    source_type,source_url=validate_source(source_type or ("email" if source and source.get("email_id") else "other"),source_url)
    from .projects import validate_id
    project_id=validate_id(project_id)
    priority=validate_priority(priority)
    people=validate_co_owners(co_owners or [])
    extras=validate_task_details(color,deadline)
    tasks = load_tasks()
    if request_id and any(t.get("id")==request_id for rows in tasks.values() for t in rows):return tasks
    key = "my_tasks" if task_type == "my" else "others_tasks"

    if source:
        for items in tasks.values():
            if any(t.get("email_id")==source["email_id"] and " ".join(t["text"].lower().split())==" ".join(text.lower().split()) for t in items):
                return tasks

    from .config import read_config
    default_owner=(read_config().get("user_context",{}).get("full_name","").strip() or "Me") if key=="my_tasks" else "Owner unclear"
    new_item = {
        "id": request_id or str(uuid.uuid4()),
        "text": text.strip(),
        "description": str(description).strip()[:4000],
        "source_type":source_type,"source_url":source_url,"priority":priority,"project_id":project_id,
        "assignee": current_user_name() if task_type=="my" else assignee.strip() if assignee else default_owner,
        "completed": False,
        "due_date": due_date or "",
        "type": task_type,
        "created_at": datetime.now().isoformat(),
    }

    new_item["co_owners"]=people
    new_item.update(extras)
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
def edit_task(task_id, text, owner, kind, due_date, description=None, source_type=None, source_url=None, priority=None, project_id=None, color=None, deadline=None, co_owners=None):
    from datetime import date
    if not text.strip(): raise ValueError('Enter a task.')
    if kind not in ('my','others','unclear'): raise ValueError('Choose an owner group.')
    if due_date: date.fromisoformat(due_date)
    people=validate_co_owners(co_owners) if co_owners is not None else None
    if priority is not None:priority=validate_priority(priority)
    if project_id is not None:
        from .projects import validate_id
        project_id=validate_id(project_id)
    data=load_tasks()
    for group in ('my_tasks','others_tasks'):
        for item in data[group]:
            if item['id']==task_id:
                extras=validate_task_details(color,deadline,item.get('deadline'))
                item.update(text=text.strip()[:2000],assignee=current_user_name() if kind=='my' else owner.strip()[:200] or 'Owner unclear',type=kind,due_date=due_date)
                if source_type is not None or source_url is not None:
                    platform,url=validate_source(source_type if source_type is not None else item.get('source_type','email' if item.get('email_id') else 'other'),source_url if source_url is not None else item.get('source_url',''))
                    item.update(source_type=platform,source_url=url)
                if people is not None:item["co_owners"]=people
                item.update(extras)
                if priority is not None:item['priority']=priority
                if project_id is not None:item['project_id']=project_id
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


def validate_source(source_type,source_url):
    from urllib.parse import urlsplit
    if source_type not in ('email','slack','teams','meeting','other'):raise ValueError('Choose a supported task source.')
    if not isinstance(source_url,str) or len(source_url)>4000:raise ValueError('Use a source link of up to 4,000 characters.')
    value=source_url.strip()
    if value:
        try:parsed=urlsplit(value);valid=parsed.scheme in ('https','http') and bool(parsed.hostname) and not any(c.isspace() or ord(c)<32 for c in value)
        except ValueError:valid=False
        if not valid:raise ValueError('Use a complete http:// or https:// link, such as a Slack message link.')
    return source_type,value


def validate_priority(value):
    if value not in ('none','low','medium','high'):raise ValueError('Choose None, Low, Medium, or High priority.')
    return value


def current_user_name():
    from .config import read_config
    return read_config().get('user_context',{}).get('full_name','').strip() or 'Me'


TASK_COLORS=('none','blue','purple','green','orange','pink')
def validate_task_details(color=None,deadline=None,current=None):
    result={}
    if color is not None:
        if color not in TASK_COLORS:raise ValueError('Choose a supported task color.')
        result['color']=color
    if deadline is not None:
        if not isinstance(deadline,dict) or deadline.get('kind') not in ('date','meeting'):raise ValueError('Choose a date or meeting deadline.')
        if deadline['kind']=='date':result['deadline']={'kind':'date'}
        else:
            offset=deadline.get('offset_minutes',0)
            if type(offset)!=int or offset not in (0,15,30,60,1440):raise ValueError('Choose a supported time before the meeting.')
            from .calendar_cache import snapshot
            try:events=snapshot()['events']
            except (RuntimeError,OSError):
                if not current or current.get('meeting_id')!=deadline.get('meeting_id'):raise ValueError('Calendar unavailable. Refresh Calendar before linking a meeting.')
                events=[]
            event=next((e for e in events if e.get('meeting_id')==deadline.get('meeting_id')),None)
            if not event:
                if current and current.get('meeting_id')==deadline.get('meeting_id') and current.get('offset_minutes')==offset:
                    result['deadline']=dict(current,availability='unavailable')
                else:raise ValueError('This meeting is no longer available. Refresh Calendar and choose a meeting.')
            else:result['deadline']=meeting_deadline(event,offset)
    return result

def meeting_deadline(event,offset):
    from datetime import timedelta
    from .calendar_cache import instant
    return {'kind':'meeting','meeting_id':event['meeting_id'],'subject':event['subject'],
            'start_time':event['start_time'],'offset_minutes':offset,
            'due_at':(instant(event['start_time'])-timedelta(minutes=offset)).isoformat(),'availability':'current'}

@_serialized
def refresh_meeting_deadlines(events):
    lookup={e['meeting_id']:e for e in events if e.get('meeting_id')}
    data=load_tasks();changed=False
    for rows in data.values():
        for task in rows:
            old=task.get('deadline',{})
            if task.get('completed') or old.get('kind')!='meeting':continue
            event=lookup.get(old.get('meeting_id'))
            new=meeting_deadline(event,old.get('offset_minutes',0)) if event else dict(old,availability='unavailable')
            if old!=new:task['deadline']=new;changed=True
    if changed:save_tasks(data)
    return changed
