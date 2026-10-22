"""Resolve stale local row IDs without guessing from subjects alone."""
import hashlib
from .config import DATA_DIR
from .storage import read_json,write_json

REFERENCES_FILE=DATA_DIR/'.outlook_assistant_mail_references.json'


def remember(profile,rows):
    data=read_json(REFERENCES_FILE,{})
    key=hashlib.sha256(str(profile).encode()).hexdigest()
    refs=data.setdefault(key,{})
    changed=False
    for row in rows:
        provider=str(row.get('message_id') or '').strip()
        if not provider:continue
        identity=hashlib.sha256(provider.encode()).hexdigest()
        if refs.get(str(row['id']))!=identity:
            refs[str(row['id'])]=identity;changed=True
    if changed:
        # Keep recent identities, including rows no longer in the cache.
        data[key]=dict(list(refs.items())[-50000:])
        write_json(REFERENCES_FILE,data)


def recover(row_id,profile,rows):
    from .tasks import load_tasks
    from .task_workflow import load
    key=hashlib.sha256(str(profile).encode()).hexdigest()
    identity=read_json(REFERENCES_FILE,{}).get(key,{}).get(str(row_id))
    records=[t for group in load_tasks().values() for t in group]+list(load()['suggestions'].values())
    related=[t for t in records if str(t.get('email_id',''))==str(row_id)]
    identities={identity} if identity else set()
    for item in related:
        identities.update(s[8:] for s in item.get('source_keys',[]) if s.startswith('message:'))
    matches=[m for m in rows if m.get('message_id') and hashlib.sha256(str(m['message_id']).strip().encode()).hexdigest() in identities]
    providers={str(m['message_id']).strip() for m in matches}
    if len(providers)==1:return dict(matches[0],recovered_from=str(row_id))
    return None
