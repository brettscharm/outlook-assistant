"""User-triggered IBM installer and daily release checks, without credentials."""
import os,re,signal,subprocess,tempfile,threading,time,urllib.request
from pathlib import Path
from .config import DATA_DIR
_RELEASE_URL='https://s3.us-south.cloud-object-storage.appdomain.cloud/bob-shell/bobshell2-version.txt'
_INSTALL_URL='https://bob.ibm.com/download/bobshell.sh'
_LOCK=threading.Lock()
_STATE={'state':'idle','message':''}
_RELEASE={'checked':0,'version':'','error':''}
PREFIX=DATA_DIR/'Library/Application Support/Outlook Assistant/bob' if DATA_DIR==Path.home() else DATA_DIR/'bob'

def release():
    with _LOCK:
        if time.time()-_RELEASE['checked']<86400:return dict(_RELEASE)
        # Retry network failures in an hour, rather than on each UI poll.
        _RELEASE['checked']=time.time()
    try:
        with urllib.request.urlopen(_RELEASE_URL,timeout=10) as response:value=response.read(100).decode().strip()
        if not re.fullmatch(r'2\.\d+\.\d+',value):raise ValueError('Unrecognized release version.')
        with _LOCK:_RELEASE.update(version=value,error='')
    except Exception:
        with _LOCK:_RELEASE.update(error='Could not check IBM for an update.',checked=time.time()-82800)
    with _LOCK:return dict(_RELEASE)

def snapshot():
    with _LOCK:return {**_STATE,'release':dict(_RELEASE)}

def start():
    from .ai_agent import _BOB_LOCK,node_executable,bob_executable
    node=node_executable(bob_executable())
    if not node:raise ValueError('Install Node.js 24 or later using IBM’s setup guide, then retry.')
    npm=Path(node).parent/'npm'
    if not npm.is_file():raise ValueError('npm is missing from your Node installation. Repair Node using IBM’s setup guide.')
    if not _BOB_LOCK.acquire(False):raise ValueError('Bob is busy. Wait for the current request to finish.')
    with _LOCK:
        if _STATE['state']=='working':
            _BOB_LOCK.release();raise ValueError('Installation is already running.')
        _STATE.update(state='working',message='Checking IBM’s release…')
    def worker():
        try:
            version=release()['version']
            if not version:raise ValueError('Could not determine a supported IBM Bob release. Retry later.')
            with tempfile.TemporaryDirectory(prefix='outlook-bob-setup-') as folder:
                script=Path(folder)/'install.sh'
                with urllib.request.urlopen(_INSTALL_URL,timeout=20) as response:content=response.read(1000000)
                if not content.startswith(b'#!/') or len(content)>=1000000:raise ValueError('Unexpected installer response.')
                script.write_bytes(content)
                PREFIX.mkdir(parents=True,exist_ok=True,mode=0o700)
                env={k:v for k,v in os.environ.items() if k not in ('BOB_API_KEY','BOB_TEAM_ID')}
                env.update(PATH=str(PREFIX/'bin')+':'+str(Path(node).parent)+':/usr/bin:/bin:/usr/sbin:/sbin',NPM_CONFIG_PREFIX=str(PREFIX))
                with _LOCK:_STATE['message']='Installing Bob '+version+' from IBM…'
                process=subprocess.Popen(['/bin/bash',str(script),'--pm','npm','--version',version],env=env,cwd=folder,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                try:process.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait();raise
                if process.returncode:raise ValueError('IBM’s installer failed. Check your network and company installation permissions, then retry.')
                from .ai_agent import bob_compatibility
                checked=bob_compatibility(str(PREFIX/'bin/bob'),node)
                if not checked['ready']:raise ValueError(checked['detail'])
                with _LOCK:_STATE.update(state='complete',message=checked['detail'])
        except subprocess.TimeoutExpired:
            with _LOCK:_STATE.update(state='failed',message='Installation timed out. Check your connection and retry.')
        except Exception as exc:
            with _LOCK:_STATE.update(state='failed',message=str(exc) if isinstance(exc,ValueError) else 'Installation failed. Check your connection and permissions.')
        finally:_BOB_LOCK.release()
    threading.Thread(target=worker,daemon=True).start()
    return snapshot()
