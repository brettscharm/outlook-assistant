"""Read-only Outlook process detection without AppleScript or automation permission."""
import subprocess
import sys
import threading
import time

_LOCK=threading.Lock()
_CHECKED=None
_RUNNING=None

def running():
    global _CHECKED,_RUNNING
    if sys.platform!='darwin':return None
    with _LOCK:
        now=time.monotonic()
        if _CHECKED is not None and now-_CHECKED<10:return _RUNNING
        try:
            result=subprocess.run(['/usr/bin/pgrep','-x','Microsoft Outlook'],capture_output=True,timeout=3)
            _RUNNING=True if result.returncode==0 else False if result.returncode==1 else None
        except (OSError,subprocess.TimeoutExpired):_RUNNING=None
        _CHECKED=now
        return _RUNNING

def open_outlook():
    global _CHECKED
    if sys.platform!='darwin':raise ValueError('Open Outlook on your Mac to receive new mail.')
    try:result=subprocess.run(['/usr/bin/open','-b','com.microsoft.Outlook'],capture_output=True,timeout=10)
    except (OSError,subprocess.TimeoutExpired):raise ValueError('Could not open Outlook. Open it from Applications.') from None
    if result.returncode:raise ValueError('Could not open Outlook. Check that it is installed in Applications.')
    with _LOCK:_CHECKED=None
    return {'opened':True}

def teams_running():
    if sys.platform!='darwin':return None
    try:
        result=subprocess.run(['/usr/bin/pgrep','-x','MSTeams'],capture_output=True,timeout=3)
        return True if result.returncode==0 else False if result.returncode==1 else None
    except (OSError,subprocess.TimeoutExpired):return None

def open_teams():
    if sys.platform!='darwin':raise ValueError('Open Teams on your Mac to update meetings.')
    try:result=subprocess.run(['/usr/bin/open','-b','com.microsoft.teams2'],capture_output=True,timeout=10)
    except (OSError,subprocess.TimeoutExpired):raise ValueError('Could not open Teams. Open it from Applications.') from None
    if result.returncode:raise ValueError('Install Microsoft Teams, sign in, and open Calendar.')
    return {'opened':True}

def sources():
    from pathlib import Path
    from .local_store import profiles
    try:mail=bool(profiles())
    except OSError:mail=False
    root=Path.home()/'Library/Containers/com.microsoft.teams2/Data/Library/Application Support/Microsoft/MSTeams/EBWebView'
    try:calendar=root.is_dir()
    except OSError:calendar=False
    return {'outlook':{'running':running(),'cache_available':mail},'teams':{'running':teams_running(),'cache_available':calendar}}
