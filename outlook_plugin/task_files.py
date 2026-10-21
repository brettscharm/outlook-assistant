"""Private document copies attached to saved tasks and projects."""
import os
import tempfile
import base64
import binascii
import re
import subprocess
import threading
import uuid
from pathlib import Path
from .config import DATA_DIR
from .storage import read_json, write_json, _replace
from .tasks import load_tasks
from .projects import list_projects

ROOT = DATA_DIR/'Library/Application Support/Outlook Assistant/attachments' if DATA_DIR == Path.home() else DATA_DIR/'attachments'
MAX_BYTES = 25 * 1024 * 1024
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
RECORDINGS = {'.mp4', '.mov', '.m4v', '.webm', '.mp3', '.m4a', '.wav'}
EXTENSIONS = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.txt', '.csv', '.rtf', '.png', '.jpg', '.jpeg'}
_LOCK = threading.RLock()

def directory(kind, owner):
    if kind not in ('task', 'project') or not isinstance(owner,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',owner):
        raise ValueError('Choose a saved task or project.')
    rows = [t for group in load_tasks().values() for t in group] if kind == 'task' else list_projects()
    if not any(row['id'] == owner for row in rows):raise ValueError('Task or project no longer exists.')
    return ROOT/kind/owner

def listing(kind, owner):
    with _LOCK:
        folder=directory(kind,owner)
        return read_json(folder/'index.json', {'files':[]})['files']

def change(data):
    with _LOCK:
        folder=directory(data.get('kind'),data.get('owner'))
        rows=read_json(folder/'index.json', {'files':[]})['files']
        action=data.get('action')
        if action=='add':
            name=data.get('name','')
            if not isinstance(name,str) or not name or len(name)>200 or '/' in name or '\\' in name or any(ord(c)<32 for c in name):raise ValueError('Use a plain document filename.')
            suffix=Path(name).suffix.lower()
            if suffix not in EXTENSIONS:raise ValueError('Choose a Word, Excel, PowerPoint, PDF, text, or image file.')
            encoded=data.get('content','')
            if not isinstance(encoded,str) or len(encoded)>4*((MAX_BYTES+2)//3):raise ValueError('Files must be 25 MB or smaller.')
            try:raw=base64.b64decode(encoded,validate=True)
            except (ValueError,binascii.Error):raise ValueError('The file could not be read. Please attach it again.')
            if len(raw)>MAX_BYTES:raise ValueError('Files must be 25 MB or smaller.')
            folder.mkdir(parents=True,exist_ok=True,mode=0o700)
            ident=uuid.uuid4().hex
            path=folder/(ident+suffix)
            _replace(path,raw)
            rows.append({'id':ident,'name':name,'size':len(raw),'suffix':suffix})
            try:write_json(folder/'index.json',{'files':rows})
            except Exception:
                path.unlink(missing_ok=True)
                raise
        else:
            item=next((r for r in rows if r['id']==data.get('id')),None)
            if not item:raise ValueError('Attachment not found.')
            path=file_path(folder,item)
            if action=='open':
                if not path.is_file():raise ValueError('The saved attachment is missing.')
                subprocess.run(['/usr/bin/open',str(path)],check=True,timeout=15,capture_output=True)
            elif action=='remove':
                rows=[r for r in rows if r['id']!=item['id']]
                write_json(folder/'index.json',{'files':rows})
                path.unlink(missing_ok=True)
            else:raise ValueError('Unknown attachment action.')
        return rows


def file_path(folder,item):
    return (folder/'recordings' if item.get('recording') else folder)/(item['id']+item['suffix'])


def upload(kind,owner,name,stream,size):
    """Stream directly to a private temporary copy; publish only complete files."""
    folder=directory(kind,owner)
    if not isinstance(name,str) or not name or len(name)>200 or '/' in name or '\\' in name or any(ord(c)<32 for c in name):raise ValueError('Use a plain filename.')
    suffix=Path(name).suffix.lower()
    if suffix not in EXTENSIONS|RECORDINGS:raise ValueError('Choose a document, image, video, or audio recording.')
    if not 0<size<=MAX_UPLOAD_BYTES:raise ValueError('Choose a file up to 2 GB.')
    recording=suffix in RECORDINGS
    destination=folder/'recordings' if recording else folder
    destination.mkdir(parents=True,exist_ok=True,mode=0o700)
    ident=uuid.uuid4().hex
    path=destination/(ident+suffix)
    fd,temp=tempfile.mkstemp(prefix='.upload-',dir=destination)
    try:
        with os.fdopen(fd,'wb') as output:
            remaining=size
            while remaining:
                chunk=stream.read(min(1024*1024,remaining))
                if not chunk:raise ValueError('Upload interrupted. Please attach the file again.')
                output.write(chunk);remaining-=len(chunk)
            output.flush();os.fsync(output.fileno())
        with _LOCK:
            directory(kind,owner)  # The project may have changed during upload.
            rows=read_json(folder/'index.json',{'files':[]})['files']
            os.replace(temp,path)
            rows.append({'id':ident,'name':name,'size':size,'suffix':suffix,'recording':recording})
            try:write_json(folder/'index.json',{'files':rows})
            except Exception:
                path.unlink(missing_ok=True);raise
            return rows
    finally:
        Path(temp).unlink(missing_ok=True)
