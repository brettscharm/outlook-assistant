"""Durable JSON replacement with private recovery copies, separate from app code."""
import json
import os
import tempfile
import threading
import time
from pathlib import Path

_LOCK=threading.RLock()
RECOVERIES=[]

def backups(path):
    return [path.parent/'.outlook_assistant_backups'/(path.name+f'.{n}') for n in range(1,4)]

def _replace(path,raw):
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.outlook-save-')
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
        # Flush the directory entry as well as file contents before reporting success.
        directory=os.open(str(path.parent),os.O_RDONLY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(name):os.unlink(name)

def write_json(path,data):
    path=Path(path)
    raw=json.dumps(data,ensure_ascii=False).encode('utf-8')
    with _LOCK:
        copies=backups(path)
        copies[0].parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chmod(copies[0].parent,0o700)
        previous=None
        if path.exists():
            try:
                previous=path.read_bytes();json.loads(previous)
            except (ValueError,UnicodeError): previous=None
        if previous is not None:
            daily=copies[0].parent/(path.name+'.daily-'+time.strftime('%Y-%m-%d'))
            if not daily.exists():_replace(daily,previous)
            for old in sorted(daily.parent.glob(path.name+'.daily-*'),reverse=True)[7:]:old.unlink()
            for older,newer in reversed(list(zip(copies,copies[1:]))):
                if older.exists():_replace(newer,older.read_bytes())
            _replace(copies[0],previous)
        _replace(path,raw)
        if previous is None and not copies[0].exists():_replace(copies[0],raw)

def read_json(path,default):
    path=Path(path)
    with _LOCK:
        try:
            result=json.loads(path.read_text())
            if not isinstance(result,dict):raise ValueError('Expected saved object')
            return result
        except (FileNotFoundError,ValueError,UnicodeError) as error:
            for backup in backups(path)+sorted((path.parent/'.outlook_assistant_backups').glob(path.name+'.daily-*'),reverse=True):
                try:
                    result=json.loads(backup.read_text())
                    if not isinstance(result,dict):continue
                except (FileNotFoundError,ValueError,UnicodeError):continue
                if path.exists():
                    damaged=backup.parent/(path.name+'.damaged-'+str(time.time_ns()))
                    _replace(damaged,path.read_bytes())
                _replace(path,json.dumps(result).encode())
                RECOVERIES.append({'file':path.name,'message':'Recovered a saved copy. The damaged original, if present, was preserved.'})
                return result
            if isinstance(error,FileNotFoundError):return default
            raise RuntimeError(f'{path.name} could not be read. It was preserved; no valid recovery copy is available.') from error


def ensure_backup(path):
    path=Path(path)
    with _LOCK:
        if not path.exists():return
        copy=backups(path)[0]
        if copy.exists():return
        raw=path.read_bytes();value=json.loads(raw)
        if not isinstance(value,dict):raise ValueError('Invalid saved data')
        copy.parent.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(copy.parent,0o700)
        _replace(copy,raw)
