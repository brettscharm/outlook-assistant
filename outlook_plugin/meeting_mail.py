"""Discover meeting evidence across all cached folders, including Deleted Items.
These are invitation/response records, never authoritative calendar events.
"""
import re
from datetime import datetime,timezone
from .mail_archive import attachment_path


def ics_time(value,params):
    try:
        if len(value)==8:return datetime.strptime(value,'%Y%m%d').date().isoformat()
        if value.endswith('Z'):return datetime.strptime(value,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc).isoformat()
        zone=next((p[5:] for p in params if p.startswith('TZID=')),None)
        if not zone:return '' # Floating times have no reliable absolute timezone.
        # Older desktop runtimes omit zoneinfo. Keep mail/sync usable; never guess a timezone.
        from zoneinfo import ZoneInfo
        return datetime.strptime(value,'%Y%m%dT%H%M%S').replace(tzinfo=ZoneInfo(zone.strip('"'))).isoformat()
    except (ValueError,KeyError,ImportError):return ''


def parse_ics(content):
    if not isinstance(content,str) or len(content)>2_000_000:return []
    lines=re.sub(r'\r?\n[ \t]','',content).splitlines()
    method='';current=None;events=[]
    for line in lines:
        if ':' not in line:continue
        left,value=line.split(':',1);parts=left.split(';');name=parts[0].upper()
        if name=='METHOD':method=value.upper()
        if name=='BEGIN' and value=='VEVENT':current={};continue
        if name=='END' and value=='VEVENT':
            if current is not None:
                current['method']=method;events.append(current)
            current=None;continue
        if current is None:continue
        if name in ('DTSTART','DTEND'):current['start_time' if name=='DTSTART' else 'end_time']=ics_time(value,parts[1:])
        elif name in ('UID','SUMMARY','STATUS','RECURRENCE-ID','SEQUENCE','RRULE'):current[name.lower()]=value[:4000]
        elif name=='ATTENDEE':
            responses=[part.split('=',1)[1] for part in parts[1:] if part.startswith('PARTSTAT=')]
            if responses:current.setdefault('responses',[]).extend(responses)
    return events


def discover(engine):
    # Do not omit trash/deleted folders: Outlook can move processed invitations there.
    backend=engine.get_active_backend()
    complete_rows=hasattr(backend,'get_cached_messages')
    rows=backend.get_cached_messages() if complete_rows else engine.get_emails(folder='all',limit=1000000)
    candidates=[]
    for row in rows:
        attachments=row.get('attachments') or []
        if any(str(a.get('name','')).lower().endswith('.ics') for a in attachments) or re.search(r'\b(meeting|invitation|accepted|declined|cancell?ed|tentative)\b',str(row.get('subject','')),re.I):
            candidates.append(row)
    candidates.sort(key=lambda row:row.get('received_time',''),reverse=True)
    try:profile=engine.get_active_backend().profile()
    except (AttributeError,RuntimeError,OSError):profile=None
    result=[]
    for row in candidates[:500]:
        message=row if complete_rows else engine.get_email_details(str(row['id'])) or row
        calendar=[]
        body=message.get('body') or ''
        if 'BEGIN:VCALENDAR' in body:calendar.extend(parse_ics(body))
        if profile:
            for attachment in message.get('attachments') or []:
                if not str(attachment.get('name','')).lower().endswith('.ics') or not attachment.get('downloaded'):continue
                path=attachment_path(profile,attachment.get('path'))
                if path:
                    try:
                        if path.stat().st_size<=2_000_000:calendar.extend(parse_ics(path.read_text(errors='replace')))
                    except OSError:pass
        result.append({'email_id':str(row['id']),'subject':row.get('subject',''),'folder':row.get('folder',''),'received_time':row.get('received_time',''),'sender':row.get('sender',''),
                       'details':calendar,'status':'Email evidence — verify in Outlook'})
    return {'items':result,'matched':len(candidates),'truncated':len(candidates)>500,'includes_deleted':True}
