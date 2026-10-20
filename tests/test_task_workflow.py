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
def item(i=1):return dict(text='Send proposal',type='my',owner='Brett',email_id=str(i),email_subject='Proposal',evidence='Brett, send the proposal',owner_evidence='Brett, send the proposal',due_date='2026-10-30',due_evidence='by October 30, 2026',due_note='')
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
  rows=tasks.load_tasks()['my_tasks'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['due_date'],'2026-10-30');self.assertEqual(rows[0]['assignee'],'Brett');self.assertEqual(rows[0]['email_id'],'1')
  tasks.edit_task(rows[0]['id'],'Changed task','Jane','others','2026-11-01')
  summary=w.snapshot('1')['suggestions'][0]
  self.assertEqual(summary['due_date'],'2026-11-01');self.assertEqual(summary['owner'],'Jane')
 def test_usage_limit_and_resume(self):
  with patch.object(BobAIAgent,'extract_tasks',return_value=[]) as extract:
   w.run(Engine([message(i) for i in range(12)]),self.opts)
   self.assertEqual(extract.call_count,1);self.assertEqual(w.JOB['status'],'paused');self.assertEqual(w.JOB['scanned'],10)
   w.run(Engine([message(i) for i in range(12)]),self.opts);self.assertEqual(extract.call_count,2);self.assertEqual(w.JOB['total'],2)
 def test_evidence_guards_ownership_and_dates(self):
  invalid=dict(item(),text='Other',evidence='send the proposal',owner_evidence='Imagined owner',due_evidence='invented date')
  model=BobAIAgent('fake')
  with patch.object(model,'_call_llm',return_value=json.dumps({'tasks':[item(),invalid]})):
   result=model.extract_tasks([dict(message(),content=message()['body'])])
  self.assertEqual(result[0]['type'],'my');self.assertEqual(result[0]['due_date'],'2026-10-30');self.assertEqual(result[1]['type'],'unclear');self.assertEqual(result[1]['due_date'],'')
 def test_schedule_requires_identity(self):
  config.update_config({'user_context':{}})
  with self.assertRaises(ValueError):w.settings(dict(self.opts,interval=15))
  self.assertEqual(w.settings(self.opts)['interval'],0)

 def test_scheduler_runs_only_at_configured_interval(self):
  with patch.object(w,'options',return_value=dict(self.opts,interval=15)),patch.object(w.time,'monotonic',side_effect=[0,901,901]),patch.object(w,'start') as start:
   from unittest.mock import Mock
   stop=Mock();stop.wait.side_effect=[False,True]
   w.scheduler(Engine([]),stop)
   start.assert_called_once()
 def test_stop_preserves_unprocessed_messages(self):
  w._STOP.set()
  with patch.object(BobAIAgent,'extract_tasks') as extract:
   w.run(Engine([message()]),self.opts);extract.assert_not_called()
  self.assertEqual(w.JOB['status'],'stopped');self.assertEqual(w.load()['processed'],{})
