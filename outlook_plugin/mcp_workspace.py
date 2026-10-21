"""Explicit, credential-free MCP access to local workspace features."""
import base64
from . import config, tasks, projects, drafts, contacts, ai_profiles, task_workflow, task_files
from .mcp_actions import S, ID, REV, FIELDS, result, check_revision, task_by_id, project_by_id

BOOL={'type':'boolean'}
def obj(fields):return {'type':'object','properties':fields,'additionalProperties':False}
def array(items,n=100):return {'type':'array','items':items,'maxItems':n}
CONTEXT={k:S(12000) for k in ('full_name','email_addresses','role','accounts','priorities','writing_style')}
PREFS=dict(CONTEXT,writing_samples=S(24000),excluded_domains=array(S(253),1000))
OWNER={'kind':{'type':'string','enum':['task','project']},'owner':ID}

def definitions(tool):
 from .mcp_server import PAGE
 specs=[
 ('list_project_emails','Read project emails linked through tasks or directly; unavailable mail has no content.',dict(PAGE,project_id=ID,query=S(1000)),['project_id'],False),
 ('link_project_email','Associate a cached email with a project, or remove its direct association. Does not change Outlook or task links.',{'project_id':ID,'email_id':S(1000),'remove':BOOL},['project_id','email_id'],True),
 ('list_contact_groups','Read saved company contact groups, member emails and numeric revisions.',{},[],False),
 ('save_contact_group','Create or update a company contact group; reuse the ID on retry. Revision 0 creates; existing groups require their latest revision. remove deletes the group only.',{'id':ID,'revision':{'type':'integer','minimum':0,'maximum':2147483647},'domain':S(253),'name':S(100),'emails':array(S(254),1000),'remove':BOOL},['id','revision'],True),
 ('list_mail_folders','Read mailbox folder IDs and names.',{},[],False),
 ('list_mail_accounts','Read locally configured mailbox accounts.',{},[],False),
 ('get_task_scan_settings','Read automatic task discovery settings and revision.',{},[],False),
 ('edit_task_scan_settings','Update task discovery settings. Scheduled scans consume Bob allowance.',{'since':S(10),'mode':{'type':'string','enum':['mine','all']},'interval':{'type':'integer','enum':[0,15,30,60]},'excluded_domains':array(S(253),1000),'expected_revision':REV},['expected_revision'],True),
 ('start_task_scan','Start task discovery from cached mail. Sends mail content to Bob and consumes Bob allowance; returns job state.',{},[],True),
 ('stop_task_scan','Request cancellation of the active task discovery job.',{},[],True),
 ('get_preferences','Read identity, role, accounts, writing preferences and exclusions. Never returns keys.',{},[],False),
 ('edit_preferences','Update supplied preferences only, using the latest revision.',dict(PREFS,expected_revision=REV),['expected_revision'],True),
 ('list_companies','Read domain-to-company mappings and pinned companies.',{},[],False),
 ('link_company','Link multiple sender domains to one company. Empty company removes links.',{'domains':array(S(253),1000),'company':S(200)},['domains','company'],True),
 ('pin_company','Pin or unpin the company linked to a domain.',{'domain':S(253),'starred':BOOL},['domain','starred'],True),
 ('list_ai_profiles','Read editable specialist instructions, examples and activity.',{},[],False),
 ('edit_ai_profile','Update supplied specialist instructions or examples.',{'profile_id':ID,'instructions':S(12000),'examples':S(12000),'expected_revision':REV},['profile_id','expected_revision'],True),
 ('get_usage','Read recorded Bob usage; Reading usage does not call Bob.',{},[],False),
 ('list_review_tasks','Read suggestions, including dismissed items that can be restored.',dict(PAGE,status={'type':'string','enum':['review','dismissed','accepted','all']}),[],False),
 ('get_review_task','Read one suggestion and revision.',{'suggestion_id':ID},['suggestion_id'],False),
 ('review_task','Accept, dismiss or restore a suggestion. quick dismiss does not provide training feedback.',dict(FIELDS,suggestion_id=ID,expected_revision=REV,action={'type':'string','enum':['accept','dismiss','restore']},reason={'type':'string','enum':list(task_workflow.REASONS)}),['suggestion_id','expected_revision','action'],True),
 ('list_drafts','Read local saved drafts. This does not read Outlook unsent drafts.',dict(PAGE),[],False),
 ('get_draft','Read local draft and numeric revision; absent draft has revision 0.',{'draft_id':S(1000)},['draft_id'],False),
 ('edit_draft','Create or edit local draft fields. Does not send email or change Outlook.',{'draft_id':S(1000),'revision':{'type':'integer','minimum':0,'maximum':2147483647},'text':S(50000),'html':S(150000),'intent':S(4000),'subject':S(2000),'sender':S(2000),'deleted':BOOL},['draft_id','revision'],True),
 ('get_task_board','Read lanes and board revision.',{},[],False),
 ('edit_task_board','Rename, reorder or add lanes. Occupied lanes cannot be removed.',{'lanes':array(obj({'id':ID,'name':S(60)}),12),'expected_revision':REV},['lanes','expected_revision'],True),
 ('delete_task','Delete one saved task after reading its revision. Attachment copies are retained.',{'task_id':ID,'expected_revision':REV},['task_id','expected_revision'],True),
 ('delete_project','Delete an empty project. Move its tasks first. Attachment copies are retained.',{'project_id':ID,'expected_revision':REV},['project_id','expected_revision'],True),
 ('edit_task_entry','Edit or remove a progress note or subtask without replacing other task fields.',{'task_id':ID,'entry_id':ID,'kind':{'type':'string','enum':['updates','subtasks']},'text':S(4000),'remove':BOOL,'expected_revision':REV},['task_id','entry_id','kind','expected_revision'],True),
 ('list_attachments','List document copies attached to a task or project.',OWNER,list(OWNER),False),
 ('read_attachment','Read an attachment as a bounded base64 chunk. Use next_offset until null.',dict(OWNER,file_id=ID,offset={'type':'integer','minimum':0,'maximum':2147483648},length={'type':'integer','minimum':1,'maximum':32768}),[*OWNER,'file_id'],False),
 ('add_attachment','Attach a base64 document copy, up to 48 KiB per MCP upload. Larger files can be attached in the app.',dict(OWNER,name=S(200),content=S(65536)),[*OWNER,'name','content'],True),
 ('remove_attachment','Permanently remove an attached copy by ID, leaving the original file untouched.',dict(OWNER,file_id=ID),[*OWNER,'file_id'],True),
 ('get_calendar_range','Read cached meetings in an explicit timezone-aware ISO date/time range, up to 63 days, with call links.',dict(PAGE,start=S(50),end=S(50)),['start','end'],False),
 ]
 return [tool(n,d,p,r,write=w) for n,d,p,r,w in specs]

