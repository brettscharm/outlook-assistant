"""Read New Outlook's on-disk cache via a pinned, read-only hxmail helper."""
import json
import os
import platform
import re
import subprocess
import threading
import time
from pathlib import Path
from .config import read_config
from .mail_filters import visible_messages

ROOT = Path(os.environ.get('OUTLOOK_ASSISTANT_PROFILE_ROOT', str(Path.home() / 'Library/Group Containers/UBF8T346G9.Office/Outlook/Outlook 15 Profiles'))).expanduser()
_LOCK = threading.RLock()
_CACHE = {}


def profiles():
    return sorted(p.parent for p in ROOT.glob('*/HxStore.hxd'))


class LocalStoreBridge:
    def profile(self):
        configured = read_config().get('outlook_profile', '')
        available = profiles()
        if configured:
            p = Path(configured).expanduser().resolve()
            if p not in [x.resolve() for x in available]:
                raise RuntimeError('The selected Outlook profile is unavailable. Choose a profile in Settings.')
            return p
        if len(available) != 1:
            raise RuntimeError('Choose an Outlook profile in Settings.' if available else 'No New Outlook cache found. Open Outlook and let it sync first.')
        return available[0]

    def is_available(self):
        return bool(profiles())

    def _load(self, force=False):
        with _LOCK:
            p = self.profile()
            stat = (p / 'HxStore.hxd').stat()
            fingerprint = (str(p), stat.st_size, stat.st_mtime_ns)
            if not force and _CACHE.get('fingerprint') == fingerprint and time.time()-_CACHE.get('checked',0)<60:
                return _CACHE
            arch = 'arm64' if platform.machine() == 'arm64' else 'amd64'
            helper = Path(__file__).parent / 'bin' / ('hxmail-darwin-' + arch)
            if not helper.exists():
                raise RuntimeError('Local Outlook reader is missing. Install the complete Mac release.')
            try:
                result = subprocess.run([str(helper), '-profile', str(p), '-body'],
                                        capture_output=True, text=True, timeout=90)
            except subprocess.TimeoutExpired:
                raise RuntimeError('Reading Outlook took too long. Let Outlook finish syncing and retry.') from None
            if result.returncode not in (0, 3):
                # Reader diagnostics contain structural information, not message text.
                detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'Unknown reader error'
                raise RuntimeError('Could not read the local Outlook cache: ' + detail[:600])
            rows = []
            for line in result.stdout.splitlines():
                m = json.loads(line)
                sender = m.get('from', {})
                rows.append(dict(m, id=str(m['id']), folder_id=str(m['folder_id']),
                                 sender=f"{sender.get('name','')} <{sender.get('address','')}>".strip(),
                                 received_time=m.get('received',''), is_read=m.get('read')=='read',
                                 body_complete=m.get('body_state') in ('inline','file') and bool(m.get('body'))))
            _CACHE.clear()
            _CACHE.update(fingerprint=fingerprint, checked=time.time(), rows=rows,
                          partial=result.returncode==3, diagnostics=result.stderr[-2000:],
                          store_updated=stat.st_mtime, profile=str(p))
            return _CACHE

    def status(self):
        data = self._load()
        rows = visible_messages(data['rows'])
        return {'active_backend':'local_cache', 'message_count':len(rows), 'excluded_count':len(data['rows'])-len(rows),
                'full_body_count':sum(m['body_complete'] for m in rows),
                'preview_count':sum(not m['body_complete'] for m in rows),
                'newest_message':rows[0]['received_time'] if rows else None,
                'cache_updated':data['store_updated'], 'checked':data['checked'],
                'profile':data['profile'], 'partial':data['partial'],
                'warning':data['diagnostics'] if data['partial'] else '',
                'calendar_supported':False}

    def list_accounts(self):
        return [{'name':self.profile().name, 'email':'all', 'type':'Local profile'}]

    def list_folders(self):
        folders = {}
        for m in visible_messages(self._load()['rows']):
            f = folders.setdefault(m['folder_id'], {'id':m['folder_id'], 'name':('Unnamed local folder' if re.fullmatch(r'(?:\{[0-9A-Fa-f-]{36}\}\d*|[0-9A-Fa-f-]{36})',m['folder']) else m['folder']) or 'Unknown folder',
                                   'kind':m['folder_kind'], 'total_messages':0, 'unread_messages':0})
            f['total_messages'] += 1
            f['unread_messages'] += m.get('read') == 'unread'
        return sorted(folders.values(), key=lambda f:(f['kind']!='inbox', f['name'].lower(), f['id']))

    def get_emails(self, folder='all', limit=50, unread_only=False, search_term=None, offset=0):
        rows = visible_messages(self._load()['rows'])
        if folder.lower() not in ('all','all mail',''):
            rows = [m for m in rows if folder in (m['folder_id'],m['folder']) or folder.lower()==m['folder_kind']]
        if unread_only:
            rows = [m for m in rows if m.get('read') == 'unread']
        if search_term:
            q = search_term.casefold()
            rows = [m for m in rows if q in '\n'.join(str(m.get(k,'')) for k in ('subject','sender','preview','body')).casefold()]
        return [{k:v for k,v in m.items() if k!='body'} for m in rows[offset:None if limit is None else offset+limit]]

    def get_email_details(self, message_id):
        return next((m for m in visible_messages(self._load()['rows']) if m['id']==str(message_id)),None)

    def get_upcoming_events(self, **kwargs):
        raise RuntimeError('Calendar events are not supported by the local cache reader yet. Mail invites are searchable in Mail; they do not prove availability.')
