"""Local project metadata; task membership is stored on each task."""
import uuid
from urllib.parse import urlsplit
from .config import read_config, update_config, _LOCK

COLORS=('blue','purple','green','orange','pink')

def list_projects():
    return [dict(project,color=project.get('color') if project.get('color') in COLORS else COLORS[index%len(COLORS)]) for index,project in enumerate(read_config().get('projects', []))]

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

def save(data,request_id=None):
    name=data.get('name','')
    if not isinstance(name,str) or not 1<=len(name.strip())<=100:raise ValueError('Enter a project name of up to 100 characters.')
    description=data.get('description','')
    if not isinstance(description,str) or len(description)>4000:raise ValueError('Keep project details under 4,000 characters.')
    if 'color' in data and data['color'] not in COLORS:raise ValueError('Choose a supported project color.')
    links=validate_links(data['links']) if 'links' in data else None
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
        update_config({'projects':rows})
        return rows
