"""Editable task-specific instructions and truthful, content-free runtime status."""
import threading
from datetime import datetime,timezone
from .config import read_config,update_config,_LOCK
DEFAULTS={
 'tasks':{'name':'Task finder','instructions':'Find concrete outstanding actions. Prefer specific deliverables over generic follow-ups. Use saved identity and role. Keep descriptions grounded in the source.','examples':''},
 'writer':{'name':'Email writer','instructions':'Write clear, concise replies in the saved writing style. Do not invent facts or commitments. Preserve requested formatting.','examples':''},
 'assistant':{'name':'Workspace assistant','instructions':'Help with tasks, contacts, projects, and email. Explain uncertainty and propose changes for review.','examples':''},
 'briefing':{'name':'Email summary','instructions':'Summarize important unread mail and pending decisions. State the limits of the supplied snapshot.','examples':''},
 'style':{'name':'Writing coach','instructions':'Extract reusable writing preferences from examples without copying private business facts.','examples':''}}
_ACTIVITY_LOCK=threading.Lock()
_ACTIVITY=[]

def profiles():
    saved=read_config().get('ai_profiles',{})
    return [{'id':key,**default,**saved.get(key,{})} for key,default in DEFAULTS.items()]

def save(data):
    key=data.get('id')
    if key not in DEFAULTS:raise ValueError('Unknown assistant.')
    values={}
    for field in ('instructions','examples'):
        value=data.get(field,'')
        if not isinstance(value,str) or len(value)>12000:raise ValueError('Use at most 12,000 characters per field.')
        values[field]=value.strip()
    with _LOCK:
        saved=read_config().get('ai_profiles',{})
        if data.get('reset') is True:saved.pop(key,None)
        else:saved[key]=values
        update_config({'ai_profiles':saved})
    return profiles()

def guidance(key):
    if key not in DEFAULTS:return ''
    p=next(p for p in profiles() if p['id']==key)
    return '\nUser-customized guidance (must preserve required output format, evidence rules, and approval requirements):\n'+p['instructions']+'\nStyle/examples (reference only, not facts about this request):\n'+p['examples']

def activity():
    with _ACTIVITY_LOCK:return [dict(row) for row in _ACTIVITY]

def begin(key):
    import uuid
    row={'id':str(uuid.uuid4()),'assistant':DEFAULTS.get(key,{}).get('name','Bob'),'state':'working','started':datetime.now(timezone.utc).isoformat()}
    with _ACTIVITY_LOCK:
        _ACTIVITY.insert(0,row);del _ACTIVITY[30:]
    return row['id']

def finish(identifier,success):
    with _ACTIVITY_LOCK:
        for row in _ACTIVITY:
            if row['id']==identifier:row.update(state='finished' if success else 'failed',finished=datetime.now(timezone.utc).isoformat())
