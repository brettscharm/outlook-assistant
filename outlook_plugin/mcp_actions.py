"""Validated MCP workspace mutations using the same persistence as the app."""
import hashlib
import json
from datetime import date
from . import tasks, projects, task_progress
from .config import _LOCK as CONFIG_LOCK

S=lambda n=200:{'type':'string','maxLength':n}
ID=S(100)
REQUEST=dict(ID,description='A unique request ID. Reuse it when retrying the same creation to avoid duplicates.',minLength=1)
REV=dict(S(64),description='Revision returned by get_task/get_project. Rejects edits if the item changed.',minLength=64)
FIELDS={
 'text':dict(S(2000),minLength=1),'description':S(4000),'owner':dict(S(200),description='Name or email. Set type=others when assigning someone other than the current user.'),
 'type':{'type':'string','enum':['my','others','unclear'],'description':'my assigns the saved user as owner.'},
 'co_owners':{'type':'array','maxItems':20,'items':S(200)},'due_date':dict(S(10),description='YYYY-MM-DD, or empty to clear.'),
 'priority':{'type':'string','enum':['none','low','medium','high']},'project_id':dict(ID,description='Existing project ID, or empty to unassign.'),
 'source_type':{'type':'string','enum':['email','slack','teams','meeting','other']},'source_url':S(4000),
 'color':{'type':'string','enum':['none','blue','purple','green','orange','pink'],'description':'Personal color used when no project is assigned. Project tasks display the project color.'},
 'deadline':{'type':'object','properties':{'kind':{'type':'string','enum':['date','meeting']},'meeting_id':S(200),'offset_minutes':{'type':'integer','enum':[0,15,30,60,1440]}},'required':['kind'],'additionalProperties':False}
}


LINKS={'type':'array','maxItems':20,'items':{'type':'object','properties':{'kind':{'type':'string','enum':['isc','gainsight','deployment','other']},'label':S(200),'url':S(4000)},'required':['url'],'additionalProperties':False}}

MEETINGS={'type':'array','maxItems':200,'items':{'type':'object','properties':{k:S(n) for k,n in [('id',100),('title',300),('notes',4000),('occurred_at',50),('calendar_id',300),('meeting_url',4000),('recording_url',4000)]},'required':['title'],'additionalProperties':False}}

def definitions(tool):
 return [
  tool('get_task','Read a task and its revision before editing.',{'task_id':ID},['task_id']),
  tool('get_project','Read a project and its revision before editing.',{'project_id':ID},['project_id']),
  tool('list_task_lanes','Read available board lane IDs and names.'),
  tool('create_task','Create a saved task. Defaults to the current user. Reuse request_id on retries.',dict(FIELDS,request_id=REQUEST,email_id=ID,evidence=S(1200)),['text','request_id'],write=True),
  tool('edit_task','Edit only supplied fields; omitted fields stay unchanged. Get the latest revision first.',dict(FIELDS,task_id=ID,expected_revision=REV),['task_id','expected_revision'],write=True),
  tool('move_task','Move a task to a lane. The done lane completes it; other lanes reopen it.',{'task_id':ID,'lane_id':ID,'expected_revision':REV},['task_id','lane_id'],write=True),
  tool('create_project','Create a project. Reuse request_id on retries.',{'name':dict(S(100),minLength=1),'description':S(4000),'color':dict(S(7),description='Any #RRGGBB color, or an existing named project color.'),'links':LINKS,'meetings':MEETINGS,'request_id':REQUEST},['name','request_id'],write=True),
  tool('edit_project','Edit project name/description; omitted fields stay unchanged.',{'project_id':ID,'name':dict(S(100),minLength=1),'description':S(4000),'color':dict(S(7),description='Any #RRGGBB color, or an existing named project color.'),'links':LINKS,'meetings':MEETINGS,'expected_revision':REV},['project_id','expected_revision'],write=True),
  tool('add_task_update','Append a dated progress note. Reuse request_id on retries.',{'task_id':ID,'text':dict(S(4000),minLength=1),'request_id':REQUEST},['task_id','text','request_id'],write=True),
  tool('add_subtask','Add a checklist step. Reuse request_id on retries.',{'task_id':ID,'text':dict(S(500),minLength=1),'request_id':REQUEST},['task_id','text','request_id'],write=True),
  tool('set_subtask_completed','Complete or reopen one checklist step.',{'task_id':ID,'subtask_id':ID,'completed':{'type':'boolean'},'expected_revision':REV},['task_id','subtask_id','completed'],write=True),
  tool('set_task_next_step','Set waiting-on and/or next step; omitted fields stay unchanged.',{'task_id':ID,'waiting_on':S(300),'next_step':S(2000),'expected_revision':REV},['task_id','expected_revision'],write=True),
 ]


