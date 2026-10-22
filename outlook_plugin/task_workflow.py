from .storage import read_json, write_json
from .config import DATA_DIR
"""Persistent, resumable task review and bounded background scanning."""
from email.utils import parseaddr
import hashlib
import json
import re
from collections import Counter
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
            item.update(status='dismissed',reason=reason,dismissed_at=time.time())
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
            source['source_keys']=item.get('source_keys',[])
            source['description']=str(data.get('description',item.get('description',''))).strip()[:4000]
            # Preserve idempotence even if an accepted suggestion is retried with an edited title.
            existing=load_tasks()
            if not any(t.get('suggestion_id')==item['id'] for group in existing.values() for t in group):
                add_task(kind,title,owner,due,source,source_type=data.get('source_type','email'),source_url=data.get('source_url',''),priority=data.get('priority','none'),project_id=data.get('project_id',''),color=data.get('color','none'),deadline=data.get('deadline'),co_owners=data.get('co_owners'),reminder=data.get('reminder'))
            item.update(status='accepted',description=source['description'],text=title,owner=owner,type=kind,due_date=due)
        else:raise ValueError('Unknown review action.')
        save(store)
    return snapshot()


def key_for(message,opts):
    ctx=read_config().get('user_context',{})
    # Preserve checkpoints from before recipient/coverage metadata was added.
    content={k:message[k] for k in ('id','subject','sender','received_time','content')}
    return hashlib.sha256(json.dumps([content,opts['mode'],ctx],sort_keys=True).encode()).hexdigest()


def source_keys(message):
    """Stable identities survive Outlook row-ID changes without storing headers."""
    keys=[]
    provider=str(message.get('message_id') or '').strip()
    if provider:keys.append('message:'+hashlib.sha256(provider.encode()).hexdigest())
    return keys


def normalized_action(value):
    return ' '.join(re.findall(r"\w+",str(value or '').casefold()))


def same_action(left,right):
    if (left.get('action_type') or 'create')!=(right.get('action_type') or 'create'):return False
    if left.get('action_type')=='complete' and left.get('task_id')!=right.get('task_id'):return False
    a,b=set(left.get('source_keys',[])),set(right.get('source_keys',[]))
    same_source=bool(a&b) if a and b else bool(left.get('email_id') and left.get('email_id')==right.get('email_id'))
    if not same_source:return same_cross_email_action(left,right)
    title_a,title_b=normalized_action(left.get('text')),normalized_action(right.get('text'))
    if title_a and title_a==title_b:return True
    quote_a,quote_b=normalized_action(left.get('evidence')),normalized_action(right.get('evidence'))
    if not quote_a or not quote_b:return False
    if quote_a==quote_b:return True
    # Different quote boundaries are common. Require substantial overlap plus
    # matching action words so distinct requests in one email remain separate.
    words_a,words_b=set(title_a.split()),set(title_b.split())
    overlap=len(words_a&words_b)/max(1,min(len(words_a),len(words_b)))
    return (min(len(quote_a),len(quote_b))>=30 and min(len(quote_a),len(quote_b))/max(len(quote_a),len(quote_b))>=.65
            and (quote_a in quote_b or quote_b in quote_a) and len(words_a&words_b)>=2 and overlap>=.6)


def same_cross_email_action(left,right):
    # Repeated reminders can have new message IDs. Require a shared concrete
    # deadline so recurring work in a later period is not silently suppressed.
    if not left.get('email_id') or not right.get('email_id'):return False
    due=left.get('due_date')
    if not due or due!=right.get('due_date'):return False
    subject=lambda row:normalized_action(re.sub(r'^(?:(?:re|fw|fwd):\s*)+', '',str(row.get('email_subject') or '').strip(),flags=re.I))
    if not subject(left) or subject(left)!=subject(right):return False
    def owner(row):
        return 'self' if row.get('type')=='my' else normalized_action(row.get('owner') or row.get('assignee'))
    if not owner(left) or owner(left)!=owner(right):return False
    title_a,title_b=normalized_action(left.get('text')),normalized_action(right.get('text'))
    quote_a,quote_b=normalized_action(left.get('evidence')),normalized_action(right.get('evidence'))
    verb=lambda title: {'accept':'join','join':'join'}.get(title.split()[0],title.split()[0]) if title else ''
    return (title_a==title_b and len(title_a.split())>=5) or (quote_a==quote_b and len(quote_a)>=60 and verb(title_a)==verb(title_b) and len(set(title_a.split())&set(title_b.split()))>=3)