def preferences():
 c=config.read_config();ctx=c.get('user_context',{})
 return {**{k:ctx.get(k,'') for k in CONTEXT},'writing_samples':c.get('writing_samples',''),'excluded_domains':c.get('excluded_domains',[])}

def suggestion(identifier):
 item=task_workflow.load()['suggestions'].get(identifier)
 if item is None:raise ValueError('Suggestion not found.')
 return item

def handle(engine,name,args):
 from .mcp_server import page
 if name in ('list_project_emails','link_project_email'):
  from . import project_mail
  if name=='list_project_emails':return project_mail.listing(engine,args['project_id'],args.get('query',''),args.get('offset',0),args.get('limit',25))
  return project_mail.link(engine,args['project_id'],args['email_id'],args.get('remove',False))
 if name in ('list_contact_groups','save_contact_group'):
  from . import contact_groups
  return contact_groups.listing() if name=='list_contact_groups' else contact_groups.save(args)
 if name=='list_mail_folders':return engine.list_folders()
 if name=='list_mail_accounts':return engine.list_accounts()
 if name in ('get_task_scan_settings','edit_task_scan_settings'):
  with task_workflow._LOCK,config._LOCK:
   current=task_workflow.options()
   if name=='edit_task_scan_settings':check_revision(current,args);task_workflow.settings(args)
   return result(task_workflow.options(),'settings')
 if name=='start_task_scan':return task_workflow.start(engine)
 if name=='stop_task_scan':return task_workflow.stop()
 if name in ('get_preferences','edit_preferences'):
  with config._LOCK:
   current=preferences()
   if name=='edit_preferences':
    check_revision(current,args)
    c=config.read_config();ctx=dict(c.get('user_context',{}));ctx.update({k:args[k] for k in CONTEXT if k in args})
    changes={'user_context':ctx}
    for key in ('writing_samples','excluded_domains'):
     if key in args:changes[key]=args[key]
    if 'excluded_domains' in changes:
     from .mail_filters import normalize_domains
     changes['excluded_domains']=normalize_domains(changes['excluded_domains'])
    config.update_config(changes)
   return result(preferences(),'preferences')
 if name=='list_companies':
  c=config.read_config();return {'domains':c.get('domain_companies',{}),'favorites':c.get('favorite_companies',[])}
 if name=='link_company':return contacts.link_companies(args['domains'],args['company'])
 if name=='pin_company':return contacts.set_favorite(args['domain'],args['starred'])
 if name=='list_ai_profiles':return {'profiles':[result(p,'profile') for p in ai_profiles.profiles()],'activity':ai_profiles.activity()}
 if name=='edit_ai_profile':
  with config._LOCK:
   current=next((p for p in ai_profiles.profiles() if p['id']==args['profile_id']),None)
   if current is None:raise ValueError('Unknown profile.')
   check_revision(current,args)
   ai_profiles.save({**current,**{k:args[k] for k in ('instructions','examples') if k in args}})
   return result(next(p for p in ai_profiles.profiles() if p['id']==current['id']),'profile')
 if name=='get_usage':
  from .usage import snapshot
  return snapshot()
 if name in ('list_review_tasks','get_review_task','review_task'):
  with task_workflow._LOCK:
   if name=='list_review_tasks':
    status=args.get('status','review');rows=list(task_workflow.load()['suggestions'].values())
    return page([result(r,'suggestion') for r in rows if status=='all' or r['status']==status],args)
   current=suggestion(args['suggestion_id'])
   if name=='review_task':
    check_revision(current,args)
    task_workflow.action({**args,'id':args['suggestion_id']})
   return result(suggestion(args['suggestion_id']),'suggestion')
 if name in ('list_drafts','get_draft','edit_draft'):
  with drafts._LOCK:
   entries=drafts.load()['entries']
   if name=='list_drafts':return page([dict(v,id=k) for k,v in entries.items() if not v.get('deleted')],args)
   identifier=args['draft_id'];current=entries.get(identifier,{'revision':0})
   if name=='edit_draft':
    saved=drafts.save_changes({'changes':[{**current,**args,'id':identifier}]})
    if saved['conflicts']:raise ValueError('Draft changed. Read it again before editing.')
    current=drafts.load()['entries'][identifier]
   return dict(current,id=identifier)
 if name in ('get_task_board','edit_task_board','delete_task','delete_project','edit_task_entry'):
  with tasks._LOCK,config._LOCK:
   if name in ('get_task_board','edit_task_board'):
    current=tasks.board_lanes()
    if name=='edit_task_board':check_revision(current,args);tasks.save_board_lanes(args['lanes'])
    return result(tasks.board_lanes(),'lanes')
   if name=='delete_project':
    current=project_by_id(args['project_id']);check_revision(current,args)
    if any(t.get('project_id')==current['id'] for rows in tasks.load_tasks().values() for t in rows):raise ValueError('Move the project’s tasks before deleting it.')
    config.update_config({'projects':[p for p in projects.list_projects() if p['id']!=current['id']]});return {'deleted':current['id']}
   current=task_by_id(args['task_id']);check_revision(current,args)
   if name=='delete_task':tasks.delete_task(current['id']);return {'deleted':current['id']}
   store=tasks.load_tasks();task=next(t for rows in store.values() for t in rows if t['id']==current['id'])
   rows=task.get(args['kind'],[]);entry=next((r for r in rows if r['id']==args['entry_id']),None)
   if entry is None:raise ValueError('Entry not found.')
   if args.get('remove'):task[args['kind']]=[r for r in rows if r['id']!=entry['id']]
   else:
    text=args.get('text','').strip()
    if not text or len(text)>(500 if args['kind']=='subtasks' else 4000):raise ValueError('Enter valid entry text.')
    entry['text']=text
   tasks.save_tasks(store);return result(task,'task')
 if name in ('list_attachments','read_attachment','add_attachment','remove_attachment'):
  with task_files._LOCK:
   rows=task_files.listing(args['kind'],args['owner'])
   if name=='list_attachments':return rows
   if name=='add_attachment':return task_files.change(dict(args,action='add'))
   item=next((r for r in rows if r['id']==args['file_id']),None)
   if item is None:raise ValueError('Attachment not found.')
   if name=='remove_attachment':return task_files.change(dict(args,id=item['id'],action='remove'))
   path=task_files.file_path(task_files.directory(args['kind'],args['owner']),item)
   offset=args.get('offset',0);length=args.get('length',32768)
   with path.open('rb') as f:f.seek(offset);data=f.read(length)
   end=offset+len(data)
   return {'name':item['name'],'content':base64.b64encode(data).decode(),'encoding':'base64','next_offset':end if end<path.stat().st_size else None}
 if name=='get_calendar_range':
  from .calendar_cache import snapshot
  data=snapshot(start=args['start'],end=args['end']);events=data.pop('events');return {**data,**page(events,args)}
 raise ValueError('Unknown tool.')
