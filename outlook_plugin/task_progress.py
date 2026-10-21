"""Atomic per-task progress changes. Notes and checklist entries use stable IDs."""
import uuid
from datetime import datetime, timezone
from . import tasks


def text(value, limit, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError('Enter valid text' + (' (required).' if required else '.'))
    return value.strip()


def change(task_id, action, data):
    with tasks._LOCK:
        saved = tasks.load_tasks()
        task = next((t for rows in saved.values() for t in rows if t['id'] == task_id), None)
        if not task:
            raise ValueError('Task not found.')
        if action == 'set_waiting':
            task['waiting_on'] = text(data.get('waiting_on', ''), 300)
            task['next_step'] = text(data.get('next_step', ''), 2000)
        elif action in ('add_update', 'add_subtask'):
            key = 'updates' if action == 'add_update' else 'subtasks'
            entries = task.setdefault(key, [])
            identifier = text(data.get('request_id', ''), 100, True)
            if any(row['id'] == identifier for row in entries):
                return saved
            if len(entries) >= (1000 if key == 'updates' else 200):
                raise ValueError('This task has reached its ' + key + ' limit.')
            entry = {'id': identifier, 'text': text(data.get('text'), 4000 if key == 'updates' else 500, True),
                     'created_at': datetime.now(timezone.utc).isoformat()}
            if key == 'subtasks':
                entry['completed'] = False
            else:
                entry['author'] = tasks.current_user_name()
            entries.append(entry)
        elif action == 'set_subtask':
            entry = next((s for s in task.get('subtasks', []) if s['id'] == data.get('subtask_id')), None)
            if entry is None:
                raise ValueError('This checklist step no longer exists.')
            if not isinstance(data.get('completed'), bool):
                raise ValueError('Choose a completion state.')
            entry['completed'] = data['completed']
        else:
            raise ValueError('Unknown progress action.')
        task['updated_at'] = datetime.now(timezone.utc).isoformat()
        tasks.save_tasks(saved)
        return saved


def export_task(task_id):
    """Explicit handoff excludes mailbox IDs, evidence and private update history."""
    with tasks._LOCK:
        task = next((t for rows in tasks.load_tasks().values() for t in rows if t['id'] == task_id), None)
        if task is None:
            raise ValueError('Task not found.')
        return {'format': 'outlook-task-handoff', 'version': 1, 'handoff_id': task['id'],
                'task': {k: task.get(k, '') for k in ('text', 'description', 'due_date', 'priority', 'source_type', 'source_url')},
                'subtasks': [s['text'] for s in task.get('subtasks', [])]}


def import_task(payload):
    if not isinstance(payload, dict) or payload.get('format') != 'outlook-task-handoff' or payload.get('version') != 1:
        raise ValueError('Choose an Outlook Assistant task handoff file.')
    item = payload.get('task')
    if not isinstance(item, dict):
        raise ValueError('Invalid task handoff.')
    title = text(item.get('text'), 2000, True)
    description = text(item.get('description', ''), 4000)
    due = text(item.get('due_date', ''), 10)
    if due:
        from datetime import date
        date.fromisoformat(due)
    identifier = text(payload.get('handoff_id'), 100, True)
    steps = payload.get('subtasks', [])
    if not isinstance(steps, list) or len(steps) > 200:
        raise ValueError('Invalid checklist.')
    steps = [text(s, 500, True) for s in steps]
    with tasks._LOCK:
        # A handoff imports once on this laptop, even if opened repeatedly.
        import hashlib
        key = 'handoff-' + hashlib.sha256(identifier.encode()).hexdigest()
        data = tasks.add_task('my', title, due_date=due, description=description, request_id=key,
                              priority=item.get('priority', 'none'), source_type=item.get('source_type') or 'other', source_url=item.get('source_url', ''))
        task = next(t for rows in data.values() for t in rows if t['id'] == key)
        if 'subtasks' not in task:
            task['subtasks'] = [{'id': str(uuid.uuid4()), 'text': s, 'completed': False} for s in steps]
            tasks.save_tasks(data)
        return data
