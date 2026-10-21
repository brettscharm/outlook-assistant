"""Local aggregate usage, without prompts, message content, credentials or Bob responses."""
import math
import shutil
import threading
from datetime import datetime, timezone
from .config import DATA_DIR
from .storage import read_json, write_json
USAGE_FILE=DATA_DIR/'.outlook_assistant_usage.json'
_LOCK=threading.RLock()
LAST_ERROR=False

TOKEN_FIELDS=('input_tokens','output_tokens','cache_read_tokens','cache_write_tokens')

def empty():
    result=dict(requests=0,succeeded=0,failed=0,reported_units=0,unreported=0)
    for field in TOKEN_FIELDS:
        result[field]=0;result[field+'_reports']=0
    return result

def normalized(bucket):
    return {**empty(),**bucket}

def record(success,stats):
    global LAST_ERROR
    value=stats.get('session_costs') if isinstance(stats,dict) else None
    try:
        cost=float(value) if value is not None and not isinstance(value,bool) else None
        if cost is not None and (not math.isfinite(cost) or cost<0):cost=None
    except (ValueError,TypeError):cost=None
    now=datetime.now(timezone.utc).isoformat();day=now[:10]
    try:
        with _LOCK:
            data=read_json(USAGE_FILE,{'started_at':now,'total':empty(),'days':{}})
            for bucket in (data['total'],data['days'].setdefault(day,empty())):
                for field,default in empty().items():bucket.setdefault(field,default)
                for field in TOKEN_FIELDS:
                    value=stats.get(field) if isinstance(stats,dict) else None
                    if type(value) is int and value>=0:
                        bucket[field]+=value;bucket[field+'_reports']+=1
                bucket['requests']+=1;bucket['succeeded' if success else 'failed']+=1
                if cost is None:bucket['unreported']+=1
                else:bucket['reported_units']=round(bucket['reported_units']+cost,6)
            data['days']={key:data['days'][key] for key in sorted(data['days'])[-93:]}
            data['last_request_at']=now
            write_json(USAGE_FILE,data)
        LAST_ERROR=False
    except (OSError,ValueError,TypeError,KeyError,OverflowError):LAST_ERROR=True

def snapshot():
    from . import config,tasks,task_workflow,email_chat,drafts,storage,task_files,mail_archive
    now=datetime.now(timezone.utc).isoformat();day=now[:10];month=now[:7]
    with _LOCK:data=read_json(USAGE_FILE,{'started_at':None,'total':empty(),'days':{}})
    monthly=empty()
    for key,bucket in data['days'].items():
        if key.startswith(month):
            for field in monthly:monthly[field]+=bucket.get(field,0)
    files=[('Settings and context',config.CONFIG_PATH),('Tasks',tasks.TASKS_FILE),('Task reviews',task_workflow.WORKFLOW_FILE),('Chat history',email_chat.CHAT_FILE),('Reply drafts',drafts.DRAFTS_FILE),('Usage history',USAGE_FILE)]
    def size(path):
        try:return path.stat().st_size if path.is_file() and not path.is_symlink() else 0
        except OSError:return 0
    items=[{'name':name,'bytes':size(path)} for name,path in files]
    backup_dirs={storage.backups(path)[0].parent for _,path in files}
    backup_bytes=0
    for directory in backup_dirs:
        if directory.exists():backup_bytes+=sum(size(path) for path in directory.iterdir())
    items.append({'name':'Recovery copies','bytes':backup_bytes})
    for label,directory in [('Task and project files',task_files.ROOT),('Mail archive',mail_archive.ROOT)]:
        items.append({'name':label,'bytes':sum(size(path) for path in directory.rglob('*')) if directory.exists() else 0})
    return {'started_at':data['started_at'],'last_request_at':data.get('last_request_at'),'today':normalized(data['days'].get(day,{})),'month':monthly,'total':normalized(data['total']),'tracking_error':LAST_ERROR,'storage':{'items':items,'total_bytes':sum(item['bytes'] for item in items),'free_bytes':shutil.disk_usage(USAGE_FILE.parent).free}}
