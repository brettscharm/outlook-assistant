"""Local project metadata; task membership is stored on each task."""
import uuid
from .config import read_config, update_config, _LOCK

def list_projects():
    return read_config().get('projects', [])

def validate_id(value):
    if value and value not in {p['id'] for p in list_projects()}:
        raise ValueError('Choose an existing project.')
    return value or ''

def save(data,request_id=None):
    name=data.get('name','')
    if not isinstance(name,str) or not 1<=len(name.strip())<=100:raise ValueError('Enter a project name of up to 100 characters.')
    description=data.get('description','')
    if not isinstance(description,str) or len(description)>4000:raise ValueError('Keep project details under 4,000 characters.')
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
        existing.update(name=name.strip(),description=description.strip())
        update_config({'projects':rows})
        return rows
