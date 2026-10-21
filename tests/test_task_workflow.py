import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import task_workflow as w,config,tasks
from outlook_plugin.ai_agent import BobAIAgent
class Engine:
 def __init__(self,rows):self.rows=rows
 def get_active_backend(self):return self
 def get_emails(self,**kw):return self.rows
 def get_email_details(self,id):return next((r for r in self.rows if r['id']==id),None)
def message(i=1):return dict(id=str(i),subject='Proposal',sender='Jane <jane@example.com>',received_time='2026-10-20T12:00:00Z',body='Brett, send the proposal by October 30, 2026.')
def item(i=1):return dict(text='Send proposal',description='Send the proposal requested by Brett.',type='my',owner='Brett',email_id=str(i),email_subject='Proposal',evidence='Brett, send the proposal',owner_evidence='Brett, send the proposal',due_date='2026-10-30',due_evidence='by October 30, 2026',due_note='')
class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for obj,attr,name in [(config,'CONFIG_PATH','config'),(tasks,'TASKS_FILE','tasks'),(w,'WORKFLOW_FILE','review')]:
   p=patch.object(obj,attr,Path(self.tmp.name)/name);p.start();self.addCleanup(p.stop)
  config.update_config({'user_context':{'full_name':'Brett Scharmett','email_addresses':'brett@example.com'}})
  w._STOP.clear();w.JOB.update(running=False,scanned=0,total=0,usage=0)
  self.opts={'since':'2026-10-01','mode':'mine','interval':0,'budget':1}
 def test_date_filter_resume_and_dismissal(self):
  engine=Engine([dict(message(0),received_time='2026-09-30T23:00:00Z'),message()])
  with patch.object(BobAIAgent,'extract_tasks',return_value=[item()]) as extract:
   w.run(engine,self.opts);self.assertEqual(extract.call_args[0][0][0]['id'],'1')
   review=w.snapshot()['suggestions'][0];w.action({'action':'dismiss','id':review['id'],'reason':'not_role'})
   w.run(engine,self.opts);self.assertEqual(extract.call_count,1)
  self.assertEqual(w.snapshot()['suggestions'][0]['status'],'dismissed')
  w.action({'action':'restore','id':review['id']});self.assertEqual(w.snapshot()['suggestions'][0]['status'],'review')
 def test_accept_is_idempotent_with_dates_owner_source(self):
  with patch.object(BobAIAgent,'extract_tasks',return_value=[item()]):w.run(Engine([message()]),self.opts)
  sid=w.snapshot()['suggestions'][0]['id'];w.action({'action':'accept','id':sid});w.action({'action':'accept','id':sid,'text':'Edited duplicate'})
  rows=tasks.load_tasks()['my_tasks'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['description'],'Send the proposal requested by Brett.');self.assertEqual(rows[0]['due_date'],'2026-10-30');self.assertEqual(rows[0]['assignee'],'Brett Scharmett');self.assertEqual(rows[0]['email_id'],'1')
  tasks.edit_task(rows[0]['id'],'Changed task','Jane','others','2026-11-01')
  summary=w.snapshot('1')['suggestions'][0]
  self.assertEqual(summary['due_date'],'2026-11-01');self.assertEqual(summary['owner'],'Jane')
 def test_legacy_budget_does_not_limit_batches(self):
  config.update_config({'task_scan':dict(self.opts,budget=1)})
  self.assertNotIn('budget',w.options())
  with patch.object(BobAIAgent,'extract_tasks',return_value=[]) as extract:
   w.run(Engine([message(i) for i in range(32)]),self.opts)
   self.assertEqual(extract.call_count,4);self.assertEqual(w.JOB['status'],'complete');self.assertEqual(w.JOB['scanned'],32)
   w.run(Engine([message(i) for i in range(32)]),self.opts);self.assertEqual(extract.call_count,4)
 def test_evidence_guards_ownership_and_dates(self):
  invalid=dict(item(),text='Other',evidence='send the proposal',owner_evidence='Imagined owner',due_evidence='invented date')
  model=BobAIAgent('fake')
  with patch.object(model,'_call_llm',return_value=json.dumps({'tasks':[item(),invalid]})):
   result=model.extract_tasks([dict(message(),content=message()['body'])])
  self.assertEqual(result[0]['description'],'Send the proposal requested by Brett.');self.assertEqual(result[0]['type'],'my');self.assertEqual(result[0]['due_date'],'2026-10-30');self.assertEqual(result[1]['type'],'my');self.assertEqual(result[1]['owner'],config.read_config()['user_context']['full_name']);self.assertEqual(result[1]['owner_evidence'],'');self.assertEqual(result[1]['due_date'],'')
 def test_automatic_default_waits_for_setup(self):
  self.assertEqual(w.options()['interval'],15)
  config.update_config({'user_context':{}})
  w.settings(dict(self.opts,interval=15))
  self.assertEqual(w.automatic_state(),'identity')
  w.settings(self.opts)
  self.assertEqual(w.automatic_state(),'paused')

 def test_scheduler_runs_immediately_then_waits(self):
  from unittest.mock import Mock
  with patch.object(w,'automatic_state',return_value='ready'),patch.object(w.time,'monotonic',side_effect=[0,60,901]),patch.object(w,'start') as start:
   stop=Mock();stop.wait.side_effect=[False,False,False,True]
   w.scheduler(Engine([message()]),stop)
   self.assertEqual(start.call_count,2)

 def test_scheduler_requires_verified_connection(self):
  from unittest.mock import Mock
  for state in ('identity','bob','paused'):
   with patch.object(w,'automatic_state',return_value=state),patch.object(w,'start') as start:
    stop=Mock();stop.wait.side_effect=[False,True]
    w.scheduler(Engine([]),stop);start.assert_not_called()

 def test_scheduler_respects_recent_persisted_check(self):
  from unittest.mock import Mock
  from datetime import datetime
  w.save({'suggestions':{},'processed':{},'last_check':datetime.now().isoformat()})
  with patch.object(w,'automatic_state',return_value='ready'),patch.object(w,'start') as start:
   stop=Mock();stop.wait.side_effect=[False,True]
   w.scheduler(Engine([]),stop);start.assert_not_called()

 def test_pause_stops_current_batch_and_survives_reload(self):
  from unittest.mock import Mock
  with patch.object(w,'_RUN',Mock(locked=lambda:True)),patch.object(w,'stop') as stop:
   w.settings(dict(self.opts,interval=0));stop.assert_called_once()
  self.assertEqual(w.options()['interval'],0)

 def test_stop_preserves_unprocessed_messages(self):
  w._STOP.set()
  with patch.object(BobAIAgent,'extract_tasks') as extract:
   w.run(Engine([message()]),self.opts);extract.assert_not_called()
  self.assertEqual(w.JOB['status'],'stopped');self.assertEqual(w.load()['processed'],{})

 def test_first_run_defaults_to_seven_days_and_remembers_start(self):
  from datetime import date,timedelta
  self.assertEqual(w.options()['since'],(date.today()-timedelta(days=7)).isoformat())
  with patch.object(BobAIAgent,'extract_tasks',return_value=[]):w.run(Engine([]),self.opts)
  self.assertEqual(w.options()['since'],self.opts['since'])

 def test_arrival_runs_before_periodic_interval(self):
  from unittest.mock import Mock
  first=message();new=message(2)
  w.save({'suggestions':{},'processed':{w.key_for(dict(id='1',subject=first['subject'],sender=first['sender'],received_time=first['received_time'],content=first['body']),w.options()):{'email_id':'1'}},'last_check':w.datetime.now().isoformat()})
  engine=Engine([first])
  calls=0
  def tick(_):
   nonlocal calls
   calls+=1
   if calls==2:engine.rows.append(new)
   return calls>2
  with patch.object(w,'automatic_state',return_value='ready'),patch.object(w.time,'monotonic',side_effect=[0,60]),patch.object(w,'start') as start:
   w.scheduler(engine,Mock(wait=tick));start.assert_called_once()

 def test_idle_watch_does_not_start_bob(self):
  from unittest.mock import Mock
  with patch.object(w,'automatic_state',return_value='ready'),patch.object(w,'start') as start:
   shutdown=Mock();shutdown.wait.side_effect=[False,True]
   w.scheduler(Engine([]),shutdown);start.assert_not_called()

