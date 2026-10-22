"""Local per-task reminders, independent of Bob and browser timers."""
import subprocess
from datetime import datetime,timezone,timedelta
from . import tasks


def validate(value,previous=None):
    if not isinstance(value,dict):raise ValueError('Choose a reminder date and time.')
    at=value.get('at','');repeat=value.get('repeat_days',0)
    if not at:return {}
    if not isinstance(at,str) or len(at)>50 or type(repeat) is not int or not 0<=repeat<=365:raise ValueError('Use a reminder date and a repeat interval from 0 to 365 days.')
    try:
        date=datetime.fromisoformat(at.replace('Z','+00:00'))
        if date.tzinfo is None:raise ValueError()
    except ValueError:raise ValueError('Choose a valid reminder time with a timezone.') from None
    result={'at':date.astimezone(timezone.utc).isoformat(),'repeat_days':repeat}
    if previous and all(previous.get(k)==v for k,v in result.items()):return previous
    return result


def notify(title):
    # User text is an argument, never executable AppleScript.
    script='on run argv\ndisplay notification (item 1 of argv) with title "Outlook Assistant" subtitle "Task reminder"\nend run'
    subprocess.run(['/usr/bin/osascript','-e',script,title[:300]],check=True,capture_output=True,timeout=10)


def check(now=None,send=notify):
    now=now or datetime.now(timezone.utc)
    with tasks._LOCK:
        data=tasks.load_tasks();changed=False
        for group in data.values():
            for task in group:
                reminder=task.get('reminder') or {}
                if task.get('completed') or not reminder.get('at'):continue
                target=reminder.get('next_at') or reminder['at']
                try:due=datetime.fromisoformat(target.replace('Z','+00:00'))
                except (ValueError,TypeError):continue
                if due.tzinfo is None or due>now or (reminder.get('notified_at') and not reminder.get('repeat_days')):continue
                # Record delivery attempts to avoid notification storms when
                # waking after missed days. macOS decides banner visibility.
                try:send(task['text'])
                except (OSError,subprocess.SubprocessError):continue
                reminder['notified_at']=now.isoformat()
                if reminder.get('repeat_days'):reminder['next_at']=(now+timedelta(days=reminder['repeat_days'])).isoformat()
                task['reminder']=reminder;changed=True
        if changed:tasks.save_tasks(data)


def scheduler(stop):
    while not stop.is_set():
        try:check()
        except Exception:pass
        stop.wait(30)
