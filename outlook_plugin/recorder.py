"""User-started native capture, durable sessions and project attachment registration."""
import json
import os
import platform
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .config import DATA_DIR
from .storage import read_json, write_json
from . import task_files

ROOT=DATA_DIR/'Library/Application Support/Outlook Assistant/recordings' if DATA_DIR==Path.home() else DATA_DIR/'recordings'
FILE=DATA_DIR/'.outlook_assistant_recorder.json'
APP=Path(__file__).parent/'bin/Outlook Recorder.app'
_LOCK=threading.RLock()
_UPDATING=False
ACTIVE={'launching','choosing','starting','recording','saving'}

def supported():
    try:return platform.system()=='Darwin' and platform.machine()=='arm64' and int(platform.mac_ver()[0].split('.')[0])>=14 and APP.is_dir()
    except (ValueError,IndexError):return False

def _folder(session):
    ident=session.get('id','')
    if not isinstance(ident,str) or len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('Invalid recording session.')
    return ROOT/ident

def _finish(session,folder):
    suffix='.mp4' if session['video'] else '.m4a'
    source=folder/('recording'+suffix)
    with task_files._LOCK:
        destination=task_files.directory('project',session['project_id'])
        files=read_json(destination/'index.json',{'files':[]})['files']
        if not any(item['id']==session['id'] for item in files):
            target=destination/'recordings'/(session['id']+suffix)
            if not source.is_file() and not target.is_file():raise ValueError('The saved recording is missing. Check the recovery folder.')
            if source.is_file():
                if source.stat().st_size==0:raise ValueError('The recorder saved an empty file.')
                target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(source,0o600);os.replace(source,target)
            files.append({'id':session['id'],'name':session['title']+suffix,'size':target.stat().st_size,'suffix':suffix,'recording':True,'occurred_at':session['created_at']})
            write_json(destination/'index.json',{'files':files})
    session['registered']=True;write_json(FILE,session)

def snapshot():
    with _LOCK:
        session=read_json(FILE,{})
        result={'supported':supported(),'active':False,'state':'idle','message':''}
        if not session:return result
        folder=_folder(session)
        try:status=json.loads((folder/'status.json').read_text())
        except (OSError,ValueError):status={'state':'launching','message':'Opening recorder…','heartbeat':session.get('created',0)}
        state=status.get('state','failed')
        if state in ACTIVE:
            pid=status.get('pid')
            alive=True
            if pid:
                try:os.kill(int(pid),0)
                except (OSError,ValueError):alive=False
            if not alive or not pid and time.time()-session['created']>60:
                state='failed';status['message']='The recorder stopped unexpectedly. Any captured files remain in the recovery folder.'
        if state=='complete' and not session.get('registered'):
            try:_finish(session,folder)
            except (OSError,ValueError,RuntimeError) as exc:state='failed';status['message']='Recording retained, but could not be attached: '+str(exc)
        if state=='complete' and session.get('registered'):
            from . import transcription
            try:transcription.enqueue(session['project_id'],session['id'],session['title'],session['created_at'])
            except (ValueError,OSError,RuntimeError) as exc:status['message']='Recording saved; transcription could not be queued: '+str(exc)
        result.update(state=state,active=state in ACTIVE,message=status.get('message',''),started_at=status.get('started_at',0),id=session['id'],project_id=session['project_id'],title=session['title'],recoverable=state=='failed')
        return result

def start(data):
    with _LOCK:
        if _UPDATING:raise ValueError('An app update is being installed. Start the recording after it finishes.')
        if snapshot()['active']:raise ValueError('A recording is already active. Stop it before starting another.')
        if not supported():raise ValueError('Recording requires an Apple silicon Mac with macOS 14 or later and the current app files.')
        project=data.get('project_id');task_files.directory('project',project)
        title=data.get('title','').strip() if isinstance(data.get('title',''),str) else ''
        if len(title)>160 or any(c in title for c in '/\\') or any(ord(c)<32 for c in title):raise ValueError('Use a recording title of up to 160 characters without slashes.')
        video=data.get('video',False);microphone=data.get('microphone',True)
        if type(video) is not bool or type(microphone) is not bool:raise ValueError('Choose recording options.')
        ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
        if shutil.disk_usage(ROOT).free<3_000_000_000:raise ValueError('Free at least 3 GB on this Mac before starting a recording.')
        now=datetime.now(timezone.utc);session={'id':uuid.uuid4().hex,'project_id':project,'title':title or 'Recording '+datetime.now().strftime('%Y-%m-%d %H.%M'),'created':time.time(),'created_at':now.isoformat(),'video':video,'microphone':microphone}
        folder=_folder(session);folder.mkdir(mode=0o700);write_json(FILE,session)
        try:subprocess.run(['/usr/bin/open','-n',str(APP),'--args',str(folder),'video' if video else 'audio','mic' if microphone else 'no-mic'],check=True,capture_output=True,timeout=15)
        except (OSError,subprocess.SubprocessError):
            write_json(folder/'status.json',{'state':'failed','message':'The recorder could not open. Reinstall the latest Mac app or check macOS security prompts.'})
            raise ValueError('The recorder could not open. Check macOS security prompts and try again.') from None
        return snapshot()

def stop():
    with _LOCK:
        status=snapshot()
        if not status['active']:return status
        session=read_json(FILE,{});(_folder(session)/'stop').touch(mode=0o600)
        return dict(status,message='Stopping and saving recording…')

def reveal():
    with _LOCK:
        session=read_json(FILE,{})
        if not session:raise ValueError('No recording session to recover.')
        subprocess.run(['/usr/bin/open',str(_folder(session))],check=True,capture_output=True,timeout=10)
        return {'opened':True}


def reserve_update():
    global _UPDATING
    with _LOCK:
        if snapshot()['active']:return False
        from . import transcription
        if any(job['state'] in transcription.ACTIVE for job in transcription.listing()):return False
        _UPDATING=True;return True

def release_update():
    global _UPDATING
    with _LOCK:_UPDATING=False
