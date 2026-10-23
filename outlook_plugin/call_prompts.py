"""Possible-call reminders from microphone activity. Never starts capture automatically."""
import json
import platform
import subprocess
import threading
import time
import uuid
from pathlib import Path
from .config import DATA_DIR, read_config, update_config
from .storage import read_json, _replace
from . import projects, recorder

APP=Path(__file__).parent/'bin/Outlook Call Reminder.app'
FILE=DATA_DIR/'.outlook_assistant_call_prompts.json'
APPS={'teams':'Microsoft Teams','slack':'Slack','chrome':'Google Chrome','safari':'Safari','edge':'Microsoft Edge','firefox':'Firefox','brave':'Brave','zoom':'Zoom'}
_LOCK=threading.RLock()
_INSTANCE=''
_LAST_HEARTBEAT=0
_ERROR=''


def supported():
    try:return platform.system()=='Darwin' and platform.machine()=='arm64' and tuple(int(n) for n in platform.mac_ver()[0].split('.')[:2])>=(14,2) and APP.is_dir()
    except (ValueError,IndexError):return False


def snapshot():
    return {'enabled':read_config().get('call_prompts_enabled',True),'supported':supported(),'running':time.time()-_LAST_HEARTBEAT<30,'error':_ERROR}


def _save(data):_replace(FILE,json.dumps(data).encode())


def command(data):
    global _LAST_HEARTBEAT,_ERROR
    action=data.get('action')
    with _LOCK:
        if action=='settings':
            if type(data.get('enabled')) is not bool:raise ValueError('Choose whether to show recording reminders.')
            update_config({'call_prompts_enabled':data['enabled']});return snapshot()
        if action=='observe':
            if not _INSTANCE or data.get('instance')!=_INSTANCE:raise ValueError('The app restarted. Reconnect the call reminder.')
            apps=data.get('apps',[])
            if not isinstance(apps,list) or len(apps)>len(APPS) or any(app not in APPS for app in apps):raise ValueError('Invalid microphone activity.')
            now=time.time();_LAST_HEARTBEAT=now
            _ERROR='Microphone activity could not be checked. Start recording manually.' if data.get('error') else ''
            state=read_json(FILE,{'sessions':{}});sessions=state.setdefault('sessions',{})
            active=recorder.snapshot()['active'];enabled=snapshot()['enabled'];candidate=None
            if not _ERROR:
                for app in apps:
                    row=sessions.get(app)
                    if row is None or now-row.get('last_seen',0)>90:
                        row={'id':uuid.uuid4().hex,'first_seen':now,'last_seen':now,'prompted':False};sessions[app]=row
                    if not row['prompted'] and (not row.get('active',True) or now-row['last_seen']>15):row['first_seen']=now
                    row['last_seen']=now
                    if active:row['prompted']=True
                    if candidate is None and enabled and not active and not row['prompted'] and now-row['first_seen']>=8:
                        candidate={'id':row['id'],'app':app,'name':APPS[app]}
                for app,row in sessions.items():row['active']=app in apps
                sessions={app:row for app,row in sessions.items() if now-row.get('last_seen',0)<86400};state['sessions']=sessions
                _save(state)
            return {'enabled':enabled,'recording':active,'candidate':candidate,'active_ids':[row['id'] for app,row in sessions.items() if app in apps],'projects':[{'id':p['id'],'name':p['name']} for p in projects.list_projects()] if candidate else []}
        if action in ('shown','dismiss'):
            state=read_json(FILE,{'sessions':{}})
            row=next((s for s in state['sessions'].values() if s['id']==data.get('id')),None)
            if row:row['prompted']=True;_save(state)
            return {'ok':True}
        raise ValueError('Unknown reminder action.')


def supervise(port,instance,shutdown):
    global _INSTANCE,_ERROR
    _INSTANCE=instance
    if not supported():return
    last_launch=0
    while not shutdown.is_set():
        if time.time()-_LAST_HEARTBEAT>30 and time.time()-last_launch>60:
            last_launch=time.time()
            try:subprocess.run(['/usr/bin/open','-g','-n',str(APP),'--args',f'http://127.0.0.1:{port}',instance],check=True,capture_output=True,timeout=10)
            except (OSError,subprocess.SubprocessError):_ERROR='Call reminders could not open. Update the app or start recording manually.'
        shutdown.wait(10)
