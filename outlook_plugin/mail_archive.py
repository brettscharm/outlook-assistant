"""Explicit local archive of downloaded, visible mail as standard EML files."""
import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path
from .config import DATA_DIR
from .storage import write_json

ROOT = DATA_DIR/'Library/Application Support/Outlook Assistant/archive' if DATA_DIR == Path.home() else DATA_DIR/'archive'
_LOCK = threading.Lock()
_STATE = {'state':'idle','messages':0,'attachments':0,'missing_attachments':0,'previews':0,'message':''}
MAX_BYTES = 5*1024**3


def status():
    return {**_STATE, 'path': str(ROOT), 'limit_bytes': MAX_BYTES}


def attachment_path(profile, value):
    if not isinstance(value,str) or not value.startswith('~/Files/'):
        return None
    root = (profile/'Files').resolve()
    candidate = profile/value[2:]
    resolved = candidate.resolve()
    if os.path.commonpath([root,resolved]) != str(root) or not resolved.is_file():
        return None
    return resolved


def archive(engine):
    if not _LOCK.acquire(False):
        return status()
    _STATE.update(state='working',messages=0,attachments=0,missing_attachments=0,previews=0,message='Saving downloaded mail…')
    def run():
        try:
            backend = engine.get_active_backend()
            profile = backend.profile()
            namespace = hashlib.sha256(str(profile.resolve()).encode()).hexdigest()[:16]
            destination = ROOT/namespace
            destination.mkdir(parents=True,exist_ok=True,mode=0o700)
            used = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
            complete_rows = hasattr(backend,'get_cached_messages')
            rows = backend.get_cached_messages() if complete_rows else engine.get_emails(folder='all',limit=1000000)
            for row in rows:
                message = row if complete_rows else engine.get_email_details(str(row['id'])) or row
                eml = EmailMessage()
                for field,value in [('Subject',message.get('subject','')),('From',message.get('sender','')),('X-Original-Received',message.get('received_time',''))]:
                    eml[field]=str(value).replace('\r',' ').replace('\n',' ')
                for field,key in [('To','to'),('Cc','cc')]:
                    recipients=message.get(key,[])
                    if isinstance(recipients,list):
                        eml[field]=', '.join(str(p.get('address','')).replace('\r','').replace('\n','') for p in recipients if isinstance(p,dict))
                try:eml['Date']=format_datetime(datetime.fromisoformat(message.get('received_time','').replace('Z','+00:00')))
                except ValueError:pass
                eml.set_content(message.get('body') or message.get('preview') or '')
                if not message.get('body_complete'):_STATE['previews']+=1
                copied=0;pending_size=0
                for entry in message.get('attachments',[]):
                    path=attachment_path(profile,entry.get('path')) if entry.get('downloaded') else None
                    if path is None:
                        _STATE['missing_attachments']+=1;continue
                    size=path.stat().st_size
                    if size>50*1024**2 or pending_size+size>100*1024**2:
                        _STATE['missing_attachments']+=1;continue
                    pending_size+=size
                    eml.add_attachment(path.read_bytes(),maintype='application',subtype='octet-stream',filename=Path(entry.get('name') or path.name).name)
                    copied+=1
                raw=eml.as_bytes()
                key=hashlib.sha256(json.dumps([message.get('message_id') or message['id'],message.get('received_time','')]).encode()).hexdigest()
                path=destination/(key+'.eml')
                # Never degrade an existing archive when Outlook later evicts content.
                if path.exists():
                    _STATE['messages']+=1;continue
                previous=0
                if used-previous+len(raw)>MAX_BYTES:
                    raise ValueError('Archive reached its 5 GB limit. Move the archive to external storage before starting another snapshot.')
                temporary=destination/(key+'.tmp')
                with temporary.open('wb') as output:
                    os.chmod(temporary,0o600);output.write(raw);output.flush();os.fsync(output.fileno())
                temporary.replace(path);used+=len(raw)-previous
                _STATE['messages']+=1;_STATE['attachments']+=copied
            _STATE.update(state='complete',message='Archive saved. Only locally downloaded content is included.',bytes=used,finished=datetime.now(timezone.utc).isoformat())
            write_json(ROOT/'summary.json',dict(_STATE))
        except Exception as exc:
            _STATE.update(state='failed',message=str(exc) if isinstance(exc,(ValueError,RuntimeError)) else 'Could not finish the archive. Earlier saved files are intact.')
        finally:_LOCK.release()
    threading.Thread(target=run,daemon=True).start()
    return status()
