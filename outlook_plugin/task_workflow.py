from .storage import read_json, write_json
from .config import DATA_DIR
"""Persistent, resumable task review and bounded background scanning."""
from email.utils import parseaddr
import hashlib
import json
import os
import tempfile
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from .config import read_config, update_config
from .ai_agent import BobAIAgent, get_bob_api_key, _BOB_LOCK
from . import bob_status
from .tasks import load_tasks, add_task, current_user_name

WORKFLOW_FILE=DATA_DIR/'.outlook_assistant_task_review.json'
_LOCK=threading.RLock()
_RUN=threading.Lock()
_STOP=threading.Event()
JOB={'running':False,'status':'idle','scanned':0,'total':0,'usage':0,'message':''}
REASONS={'quick':'Dismissed without feedback','not_mine':'Not my task','not_role':'Not relevant to my role','done':'Already done','duplicate':'Duplicate','not_action':'Not a real action item'}


def load():
    return read_json(WORKFLOW_FILE,{'suggestions':{},'processed':{},'last_check':None})

def save(data):
    write_json(WORKFLOW_FILE,data)


def options():
    saved={k:v for k,v in read_config().get('task_scan',{}).items() if k != 'budget'}
    since=saved.get('since') or load().get('initial_since') or (date.today()-timedelta(days=7)).isoformat()
    return dict({'since':since,'mode':'mine','interval':15,'excluded_domains':[]},**saved)


def validate_options(data):
    opts=options()
    for key in ('since','mode','interval','excluded_domains'):
        if key in data:opts[key]=data[key]
    from .mail_filters import normalize_domains
    opts['excluded_domains']=normalize_domains(opts.get('excluded_domains',[]))
    date.fromisoformat(opts['since'])
    if opts['since']>date.today().isoformat():raise ValueError('Choose a start date on or before today.')
    if opts['mode'] not in ('mine','all'):raise ValueError('Choose My tasks or All email tasks.')
    if opts['interval'] not in (0,15,30,60):raise ValueError('Choose a supported check interval.')
    return opts


def identity_ready():
    ctx=read_config().get('user_context',{})
    return bool(ctx.get('full_name','').strip() and '@' in ctx.get('email_addresses',''))


def settings(data):
    opts=validate_options(data)
    update_config({'task_scan':opts})
    if not opts['interval'] and _RUN.locked():stop()
    return opts


def automatic_state():
    if not options()['interval']:return 'paused'
    if not identity_ready():return 'identity'
    if bob_status.current(get_bob_api_key())['state']!='connected':return 'bob'
    return 'ready'


def snapshot(email_id=None):
    data=load()
    with _LOCK:job=dict(JOB)
    items=list(data['suggestions'].values())
    saved=load_tasks()
    linked={t.get('suggestion_id'):t for group in saved.values() for t in group if t.get('suggestion_id')}
    for item in items:
        if item['status']=='review' and item.get('type') in ('unclear','my'):
            item.update(type='my',owner=current_user_name())
        if item['status']=='accepted' and item['id'] in linked:
            task=linked[item['id']]
            item.update(project_id=task.get('project_id',''),priority=task.get('priority','none'),text=task['text'],description=task.get('description',''),source_type=task.get('source_type','email'),source_url=task.get('source_url',''),owner=task.get('assignee','Owner unclear'),type=task.get('type',item['type']),due_date=task.get('due_date',''),completed=task.get('completed',False))
    if email_id:items=[t for t in items if t['email_id']==email_id]
    return {'suggestions':items,'job':job,'options':options(),'last_check':data.get('last_check'),
            'identity_ready':identity_ready(),'automatic_state':automatic_state(),'reasons':REASONS,
            'email_scanned':any(p.get('email_id')==email_id for p in data['processed'].values()) if email_id else False}