def remembered_actions(data,saved,messages):
    identities={m.get('source_id',m['id']):source_keys(m) for m in messages}
    result=[]
    for item in list(data['suggestions'].values())+saved:
        row=dict(item)
        if not row.get('source_keys'):row['source_keys']=identities.get(row.get('email_id'),[])
        result.append(row)
    return result


def reviewed_context(history,batch):
    sources={m.get('source_id',m['id']) for m in batch}
    words=set(re.findall(r'\w+', ' '.join(m.get('subject','')+' '+m.get('content','') for m in batch).casefold()))
    reviewed=[r for r in history if r.get('status') in ('dismissed','accepted','review') or 'completed' in r]
    reviewed.sort(key=lambda r:(r.get('email_id') in sources,len(words&set(normalized_action(r.get('text')).split()))),reverse=True)
    result=[];size=0
    for row in reviewed[:200]:
        entry={k:row.get(k,'') for k in ('id','text','email_id','evidence','status','completed','type','owner','assignee','action_type','task_id')}
        for key in ('text','evidence'):entry[key]=str(entry[key])[:600]
        size+=len(json.dumps(entry))
        if size>40000:break
        result.append(entry)
    return result


def candidate_messages(engine,opts,email_id=None):
    backend=engine.get_active_backend()
    if email_id:
        rows=[engine.get_email_details(email_id)]
    else:
        from .local_store import LocalStoreBridge
        # Read bodies in one pass rather than searching the entire cache per email.
        rows=backend.get_cached_messages() if isinstance(backend,LocalStoreBridge) else backend.get_emails(folder='all',limit=100000)
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
        content=message.get('body') or message.get('preview') or ''
        # Overlap protects requests/deadlines split across boundaries. The first
        # segment keeps its old key; newly accessible tails are scanned once.
        starts=range(0,max(1,len(content)-1200),4800)
        for part,start in enumerate(starts):
            source_id=str(message['id'])
            result.append(dict(id=source_id if not part else f'{source_id}::part:{part}',
                source_id=source_id,subject=message.get('subject',''),sender=message.get('sender',''),
                received_time=received,content=content[start:start+6000],
                opening_context=content[:1200] if part else '',
                to=message.get('to',[]),cc=message.get('cc',[]),
                message_id=message.get('message_id',''),
                coverage='body' if message.get('body') else 'preview',part=part+1))
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


def dismissal_context(suggestions,batch):
    """Use the full history for counts and retrieval, with a bounded prompt."""
    rows=[t for t in suggestions.values() if t.get('status')=='dismissed' and t.get('reason') in REASONS and t['reason']!='quick']
    counts=Counter(REASONS[t['reason']] for t in rows)
    stop={'this','that','with','from','have','will','your','please','email','task','send','review','about','next'}
    tokens=lambda value:set(re.findall(r'[a-z0-9]{4,}',value.casefold()))-stop
    context=tokens(' '.join(str(m.get(k,'')) for m in batch for k in ('subject','content','body','sender')))
    ids={str(m.get('id','')) for m in batch}
    def rank(pair):
        index,item=pair
        same=bool(item.get('email_id')) and str(item['email_id']) in ids
        overlap=len(context & tokens(str(item.get('text',''))+' '+str(item.get('email_subject',''))+' '+str(item.get('company',''))))
        stamp=item.get('dismissed_at',0)
        return (same,overlap,stamp if isinstance(stamp,(int,float)) else 0,index)
    ranked=sorted(enumerate(rows),key=rank,reverse=True)
    examples=[];seen=set();size=0
    for _,item in ranked:
        title=str(item.get('text',''))[:300];reason=REASONS[item['reason']]
        key=(' '.join(title.casefold().split()),reason)
        if key in seen:continue
        example={'text':title,'reason':reason}
        cost=len(json.dumps(example,ensure_ascii=False))
        if size+cost>24000:continue
        examples.append(example);seen.add(key);size+=cost
        if len(examples)>=100:break
    return examples,{'total':len(rows),'by_reason':dict(counts),'examples_included':len(examples)}


