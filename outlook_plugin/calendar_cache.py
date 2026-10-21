"""Read materialized Teams calendar entries. Never infer free/busy or expand series."""
import hashlib,json,subprocess,threading,time,re,html
from urllib.parse import urlsplit
from datetime import datetime,timezone,timedelta
from pathlib import Path
_LOCK=threading.Lock()
_CACHE={}
from .config import DATA_DIR
from .storage import _replace
CACHE_FILE=DATA_DIR/'.outlook_assistant_calendar_cache.json'
_REFRESH_LOCK=threading.Lock()
_DISK_LOADED=False
_LAST_ATTEMPT=0
_LAST_ERROR=''


def _hydrate():
    global _DISK_LOADED
    with _LOCK:
        if _CACHE or _DISK_LOADED:return
        _DISK_LOADED=True
        try:
            data=json.loads(CACHE_FILE.read_text())
            if isinstance(data,dict) and isinstance(data.get('events'),list) and type(data.get('checked')) in (int,float) and 0<data['checked']<=time.time()+60:
                _CACHE.update(data)
        except (OSError,ValueError,TypeError):pass


def _read_calendar():
    helper=Path(__file__).parent/'bin/teams-calendar-darwin'
    if not helper.exists():raise RuntimeError('Install the current desktop release to add the calendar reader.')
    try:run=subprocess.run([str(helper)],capture_output=True,text=True,timeout=100)
    except subprocess.TimeoutExpired:raise RuntimeError('Teams calendar took too long to read. Let Teams finish syncing and retry.') from None
    if run.returncode:raise RuntimeError('Could not read the Teams calendar cache. Open Teams and its Calendar, then retry.')
    try:data=json.loads(run.stdout)
    except ValueError:raise RuntimeError('Calendar reader returned an unreadable result.') from None
    if not isinstance(data,dict) or not isinstance(data.get('events'),list):raise RuntimeError('Calendar reader returned an unsupported format.')
    return dict(data,checked=time.time())


def _refresh(force=False,held=False):
    global _LAST_ATTEMPT,_LAST_ERROR
    if not held:_REFRESH_LOCK.acquire()
    try:
        with _LOCK:
            if not force and time.time()-_CACHE.get('checked',0)<60:return
            _LAST_ATTEMPT=time.time()
        data=_read_calendar()
        # A derived snapshot needs one private atomic copy, not daily history.
        try:
            CACHE_FILE.parent.mkdir(parents=True,exist_ok=True)
            _replace(CACHE_FILE,json.dumps(data,allow_nan=False).encode())
            error=''
        except (OSError,ValueError):error='Calendar refreshed, but its offline copy could not be saved.'
        with _LOCK:
            _CACHE.clear();_CACHE.update(data);_LAST_ERROR=error
    except Exception:
        with _LOCK:_LAST_ERROR='Calendar refresh failed. Open Teams Calendar and try again. Saved meetings are still shown.'
        if not held:raise
    finally:_REFRESH_LOCK.release()


def instant(value):
    if isinstance(value,dict):value=value.get('$date')
    try:
        if isinstance(value,(int,float)) and not isinstance(value,bool):return datetime.fromtimestamp(value/1000,timezone.utc)
        if isinstance(value,str):
            if value.isdigit():return datetime.fromtimestamp(int(value)/1000,timezone.utc)
            parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
            if parsed.tzinfo:return parsed.astimezone(timezone.utc)
    except (ValueError,OverflowError,OSError):pass
    return None

def meeting_url(row):
    candidates=[row.get('skypeTeamsMeetingUrl'),row.get('joinWebUrl')]
    candidates += re.findall(r'https://[^\s<>"\']+',str(row.get('location') or ''))
    for value in candidates:
        if not isinstance(value,str):continue
        value=html.unescape(value).strip().rstrip(').,;')
        try:
            url=urlsplit(value)
            if url.scheme=='https' and url.hostname and not url.username and not url.password and '[redacted]' not in value and not any(c.isspace() for c in value):return value[:8000]
        except ValueError:pass
    return ''

def attendee_email(value):
    if not isinstance(value,str):return ''
    value=value.strip().lower()
    return value if len(value)<=254 and re.fullmatch(r'[^\s@<>?,;]+@[^\s@<>?,;]+\.[^\s@<>?,;]+',value) else ''


