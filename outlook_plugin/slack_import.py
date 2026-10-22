"""Local, explicit Slack imports. No Slack credentials, cache scraping or live syncing."""
import hashlib
import html
import json
import re
import threading
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from .config import DATA_DIR
from .storage import read_json, write_json

FILE=DATA_DIR/'.outlook_assistant_slack.json'
_LOCK=threading.RLock()

def load():return read_json(FILE,{'messages':{},'users':{}})

def field(value,limit,label):
    if not isinstance(value,str) or len(value)>limit:raise ValueError(f'{label} must be text up to {limit:,} characters.')
    return value.strip()

def safe_link(value):
    value=field(value,4000,'Slack link')
    if value:
        url=urlparse(value)
        if url.scheme!='https' or not url.hostname or not url.hostname.endswith('.slack.com') or url.username or url.password:raise ValueError('Use an https Slack message link.')
    return value

def readable(value,users):
    value=re.sub(r'<@([A-Z0-9]+)>',lambda m:'@'+users.get(m[1],m[1]),value)
    value=re.sub(r'<(https?://[^>|]+)(?:\|([^>]+))?>',lambda m:(m[2]+' ('+m[1]+')') if m[2] else m[1],value)
    return html.unescape(value)

def import_messages(data):
    workspace=field(data.get('workspace',''),100,'Workspace');channel=field(data.get('channel',''),150,'Conversation')
    if not workspace:raise ValueError('Enter a workspace name.')
    payload=data.get('messages');paste=field(data.get('text',''),100000,'Pasted conversation');link=safe_link(data.get('url',''))
    if payload is not None and (not isinstance(payload,list) or len(payload)>5000):raise ValueError('Choose a JSON array of up to 5,000 messages or users.')
    if len(json.dumps(data).encode())>1100000:raise ValueError('Import at most 1 MB at a time.')
    with _LOCK:
        saved=load();users=saved.setdefault('users',{}).setdefault(workspace.casefold(),{})
        if payload and all(isinstance(row,dict) and 'id' in row and 'profile' in row for row in payload):
            for row in payload:
                profile=row.get('profile') or {}
                if not isinstance(profile,dict):raise ValueError('Invalid Slack user profile.')
                users[field(row['id'],100,'User ID')]=field(profile.get('real_name') or profile.get('display_name') or row.get('name',''),200,'User name')
            write_json(FILE,saved);return {'added':0,'updated':0,'users':len(payload),'skipped':0}
        if not channel:raise ValueError('Enter the channel or conversation name.')
        if paste and payload:raise ValueError('Paste text or choose JSON files, not both.')
        if not paste and not payload:raise ValueError('Paste a conversation or select message JSON files.')
        rows=payload or [{'text':paste,'url':link}];added=updated=skipped=0
        conversation=workspace.casefold()+'\n'+channel.casefold()
        for row in rows:
            if not isinstance(row,dict):raise ValueError('Each Slack message must be an object.')
            body=field(row.get('text',''),100000,'Message')
            if not body:skipped+=1;continue
            stamp=field(row.get('ts',''),40,'Message timestamp');occurred=''
            if stamp:
                try:
                    number=Decimal(stamp)
                    if not number.is_finite() or number<0:raise ValueError()
                    occurred=datetime.fromtimestamp(float(number),timezone.utc).isoformat()
                except (ValueError,OverflowError,OSError,InvalidOperation):raise ValueError('Invalid Slack timestamp.') from None
            identity=stamp or hashlib.sha256(body.encode()).hexdigest()
            key=hashlib.sha256((conversation+'\n'+identity).encode()).hexdigest()
            entry=dict(id=key,conversation=conversation,workspace=workspace,channel=channel,text=body,user=field(row.get('user') or row.get('username') or 'Unknown sender',200,'Sender'),occurred_at=occurred,url=safe_link(row.get('url',link)),thread_ts=field(row.get('thread_ts',''),40,'Thread timestamp'))
            old=saved['messages'].get(key)
            if old==entry:skipped+=1;continue
            if old:updated+=1
            else:added+=1
            saved['messages'][key]=entry
        write_json(FILE,saved)
        return {'added':added,'updated':updated,'skipped':skipped,'users':0}

def documents():
    saved=load();rows=[]
    for row in saved['messages'].values():
        users=saved.get('users',{}).get(row['workspace'].casefold(),{})
        rows.append(dict(row,sender=users.get(row['user'],row['user']),text=readable(row['text'],users)))
    return rows

def listing(query='',conversation='',offset=0):
    rows=documents();conversations=sorted({(r['conversation'],r['workspace']+' · '+r['channel']) for r in rows},key=lambda r:r[1].casefold())
    query=str(query).strip().casefold()
    rows=[r for r in rows if (not conversation or r['conversation']==conversation) and (not query or query in (r['id']+' '+r['text']+' '+r['sender']+' '+r['channel']).casefold())]
    rows.sort(key=lambda r:(r['occurred_at'],r['id']),reverse=True);offset=max(0,int(offset))
    return {'items':rows[offset:offset+30],'total':len(rows),'conversations':[{'id':i,'name':n} for i,n in conversations]}
