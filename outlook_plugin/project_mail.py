"""Project mail combines live task references with explicitly saved links."""
from . import projects, tasks
from .config import _LOCK, update_config
from .local_store import LocalStoreBridge
from .mail_filters import visible_messages


def project(identifier):
    value=next((p for p in projects.list_projects() if p['id']==identifier),None)
    if value is None:raise ValueError('Project not found.')
    return value


def listing(engine,identifier,query='',offset=0,limit=25,discover=False):
    current=project(identifier)
    direct=set(current.get('email_ids',[]));related={}
    for group in tasks.load_tasks().values():
        for task in group:
            if task.get('project_id')==identifier and task.get('email_id'):
                related.setdefault(str(task['email_id']),[]).append(task['id'])
    ids=direct|set(related)
    backend=engine.get_active_backend()
    rows=backend.get_cached_messages() if isinstance(backend,LocalStoreBridge) else backend.get_emails(folder='all',limit=100000)
    rows=visible_messages(rows)
    result=[];seen=set();needle=query.strip().casefold()
    for message in rows:
        ident=str(message['id'])
        if ident in seen or (not discover and ident not in ids):continue
        seen.add(ident)
        if needle and needle not in '\n'.join(str(message.get(k,'')) for k in ('subject','sender','body','preview')).casefold():continue
        result.append(dict(id=ident,subject=message.get('subject',''),sender=message.get('sender',''),received_time=message.get('received_time',''),available=True,direct=ident in direct,task_ids=related.get(ident,[]),associated=ident in ids))
    if not discover and not needle:
        # Retain the association when cache content is absent or excluded, but
        # never reveal a previously saved subject from an excluded sender.
        for ident in ids-seen:
            result.append(dict(id=ident,subject='Email unavailable',sender='',received_time='',available=False,direct=ident in direct,task_ids=related.get(ident,[]),associated=True))
    result.sort(key=lambda m:(m['received_time'],m['id']),reverse=True)
    offset=max(0,int(offset));limit=max(1,min(100,int(limit)))
    return {'items':result[offset:offset+limit],'total':len(result),'offset':offset,'limit':limit}


def link(engine,identifier,email_id,remove=False):
    if not isinstance(email_id,str) or not 1<=len(email_id)<=1000:raise ValueError('Choose an email.')
    if not remove:
        message=engine.get_email_details(email_id)
        if not message or not visible_messages([message]):raise ValueError('This email is not available in the local cache.')
    with _LOCK:
        rows=projects.list_projects();current=next((p for p in rows if p['id']==identifier),None)
        if current is None:raise ValueError('Project not found.')
        ids=list(dict.fromkeys(current.get('email_ids',[])))
        if remove:ids=[i for i in ids if i!=email_id]
        elif email_id not in ids:
            if len(ids)>=5000:raise ValueError('This project already has 5,000 directly linked emails.')
            ids.append(email_id)
        current['email_ids']=ids;update_config({'projects':rows})
    return {'linked':not remove}