def attendees(row):
    people={}
    raw=row.get('attendees',[])
    if not isinstance(raw,list):return []
    for item in raw[:2000]:
        if not isinstance(item,dict):continue
        name=str(item.get('name') or '')[:500]
        email=attendee_email(item.get('email'))
        if not name and not email:continue
        key=email or 'name:'+name.casefold()
        kind=item.get('type') if item.get('type') in ('required','optional','resource') else 'invited'
        person={'name':name or email,'email':email,'type':kind,'response':str(item.get('response') or '')[:100]}
        if key not in people or people[key]['type']!='required':people[key]=person
    return list(people.values())


def normalize(rows,now,days):
    entries={};skipped=0
    for row in rows:
        if not isinstance(row,dict):skipped+=1;continue
        if str(row.get('eventType','')).lower() in ('master','recurringmaster'):continue
        start,end=instant(row.get('startTime')),instant(row.get('endTime'))
        identity=row.get('iCalUID') or row.get('objectId')
        if not start or not end or end<start or not identity:skipped+=1;continue
        key=hashlib.sha256(json.dumps([row.get('account'),identity,start.isoformat()]).encode()).hexdigest()
        modified=instant(row.get('lastModifiedTime')) or datetime.min.replace(tzinfo=timezone.utc)
        if key in entries and entries[key][0]>modified:continue
        entries[key]=(modified,row,start,end)
    result=[]
    for key,(_,row,start,end) in entries.items():
        if row.get('isCancelled') is True or row.get('isDraft') is True:continue
        if end<=now or start>=now+timedelta(days=days):continue
        result.append({'id':key,'meeting_id':hashlib.sha256(json.dumps([row.get('account'),row.get('objectId') or [row.get('iCalUID'),start.isoformat()]]).encode()).hexdigest(),'subject':str(row.get('subject') or 'Untitled meeting')[:2000],
          'start_time':start.isoformat(),'end_time':end.isoformat(),'organizer':str(row.get('organizerName') or '')[:500],
          'organizer_email':attendee_email(row.get('organizerEmail')),'attendees':attendees(row),'attendees_available':row.get('attendeesAvailable') is True,
          'location':str(row.get('location') or '')[:2000],'join_url':meeting_url(row),
          'all_day':row.get('isAllDayEvent') is True,'source':str(row.get('source') or 'Teams cache'),'response':str(row.get('responseType') or '')})
    return sorted(result,key=lambda row:row['start_time']),skipped

def snapshot(days=30,force=False,start=None,end=None,background=False):
    global _LAST_ATTEMPT
    if start is not None or end is not None:
        start,end=instant(start),instant(end)
        if not start or not end or not 0<(end-start).total_seconds()<=63*86400:raise ValueError('Choose a calendar range of up to 63 days with timezone offsets.')
    _hydrate()
    if background:
        with _LOCK:
            due=force or (time.time()-_CACHE.get('checked',0)>=60 and time.time()-_LAST_ATTEMPT>=60)
            if due and _REFRESH_LOCK.acquire(blocking=False):
                _LAST_ATTEMPT=time.time()
                try:threading.Thread(target=_refresh,kwargs={'force':force,'held':True},daemon=True).start()
                except Exception:_REFRESH_LOCK.release();raise
    else:_refresh(force=force)
    with _LOCK:
        data=dict(_CACHE);error=_LAST_ERROR
    rows=data.get('events',[])
    events,skipped=normalize(rows,start or datetime.now(timezone.utc),(end-start).total_seconds()/86400 if start else days)
    cached_dates=[instant(row.get('endTime')) for row in rows if isinstance(row,dict)]
    latest=max((d for d in cached_dates if d),default=None)
    return {'events':events,'latest_cached_end':latest.isoformat() if latest else None,'checked':data.get('checked'),'sources':data.get('sources',0),'skipped':skipped+data.get('skipped',0),
            'cached_records':len(rows),'refreshing':_REFRESH_LOCK.locked(),'refresh_error':error,'has_snapshot':'checked' in data,
            'warning':'From the calendar saved by Teams. Open Teams Calendar to download changes.'}