def action(data):
    with _LOCK:
        store=load();item=store['suggestions'].get(str(data.get('id','')))
        if not item:raise ValueError('Suggestion not found.')
        act=data.get('action')
        if act=='dismiss':
            reason=data.get('reason')
            if reason not in REASONS:raise ValueError('Choose a dismissal reason.')
            item.update(status='dismissed',reason=reason)
        elif act=='restore':item.update(status='review',reason='')
        elif act=='accept' and item.get('action_type')=='complete':
            from . import tasks
            with tasks._LOCK:
                task=next((t for rows in tasks.load_tasks().values() for t in rows if t['id']==item['task_id']),None)
                if task is None:raise ValueError('This task no longer exists.')
                if not task.get('completed'):
                    if hashlib.sha256(json.dumps(task,sort_keys=True).encode()).hexdigest()!=item['expected']:raise ValueError('This task changed. Review it on your board before marking it done.')
                    tasks.move_task(task['id'],'done')
                item.update(status='accepted',completed=True)
        elif act=='accept':
            title=str(data.get('text',item['text'])).strip()[:2000]
            owner=str(data.get('owner',item['owner'])).strip()[:200]
            kind=data.get('type','my' if item['type']=='unclear' else item['type']);due=str(data.get('due_date',item.get('due_date','')))
            if not title:raise ValueError('Enter a task title.')
            if kind not in ('my','others','unclear'):raise ValueError('Choose an owner group.')
            if kind=='my':owner=current_user_name()
            if due:date.fromisoformat(due)
            source={k:item.get(k,'') for k in ('email_id','email_subject','evidence','owner_evidence','due_evidence','due_note','company')}
            source['suggestion_id']=item['id']
            source['description']=str(data.get('description',item.get('description',''))).strip()[:4000]
            # Preserve idempotence even if an accepted suggestion is retried with an edited title.
            existing=load_tasks()
            if not any(t.get('suggestion_id')==item['id'] for group in existing.values() for t in group):
                add_task(kind,title,owner,due,source,source_type=data.get('source_type','email'),source_url=data.get('source_url',''),priority=data.get('priority','none'),project_id=data.get('project_id',''),color=data.get('color','none'),deadline=data.get('deadline'),co_owners=data.get('co_owners'))
            item.update(status='accepted',description=source['description'],text=title,owner=owner,type=kind,due_date=due)
        else:raise ValueError('Unknown review action.')
        save(store)
    return snapshot()


def key_for(message,opts):
    ctx=read_config().get('user_context',{})
    return hashlib.sha256(json.dumps([message,opts['mode'],ctx],sort_keys=True).encode()).hexdigest()


def candidate_messages(engine,opts,email_id=None):
    backend=engine.get_active_backend()
    if email_id:
        rows=[engine.get_email_details(email_id)]
    else:
        from .local_store import LocalStoreBridge
        rows=backend.get_emails(folder='all',limit=None if isinstance(backend,LocalStoreBridge) else 100000)
    result=[]
    for row in rows:
        if not row:continue
        received=str(row.get('received_time',''))
        try:received_day=datetime.fromisoformat(received.replace('Z','+00:00')).astimezone().date().isoformat()
        except (ValueError,TypeError):received_day=''
        if not email_id and (not received_day or received_day<opts['since']):continue
        message=row if 'body' in row else engine.get_email_details(str(row['id']))
        if not message:continue
        domain=parseaddr(message.get('sender',''))[1].rsplit('@',1)[-1].lower().rstrip('.')
        if any(domain==rule or domain.endswith('.'+rule) for rule in opts.get('excluded_domains',[])):continue
        result.append(dict(id=str(message['id']),subject=message.get('subject',''),sender=message.get('sender',''),
            received_time=received,content=(message.get('body') or message.get('preview') or '')[:6000]))
    return sorted(result,key=lambda m:m['received_time'],reverse=True)


def sync_tasks(engine, automatic=False):
    """Refresh discovery without duplicating an active scan or changing preferences."""
    if automatic and not options()['interval']:
        return {'state':'paused','message':'Automatic task discovery is paused.'}
    if not identity_ready():
        return {'state':'setup','message':'Add your name and email in My context to check tasks.'}
    if not get_bob_api_key():
        return {'state':'setup','message':'Add your Bob API key in Settings to check tasks.'}
    if _RUN.locked():
        return {'state':'running','message':'Task check is already running.'}
    if _BOB_LOCK.locked():
        return {'state':'busy','message':'Mail synced. Bob is busy; try Sync now again when it finishes.'}
    from .ai_agent import bob_compatibility
    compatibility=bob_compatibility()
    if not compatibility['ready']:
        return {'state':'setup','message':compatibility['detail']}
    if automatic and automatic_state()!='ready':
        return {'state':'setup','message':'Test your Bob connection in Settings to resume task discovery.'}
    try:
        start(engine)
    except ValueError:
        if _RUN.locked():return {'state':'running','message':'Task check is already running.'}
        raise
    return {'state':'running','message':'Mail synced. Checking new and changed emails for tasks…'}


def start(engine,settings_override=None,email_id=None):
    opts=validate_options(settings_override or {})
    if not identity_ready():raise ValueError('First save your name and email addresses in My context so Bob can identify your tasks.')
    if not _RUN.acquire(blocking=False):raise ValueError('A task scan is already running.')
    _STOP.clear()
    with _LOCK:JOB.update(running=True,status='running',scanned=0,total=0,usage=0,message='Finding cached emails in your date range…')
    def worker():
        try:run(engine,opts,email_id)
        except Exception as exc:
            with _LOCK:JOB.update(status='error',message=str(exc)[:400])
        finally:
            with _LOCK:JOB['running']=False
            _RUN.release()
    threading.Thread(target=worker,daemon=True).start()
    return snapshot()


