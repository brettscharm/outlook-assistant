"""Durable one-at-a-time recording pipeline, with local speech and Bob task review."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from .config import DATA_DIR, _LOCK as CONFIG_LOCK, update_config
from .storage import read_json, write_json
from . import projects, task_files, meeting_tasks

ROOT = (DATA_DIR/'Library/Application Support/Outlook Assistant' if DATA_DIR == Path.home() else DATA_DIR)/'transcription'
_LOCK = threading.RLock()
_WORK = threading.Lock()
ACTIVE = {'queued','processing','finding_tasks'}


def folder(ident):
    if not isinstance(ident,str) or not re.fullmatch('[a-f0-9]{32}',ident): raise ValueError('Invalid transcription ID.')
    return ROOT/'jobs'/ident


def load(ident):
    job=read_json(folder(ident)/'job.json',{})
    if not job: raise ValueError('Transcription not found.')
    return job


def save(job): write_json(folder(job['id'])/'job.json',job)


def enqueue(project_id, file_id, title='', occurred_at='', retry=False):
    files=task_files.listing('project',project_id)
    item=next((f for f in files if f['id']==file_id and f.get('recording')),None)
    if not item: raise ValueError('Choose a local recording attached to a project.')
    ident=hashlib.sha256((project_id+':'+file_id).encode()).hexdigest()[:32]
    with _LOCK:
        job=read_json(folder(ident)/'job.json',{})
        if job:
            if retry and job['state'] not in ACTIVE:
                job.update(state='queued',message='Queued',error='');save(job)
            return job
        job={'id':ident,'project_id':project_id,'file_id':file_id,'title':title or item['name'],'occurred_at':occurred_at or item.get('occurred_at',''),'state':'queued','message':'Queued','created':time.time(),'meeting_ids':[],'added':0}
        save(job);return job


def listing():
    with _LOCK:
        rows=[]
        for path in (ROOT/'jobs').glob('*/job.json'):
            job=read_json(path,{})
            if not job: continue
            row={k:v for k,v in job.items() if k!='published_transcript'}
            if job['state']=='processing':row.update(read_json(path.parent/'progress.json',{}))
            rows.append(row)
        return sorted(rows,key=lambda j:j['created'],reverse=True)


def detail(ident):
    with _LOCK:
        job=load(ident);result=read_json(folder(ident)/'result.json',{})
        hints={}
        for segment in result.get('segments',[]):
            match=re.search(r'\b(?i:my name is|this is|I am|I[’\']m) ([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b',segment['text'])
            if match:hints.setdefault(segment['speaker'],match[1])
        return dict(job,result=result,name_hints=hints)


def runtime():
    from .speech_runtime import install
    return install(ROOT)


def render(result):
    names=result.get('speaker_names',{})
    return '\n'.join(f"[{int(s['start'])//60:02d}:{int(s['start'])%60:02d}] {names.get(s['speaker'],s['speaker'])}: {s['text']}" for s in result['segments'])


def persist_transcript(job,result):
    transcript=render(result)
    if len(transcript)>500000: raise ValueError('The transcript exceeds the project text limit. The full transcript remains saved in the recording job.')
    with CONFIG_LOCK:
        rows=projects.list_projects(); project=next((p for p in rows if p['id']==job['project_id']),None)
        if not project: raise ValueError('The project was removed. Your recording and transcript are retained.')
        meetings=project.setdefault('meetings',[])
        # Reuse the meeting associated with this file; never overwrite user-written transcript text.
        meeting=next((m for m in meetings if m.get('id') in job['meeting_ids'] or m.get('id')==job['id']),None)
        if meeting is None:
            meeting={'id':job['id'],'title':job['title'][:300],'transcript':'','recording_file_id':job['file_id'],'occurred_at':job['occurred_at']}
            if len(meetings)>=200: raise ValueError('This project already has 200 meetings. The transcript is retained in Recordings.')
            meetings.append(meeting)
        previous=job.get('published_transcript','')
        if meeting.get('transcript','') not in ('',previous,transcript):
            raise ValueError('This transcript was edited in Projects. Your edits were preserved; view the generated transcript in Recordings.')
        meeting['transcript']=transcript
        project['meetings']=projects.validate_meetings(meetings)
        update_config({'projects':rows})
        job['meeting_ids']=[meeting['id']];job['published_transcript']=transcript;save(job)


def rename_speakers(data):
    if not _WORK.acquire(blocking=False):raise ValueError('Wait for the current recording to finish processing before changing speaker names.')
    try:
        with _LOCK:
            job=load(data.get('id'))
            if job['state'] in ACTIVE:raise ValueError('Wait for this recording to finish processing before changing speaker names.')
            result=read_json(folder(job['id'])/'result.json',{})
            if not result: raise ValueError('Wait for the transcript to finish.')
            names=data.get('names')
            speakers={s['speaker'] for s in result['segments']}
            if not isinstance(names,dict) or any(k not in speakers or not isinstance(v,str) or len(v)>100 or any(ord(c)<32 for c in v) for k,v in names.items()):raise ValueError('Use a name of up to 100 characters for each speaker.')
            result['speaker_names']={k:v.strip() for k,v in names.items() if v.strip()}
            write_json(folder(job['id'])/'result.json',result)
            persist_transcript(job,result)
            job.update(state='queued',message='Updating task suggestions…',error='');save(job)
            return detail(job['id'])
    finally:_WORK.release()


def process(job, shutdown):
    path=folder(job['id']);result=read_json(path/'result.json',{})
    if not result:
        job.update(state='processing',message='Preparing local transcription…');save(job)
        write_json(path/'progress.json',{'message':'Setting up local speech tools (first use may take several minutes)…','percent':0})
        python=runtime()
        item=next((f for f in task_files.listing('project',job['project_id']) if f['id']==job['file_id']),None)
        if not item: raise ValueError('The recording attachment was removed.')
        source=task_files.file_path(task_files.directory('project',job['project_id']),item)
        environment={k:v for k,v in os.environ.items() if k in ('PATH','HOME','TMPDIR','LANG','SYSTEMROOT')}
        environment.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',HF_HUB_DISABLE_TELEMETRY='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',HF_HUB_DISABLE_XET='1')
        with (path/'worker.log').open('wb') as log:
            os.chmod(path/'worker.log',0o600)
            child=subprocess.Popen([str(python),str(Path(__file__).with_name('speech_worker.py')),str(source),str(ROOT/'models'),str(path/'result.json'),str(path/'progress.json')],stdout=log,stderr=log,env=environment)
            started=time.monotonic()
            while child.poll() is None:
                if shutdown.wait(1) or time.monotonic()-started>21600:
                    child.terminate()
                    try:child.wait(timeout=10)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
                    if shutdown.is_set():job.update(state='queued',message='Waiting to resume');save(job);return
                    raise ValueError('Transcription timed out. Your recording is saved; retry with a shorter file.')
            if child.returncode: raise ValueError(read_json(path/'progress.json',{}).get('message','Local speech processing failed. Retry transcription.'))
        result=read_json(path/'result.json',{})
        if not isinstance(result.get('segments'),list):raise ValueError('The speech engine returned an invalid transcript.')
    persist_transcript(job,result)
    if not result['segments']:job.update(state='complete',message='No speech detected',error='');save(job);return
    job.update(state='finding_tasks',message='Finding project tasks…');save(job)
    for ident in job['meeting_ids']:
        answer=meeting_tasks.extract({'project_id':job['project_id'],'meeting_id':ident})
        job['added']+=answer['added'];save(job)
    job.update(state='complete',message='Transcript and task suggestions ready',error='');save(job)


def scheduler(shutdown):
    # A second server must not run another speech worker against the same queue.
    import fcntl
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (ROOT/'worker.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        for row in listing():
            if row['state'] in ACTIVE:
                job=load(row['id']);job.update(state='queued',message='Resuming…');save(job)
        while not shutdown.is_set():
            from . import recorder
            try:recorder.snapshot()
            except (ValueError,OSError,RuntimeError):pass  # A removed project must not stop other jobs.
            # Finalize and enqueue even when no browser window is open.
            job=next((row for row in reversed(listing()) if row['state']=='queued'),None)
            if job:
                with _WORK:
                    try:process(load(job['id']),shutdown)
                    except Exception as exc:
                        current=load(job['id']);current.update(state='error',error=str(exc)[:600],message='Transcript saved; task suggestions need retry' if (folder(job['id'])/'result.json').exists() else 'Transcription needs attention');save(current)
            shutdown.wait(3)
