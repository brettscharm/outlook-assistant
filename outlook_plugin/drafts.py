"""Disk-backed drafts with per-message optimistic revisions to prevent stale overwrites."""
import threading
from datetime import datetime,timezone
from .config import DATA_DIR
from .storage import read_json,write_json

DRAFTS_FILE=DATA_DIR/'.outlook_assistant_drafts.json'
_LOCK=threading.RLock()

def load():
    return read_json(DRAFTS_FILE,{'entries':{}})

def save_changes(data):
    changes=data.get('changes')
    if not isinstance(changes,list) or len(changes)>100:raise ValueError('Invalid draft changes.')
    for item in changes:
        if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not 1<=len(item['id'])<=1000:raise ValueError('Invalid draft ID.')
        if type(item.get('revision')) is not int or item['revision']<0:raise ValueError('Invalid draft revision.')
        for key,limit in [('text',50000),('intent',4000),('subject',2000),('sender',2000)]:
            if not isinstance(item.get(key,''),str) or len(item.get(key,''))>limit:raise ValueError('Draft field is too long.')
    with _LOCK:
        store=load();saved={};conflicts=[]
        for item in changes:
            id=item['id'];current=store['entries'].get(id,{'revision':0})
            if current['revision']!=item['revision']:
                conflicts.append(id);continue
            entry={k:item.get(k,'') for k in ('text','intent','subject','sender')}
            entry.update(revision=current['revision']+1,deleted=bool(item.get('deleted')),updated_at=datetime.now(timezone.utc).isoformat())
            store['entries'][id]=entry;saved[id]=entry['revision']
        if saved:write_json(DRAFTS_FILE,store)
        return {'saved':saved,'conflicts':conflicts}