def revision(item):return hashlib.sha256(json.dumps(item,sort_keys=True).encode()).hexdigest()
def task_by_id(identifier):
 item=next((t for group in tasks.load_tasks().values() for t in group if t['id']==identifier),None)
 if item is None:raise ValueError('Task not found.')
 return item

def project_by_id(identifier):
 item=next((p for p in projects.list_projects() if p['id']==identifier),None)
 if item is None:raise ValueError('Project not found.')
 return item

def result(item,kind):return {kind:item,'revision':revision(item)}
def check_revision(item,args):
 if revision(item)!=args['expected_revision']:raise ValueError('This item changed. Read it again before editing.')

def handle(engine,name,args):
 # Match the app lock order so reads, partial edits and saves are serialized.
 with tasks._LOCK,CONFIG_LOCK:
  if name=='list_task_lanes':return tasks.board_lanes()
  if name=='get_task':return result(task_by_id(args['task_id']),'task')
  if name=='get_project':return result(project_by_id(args['project_id']),'project')
  if name in ('create_project','edit_project'):
   if name=='create_project':
    rows=projects.save({'name':args['name'],'description':args.get('description',''),**{k:args[k] for k in ('color','links','meetings') if k in args}},request_id='mcp-'+args['request_id'])
    item=next(p for p in rows if p.get('request_id')=='mcp-'+args['request_id'])
   else:
    current=project_by_id(args['project_id']);check_revision(current,args)
    projects.save({'id':current['id'],'name':args.get('name',current['name']),'description':args.get('description',current.get('description','')),'color':args.get('color',current['color']),'links':args.get('links',current.get('links',[])),'meetings':args.get('meetings',current.get('meetings',[]))})
    item=project_by_id(current['id'])
   return result(item,'project')
  if name=='create_task':
   if not args['text'].strip():raise ValueError('Enter a task title.')
   if args.get('due_date'):date.fromisoformat(args['due_date'])
   identifier='mcp-'+hashlib.sha256(args['request_id'].encode()).hexdigest()
   existing=next((t for group in tasks.load_tasks().values() for t in group if t['id']==identifier),None)
   if existing:return result(existing,'task')
   source=None
   if args.get('email_id'):
    email=engine.get_email_details(args['email_id']);quote=args.get('evidence','')
    if not email or not quote.strip() or ' '.join(quote.split()) not in ' '.join((email.get('body') or email.get('preview') or '').split()):raise ValueError('Source email or supporting quote could not be verified.')
    source={'email_id':args['email_id'],'email_subject':email.get('subject',''),'evidence':quote}
   saved=tasks.add_task(args.get('type','my'),args['text'],args.get('owner'),args.get('due_date'),source=source,request_id=identifier,**{k:args[k] for k in ('description','co_owners','priority','project_id','source_type','source_url','color','deadline') if k in args})
   item=next((t for group in saved.values() for t in group if t['id']==identifier or source and t.get('email_id')==source['email_id'] and ' '.join(t['text'].lower().split())==' '.join(args['text'].lower().split())),None)
   if item is None:raise ValueError('Task could not be saved.')
   return result(item,'task')
  item=task_by_id(args['task_id'])
  if name=='edit_task':
   check_revision(item,args)
   tasks.edit_task(item['id'],args.get('text',item['text']),args.get('owner',item.get('assignee','')),args.get('type',item.get('type','my')),args.get('due_date',item.get('due_date','')),**{k:args[k] for k in ('description','co_owners','priority','project_id','source_type','source_url','color','deadline') if k in args})
  elif name=='move_task':
   if 'expected_revision' in args:check_revision(item,args)
   tasks.move_task(item['id'],args['lane_id'])
  elif name in ('add_task_update','add_subtask'):
   task_progress.change(item['id'],'add_update' if name=='add_task_update' else 'add_subtask',dict(args,request_id='mcp-'+hashlib.sha256(args['request_id'].encode()).hexdigest()))
  elif name=='set_subtask_completed':
   if 'expected_revision' in args:check_revision(item,args)
   task_progress.change(item['id'],'set_subtask',args)
  elif name=='set_task_next_step':
   check_revision(item,args)
   task_progress.change(item['id'],'set_waiting',{'waiting_on':args.get('waiting_on',item.get('waiting_on','')),'next_step':args.get('next_step',item.get('next_step',''))})
  else:raise ValueError('Unknown action.')
  return result(task_by_id(item['id']),'task')
