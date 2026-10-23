"""Local project metadata; task membership is stored on each task."""
import uuid
import re
from datetime import datetime
from urllib.parse import urlsplit
from .config import read_config, update_config, _LOCK

COLORS=('blue','purple','green','orange','pink')

def valid_color(value):
    return isinstance(value,str) and (value in COLORS or re.fullmatch(r'#[0-9a-fA-F]{6}',value) is not None)

def list_projects():
    return [dict(project,color=project.get('color') if valid_color(project.get('color')) else COLORS[index%len(COLORS)]) for index,project in enumerate(read_config().get('projects', []))]

def validate_id(value):
    if value and value not in {p['id'] for p in list_projects()}:
        raise ValueError('Choose an existing project.')
    return value or ''

def validate_links(links):
    if not isinstance(links,list) or len(links)>20:raise ValueError('Add up to 20 opportunity or renewal links.')
    result=[]
    for link in links:
        if not isinstance(link,dict) or link.get('kind') not in ('isc','gainsight','deployment','other'):raise ValueError('Choose a link type.')
        label=link.get('label','');url=link.get('url','')
        if not isinstance(label,str) or len(label)>200:raise ValueError('Keep link labels under 200 characters.')
        if not isinstance(url,str) or len(url)>4000:raise ValueError('Invalid project link.')
        parsed=urlsplit(url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in url):raise ValueError('Use a complete HTTPS link without embedded credentials.')
        result.append({'kind':link['kind'],'label':label.strip(),'url':url})
    return result

def validate_meetings(meetings):
    if not isinstance(meetings,list) or len(meetings)>200:raise ValueError('Add up to 200 meetings per project.')
    result=[];seen=set()
    for meeting in meetings:
        if not isinstance(meeting,dict):raise ValueError('Invalid meeting.')
        row={}
        for key,limit in [('id',100),('title',300),('notes',4000),('transcript',500000),('recording_file_id',100),('occurred_at',50),('calendar_id',300),('meeting_url',4000),('recording_url',4000)]:
            value=meeting.get(key,'')
            if not isinstance(value,str) or len(value)>limit:raise ValueError('Invalid meeting '+key+'.')
            row[key]=value.strip()
        if not row['title']:raise ValueError('Enter a meeting name.')
        row['id']=row['id'] or uuid.uuid4().hex
        if row['id'] in seen:raise ValueError('Duplicate meeting ID.')
        seen.add(row['id'])
        if row['occurred_at']:
            try:
                instant=datetime.fromisoformat(row['occurred_at'].replace('Z','+00:00'))
                if instant.tzinfo is None:raise ValueError()
            except ValueError:raise ValueError('Choose a valid meeting date and timezone.') from None
        for key in ('meeting_url','recording_url'):
            if row[key]:validate_links([{'kind':'other','url':row[key]}])
        result.append(row)
    return result


def save(data,request_id=None):
    name=data.get('name','')
    if not isinstance(name,str) or not 1<=len(name.strip())<=100:raise ValueError('Enter a project name of up to 100 characters.')
    description=data.get('description','')
    if not isinstance(description,str) or len(description)>4000:raise ValueError('Keep project details under 4,000 characters.')
    if 'color' in data and not valid_color(data['color']):raise ValueError('Choose a color or enter a six-digit hex color such as #008080.')
    links=validate_links(data['links']) if 'links' in data else None
    meetings=validate_meetings(data['meetings']) if 'meetings' in data else None
    with _LOCK:
        rows=list_projects()
        if request_id:
            previous=next((p for p in rows if p.get('request_id')==request_id),None)
            if previous:return rows
        existing=next((p for p in rows if p['id']==data.get('id')),None)
        if data.get('id') and not existing:raise ValueError('Project not found.')
        if any(p['name'].casefold()==name.strip().casefold() and p is not existing for p in rows):raise ValueError('A project already has that name.')
        if existing is None:
            existing={'id':str(uuid.uuid4())};rows.append(existing)
            if request_id:existing['request_id']=request_id
        existing.update(name=name.strip(),description=description.strip(),color=data.get('color',existing.get('color',COLORS[(len(rows)-1)%len(COLORS)])))
        if links is not None:existing['links']=links
        if meetings is not None:existing['meetings']=meetings
        update_config({'projects':rows})
        return rows


def add_calendar_meeting(data):
    """Append one occurrence without overwriting a project's other work."""
    meeting=validate_meetings([data.get('meeting')])[0]
    if not meeting['calendar_id'] or not meeting['occurred_at']:raise ValueError('Choose a dated calendar event.')
    with _LOCK:
        rows=list_projects()
        project=next((p for p in rows if p['id']==data.get('project_id')),None)
        if project is None:raise ValueError('Project not found.')
        meetings=project.setdefault('meetings',[])
        instant=datetime.fromisoformat(meeting['occurred_at'].replace('Z','+00:00'))
        if any(m.get('calendar_id')==meeting['calendar_id'] and m.get('occurred_at') and datetime.fromisoformat(m['occurred_at'].replace('Z','+00:00'))==instant for m in meetings):return rows
        project['meetings']=validate_meetings(meetings+[meeting])
        update_config({'projects':rows})
        return rows
