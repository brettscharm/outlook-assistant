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