class SyncTests(unittest.TestCase):
 setUp = WorkflowTests.setUp
 def test_manual_sync_starts_without_changing_paused_preference(self):
  from unittest.mock import Mock
  engine=Mock()
  with patch.object(w,'identity_ready',return_value=True),patch.object(w,'get_bob_api_key',return_value='fake'),patch.object(w,'_RUN') as running,patch.object(w,'_BOB_LOCK') as bob,patch.object(w,'start') as start:
   running.locked.return_value=False;bob.locked.return_value=False
   self.assertEqual(w.sync_tasks(engine)['state'],'running');start.assert_called_once_with(engine)
 def test_wake_respects_pause(self):
  with patch.object(w,'options',return_value={'interval':0}),patch.object(w,'start') as start:
   self.assertEqual(w.sync_tasks(None,automatic=True)['state'],'paused');start.assert_not_called()
 def test_sync_does_not_duplicate_scan_or_interrupt_chat(self):
  with patch.object(w,'identity_ready',return_value=True),patch.object(w,'get_bob_api_key',return_value='fake'),patch.object(w,'_RUN') as running,patch.object(w,'_BOB_LOCK') as bob,patch.object(w,'start') as start:
   running.locked.return_value=True
   self.assertEqual(w.sync_tasks(None)['state'],'running');start.assert_not_called()
   running.locked.return_value=False;bob.locked.return_value=True
   self.assertEqual(w.sync_tasks(None)['state'],'busy');start.assert_not_called()

 def test_sync_explains_missing_bob(self):
  with patch.object(w,'identity_ready',return_value=True),patch.object(w,'get_bob_api_key',return_value='fake'),patch.object(w,'_RUN') as running,patch.object(w,'_BOB_LOCK') as bob,patch('outlook_plugin.ai_agent.bob_executable',return_value=None),patch.object(w,'start') as start:
   running.locked.return_value=False;bob.locked.return_value=False
   result=w.sync_tasks(None)
   self.assertEqual(result['state'],'setup');self.assertIn('Settings',result['message']);start.assert_not_called()

 def test_existing_unclear_suggestion_defaults_to_me(self):
  w.save({'suggestions':{'qa':dict(item(),id='qa',type='unclear',owner='Owner unclear',status='review')},'processed':{}})
  suggestion=w.snapshot()['suggestions'][0]
  self.assertEqual(suggestion['type'],'my');self.assertEqual(suggestion['owner'],'Brett Scharmett')
  w.action({'action':'accept','id':'qa'})
  self.assertEqual(tasks.load_tasks()['my_tasks'][0]['assignee'],'Brett Scharmett')
 def test_completion_requires_evidence_and_review(self):
  task=tasks.add_task('my','Send proposal')['my_tasks'][0]
  mail=dict(message(),content='The proposal has been sent to Acme.')
  model=BobAIAgent('fake')
  payload={'tasks':[],'completed':[{'task_id':task['id'],'email_id':'1','evidence':'The proposal has been sent to Acme.'},{'task_id':task['id'],'email_id':'1','evidence':'invented'}]}
  with patch.object(model,'_call_llm',return_value=json.dumps(payload)):model.extract_tasks([mail],active_tasks=[task])
  self.assertEqual(len(model.last_completions),1)
  suggestion=dict(model.last_completions[0],id='complete-one',status='review',reason='')
  w.save({'suggestions':{'complete-one':suggestion},'processed':{}})
  self.assertFalse(tasks.load_tasks()['my_tasks'][0]['completed'])
  w.action({'action':'accept','id':'complete-one'})
  self.assertTrue(tasks.load_tasks()['my_tasks'][0]['completed'])
 def test_stale_completion_is_rejected(self):
  import hashlib
  task=tasks.add_task('my','Send proposal')['my_tasks'][0]
  expected=hashlib.sha256(json.dumps(task,sort_keys=True).encode()).hexdigest()
  w.save({'suggestions':{'c':dict(item(),id='c',action_type='complete',task_id=task['id'],expected=expected,status='review')},'processed':{}})
  tasks.edit_task(task['id'],'Send revised proposal','Me','my','')
  with self.assertRaisesRegex(ValueError,'changed'):w.action({'action':'accept','id':'c'})
  self.assertFalse(tasks.load_tasks()['my_tasks'][0]['completed'])
