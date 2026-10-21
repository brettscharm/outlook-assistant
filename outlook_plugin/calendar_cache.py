"""Read materialized Teams calendar entries. Never infer free/busy or expand series."""
import hashlib,json,subprocess,threading,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
_LOCK=threading.Lock()
_CACHE={}

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
        result.append({'id':key,'meeting_id':hashlib.sha256(json.dumps([row.get('account'),row.get('objectId') or [identity,start.isoformat()]]).encode()).hexdigest(),'subject':str(row.get('subject') or 'Untitled meeting')[:2000],
          'start_time':start.isoformat(),'end_time':end.isoformat(),'organizer':str(row.get('organizerName') or '')[:500],
          'location':str(row.get('location') or '')[:2000],'join_url':str(row.get('skypeTeamsMeetingUrl') or '')[:8000],
          'all_day':row.get('isAllDayEvent') is True,'source':str(row.get('source') or 'Teams cache'),'response':str(row.get('responseType') or '')})
    return sorted(result,key=lambda row:row['start_time']),skipped

def snapshot(days=30,force=False,start=None,end=None):
    if start is not None or end is not None:
        start,end=instant(start),instant(end)
        if not start or not end or not 0<(end-start).total_seconds()<=63*86400:raise ValueError('Choose a calendar range of up to 63 days with timezone offsets.')
    with _LOCK:
        if force or time.time()-_CACHE.get('checked',0)>60:
            helper=Path(__file__).parent/'bin/teams-calendar-darwin'
            if not helper.exists():raise RuntimeError('Install the current desktop release to add the calendar reader.')
            try:run=subprocess.run([str(helper)],capture_output=True,text=True,timeout=100)
            except subprocess.TimeoutExpired:raise RuntimeError('Teams calendar took too long to read. Let Teams finish syncing and retry.') from None
            if run.returncode:raise RuntimeError('Could not read the Teams calendar cache. Open Teams and its Calendar, then retry.')
            try:data=json.loads(run.stdout)
            except ValueError:raise RuntimeError('Calendar reader returned an unreadable result.') from None
            if not isinstance(data,dict) or not isinstance(data.get('events'),list):raise RuntimeError('Calendar reader returned an unsupported format.')
            _CACHE.clear();_CACHE.update(data,checked=time.time())
        events,skipped=normalize(_CACHE['events'],start or datetime.now(timezone.utc),(end-start).total_seconds()/86400 if start else days)
        cached_dates=[instant(row.get('endTime')) for row in _CACHE['events'] if isinstance(row,dict)]
        latest=max((d for d in cached_dates if d),default=None)
        return {'events':events,'latest_cached_end':latest.isoformat() if latest else None,'checked':_CACHE['checked'],'sources':_CACHE.get('sources',0),'skipped':skipped+_CACHE.get('skipped',0),
                'cached_records':len(_CACHE['events']),
                'warning':'From the calendar saved by Teams. Open Teams Calendar to download changes.'}
