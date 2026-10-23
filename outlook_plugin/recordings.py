"""Read-only library of saved recording attachments and project meeting transcripts."""
from . import projects, tasks, task_files


def listing(query='',project_id='',offset=0,limit=20):
    rows=[];warnings=[];project_rows=projects.list_projects()
    names={p['id']:p['name'] for p in project_rows}
    def files(kind,owner):
        try:return [f for f in task_files.listing(kind,owner) if f.get('recording')]
        except (ValueError,OSError):warnings.append('Some saved attachments could not be read.');return []
    for f in files('library','recordings'):
        pid=f.get('project_id','')
        if project_id and pid!=project_id:continue
        rows.append(dict(id='file:library:'+f['id'],title=f['name'],project_id=pid,project_name=names.get(pid,'No project'),owner_kind='library',owner_id='recordings',file=f,has_transcript=False,occurred_at=f.get('occurred_at','')))
    for p in project_rows:
        if project_id and p['id']!=project_id:continue
        attached=files('project',p['id']);library={f['id']:f for f in files('library','recordings') if f.get('project_id')==p['id']};by_id={f['id']:f for f in attached};used=set()
        for m in p.get('meetings',[]):
            if not (m.get('recording_url') or m.get('recording_file_id') or m.get('transcript')):continue
            file=by_id.get(m.get('recording_file_id')) or library.get(m.get('recording_file_id'));is_library=m.get('recording_file_id') in library;used.add(m.get('recording_file_id'))
            if is_library:rows=[r for r in rows if r['id']!='file:library:'+m['recording_file_id']]
            rows.append(dict(id='meeting:'+p['id']+':'+m['id'],title=m['title'],project_id=p['id'],project_name=p['name'],meeting_id=m['id'],owner_kind='library' if is_library else 'project',owner_id='recordings' if is_library else p['id'],file=file,url=m.get('recording_url',''),has_transcript=bool(m.get('transcript','').strip()),occurred_at=m.get('occurred_at',''),missing_file=bool(m.get('recording_file_id') and not file)))
        for f in attached:
            if f['id'] not in used:rows.append(dict(id='file:project:'+p['id']+':'+f['id'],title=f['name'],project_id=p['id'],project_name=p['name'],owner_kind='project',owner_id=p['id'],file=f,has_transcript=False,occurred_at=f.get('occurred_at','')))
    for group in tasks.load_tasks().values():
        for task in group:
            pid=task.get('project_id','')
            if project_id and pid!=project_id:continue
            for f in files('task',task['id']):rows.append(dict(id='file:task:'+task['id']+':'+f['id'],title=f['name'],project_id=pid,project_name=names.get(pid,'No project'),owner_kind='task',owner_id=task['id'],task_title=task['text'],file=f,has_transcript=False,occurred_at=f.get('occurred_at','')))
    needle=str(query).strip().casefold()
    if needle:rows=[r for r in rows if needle in ' '.join(str(r.get(k,'')) for k in ('title','project_name','task_title')).casefold() or needle in str((r.get('file') or {}).get('name','')).casefold()]
    rows.sort(key=lambda r:(not bool(r.get('occurred_at')),r['title'].casefold()))
    # ISO offsets are normalized for chronological ordering by instant.
    from datetime import datetime
    def stamp(row):
        try:return datetime.fromisoformat(row.get('occurred_at','').replace('Z','+00:00')).timestamp()
        except (ValueError,TypeError,OverflowError):return float('-inf')
    rows.sort(key=stamp,reverse=True)
    offset=max(0,int(offset));limit=max(1,min(100,int(limit)))
    return {'items':rows[offset:offset+limit],'total':len(rows),'offset':offset,'limit':limit,'projects':[{'id':p['id'],'name':p['name']} for p in project_rows],'warnings':list(dict.fromkeys(warnings))}