def stop():
    _STOP.set()
    with _LOCK:JOB['message']='Stopping after the current batch. Completed work is saved.'
    return snapshot()


def run(engine,opts,email_id=None):
    if not email_id:
        with _LOCK:
            checkpoint=load()
            if not checkpoint.get('initial_since'):
                checkpoint['initial_since']=opts['since'];save(checkpoint)
    messages=candidate_messages(engine,opts,email_id)
    data=load();pending=[m for m in messages if key_for(m,opts) not in data['processed']]
    with _LOCK:JOB.update(total=len(pending),message=f'{len(pending)} new or changed cached emails to review.')
    spent=0;ai=BobAIAgent()
    for offset in range(0,len(pending),10):
        if _STOP.is_set():
            with _LOCK:JOB.update(status='stopped',message='Stopped. Start another scan to resume remaining messages.')
            return
        batch=pending[offset:offset+10]
        with _LOCK:JOB['message']=f'Reviewing emails {offset+1}–{offset+len(batch)} of {len(pending)}…'
        current=load()
        feedback=[dict(text=t['text'],reason=REASONS.get(t.get('reason'),'Dismissed')) for t in current['suggestions'].values() if t['status']=='dismissed' and t.get('reason') not in ('quick','')][-20:]
        active=[t for rows in load_tasks().values() for t in rows if not t.get('completed')][:200]
        found=ai.extract_tasks(batch,mode=opts['mode'],feedback=feedback,active_tasks=active)+ai.last_completions
        reported=ai.last_usage.get('session_costs',0)
        try:cost=max(0,float(reported))
        except (TypeError,ValueError):cost=0
        spent+=cost
        links=read_config().get('domain_companies',{})
        from email.utils import parseaddr
        sources={m['id']:m for m in batch}
        with _LOCK:
            data=load()
            existing=load_tasks()
            known={(t.get('email_id'),' '.join(t['text'].lower().split())) for group in existing.values() for t in group}
            for item in found:
                # Stable evidence identity suppresses rephrased suggestions and remembered dismissals.
                normalized=' '.join(item['evidence'].casefold().split())
                sid=hashlib.sha256((item['email_id']+'\n'+normalized+('\ncomplete:'+item['task_id'] if item.get('action_type')=='complete' else '')).encode()).hexdigest()[:24]
                if sid in data['suggestions']:continue
                domain=parseaddr(sources[item['email_id']]['sender'])[1].rsplit('@',1)[-1].lower()
                item.update(id=sid,status='accepted' if (item['email_id'],' '.join(item['text'].lower().split())) in known else 'review',reason='',company=links.get(domain,''))
                data['suggestions'][sid]=item
            for m in batch:data['processed'][key_for(m,opts)]={'email_id':m['id'],'checked':datetime.now().isoformat()}
            data['last_check']=datetime.now().isoformat();save(data)
            JOB.update(scanned=offset+len(batch),usage=round(spent,6))
    with _LOCK:
        data=load();data['last_check']=datetime.now().isoformat();save(data)
        JOB.update(status='complete',message='Scan complete. Review new suggestions below.' if pending else 'No new or changed cached messages in this range.')


def scheduler(engine,shutdown):
    last_attempt=None
    last_poll=None
    observed=None
    while not shutdown.wait(15):
        opts=options()
        if not opts['interval']:
            last_attempt=None;last_poll=None;observed=None
            continue
        if automatic_state()!='ready' or _RUN.locked() or _BOB_LOCK.locked():continue
        now=time.monotonic()
        if last_poll is not None and now-last_poll<60:continue
        last_poll=now
        try:
            data=load()
            keys={key_for(m,opts) for m in candidate_messages(engine,opts)}
            pending=keys-set(data['processed'])
            arrivals=pending-(observed if observed is not None else set())
            observed=keys
            if not pending:continue  # Local checks never spend Bobcoins when nothing changed.
            elapsed=float('inf')
            if data.get('last_check'):
                try:elapsed=(datetime.now().astimezone()-datetime.fromisoformat(data['last_check']).astimezone()).total_seconds()
                except (ValueError,TypeError):pass
            due=(last_attempt is None or now-last_attempt>=opts['interval']*60) and elapsed>=opts['interval']*60
            if not arrivals and not due:continue
            last_attempt=now
            start(engine,opts)
        except Exception as exc:
            with _LOCK:JOB.update(status='error',message=str(exc)[:400])