def run(engine,opts,email_id=None):
    if not email_id:
        with _LOCK:
            checkpoint=load()
            if not checkpoint.get('initial_since'):
                checkpoint['initial_since']=opts['since'];save(checkpoint)
    messages=candidate_messages(engine,opts,email_id)
    data=load();pending=[m for m in messages if key_for(m,opts) not in data['processed']]
    with _LOCK:JOB.update(total=len(pending),message=f'{len(pending)} new or changed email sections to review.')
    spent=0;ai=BobAIAgent()
    for offset in range(0,len(pending),10):
        if _STOP.is_set():
            with _LOCK:JOB.update(status='stopped',message='Stopped. Start another scan to resume remaining messages.')
            return
        batch=pending[offset:offset+10]
        with _LOCK:JOB['message']=f'Reviewing email sections {offset+1}–{offset+len(batch)} of {len(pending)}…'
        current=load()
        feedback,feedback_summary=dismissal_context(current['suggestions'],batch)
        saved=[t for rows in load_tasks().values() for t in rows]
        active=[t for t in saved if not t.get('completed')][:200]
        history=remembered_actions(current,saved,messages)
        found=ai.extract_tasks(batch,mode=opts['mode'],feedback=feedback,active_tasks=active,feedback_summary=feedback_summary,reviewed_actions=reviewed_context(history,batch))+ai.last_completions
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
            historical=remembered_actions(data,[t for rows in existing.values() for t in rows],messages)
            for old in historical:
                if old.get('id') in data['suggestions'] and old.get('source_keys'):data['suggestions'][old['id']]['source_keys']=old['source_keys']
            known={(t.get('email_id'),' '.join(t['text'].lower().split())) for group in existing.values() for t in group}
            for item in found:
                # Stable evidence identity suppresses rephrased suggestions and remembered dismissals.
                source=sources[item['email_id']]
                item['email_id']=source.get('source_id',source['id'])
                item['source_keys']=source_keys(source)
                if any(same_action(item,previous) for previous in historical):continue
                normalized=' '.join(item['evidence'].casefold().split())
                # Only deduplicate copies with a provider message ID and the
                # same evidence; similar recurring requests must remain separate.
                provider_id=source.get('message_id')
                duplicate_key=hashlib.sha256((str(provider_id)+'\n'+normalized+'\n'+item.get('task_id','')).encode()).hexdigest() if provider_id else ''
                if duplicate_key and any(s.get('duplicate_key')==duplicate_key and s.get('action_type')==item.get('action_type') for s in data['suggestions'].values()):continue
                if duplicate_key:item['duplicate_key']=duplicate_key
                sid=hashlib.sha256((item['email_id']+'\n'+normalized+('\ncomplete:'+item['task_id'] if item.get('action_type')=='complete' else '')).encode()).hexdigest()[:24]
                if sid in data['suggestions']:continue
                domain=parseaddr(source['sender'])[1].rsplit('@',1)[-1].lower()
                item.update(created_at=datetime.now().astimezone().isoformat(),id=sid,status='accepted' if (item['email_id'],' '.join(item['text'].lower().split())) in known else 'review',reason='',company=links.get(domain,''))
                data['suggestions'][sid]=item
                historical.append(item)
            rejected=getattr(ai,'last_rejected_sources',set())
            for m in batch:
                if m['id'] not in rejected:data['processed'][key_for(m,opts)]={'email_id':m.get('source_id',m['id']),'checked':datetime.now().isoformat()}
            data['last_check']=datetime.now().isoformat();save(data)
            JOB.update(scanned=offset+len(batch),usage=round(spent,6))
        if rejected:
            raise RuntimeError('Some task suggestions could not be verified against their emails. Valid suggestions were saved; unverified emails will be retried on the next scan.')
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
