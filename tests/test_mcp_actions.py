import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from outlook_plugin import config,tasks,mcp_server as m
class ActionsTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  for module,field,name in [(config,'CONFIG_PATH','config'),(tasks,'TASKS_FILE','tasks')]:
   p=patch.object(module,field,Path(tmp.name)/name);p.start();self.addCleanup(p.stop)
  config.update_config({'user_context':{'full_name':'Test User'}})
  self.engine=Mock()
 def call(self,tool_name,**args):return m.handle_tool_call(self.engine,tool_name,args)
 def create(self,**kwargs):return self.call('create_task',text='Prepare proposal',request_id='create-1',**kwargs)
 def test_create_retry_edit_preserves_fields_and_rejects_stale(self):
  original=self.create(description='Keep details',co_owners=['Pat'],priority='high')
  self.assertEqual(original['task']['assignee'],'Test User')
  self.assertEqual(self.create()['task']['id'],original['task']['id'])
  edited=self.call('edit_task',task_id=original['task']['id'],expected_revision=original['revision'],text='Prepare final proposal')
  self.assertEqual(edited['task']['description'],'Keep details')
  self.assertEqual(edited['task']['co_owners'],['Pat'])
  with self.assertRaises(ValueError):self.call('edit_task',task_id=original['task']['id'],expected_revision=original['revision'],text='Stale')
  self.assertEqual(len(tasks.load_tasks()['my_tasks']),1)
 def test_project_create_retry_partial_edit_and_assignment(self):
  p=self.call('create_project',name='Renewal',description='Retain',request_id='project-1')
  self.assertEqual(self.call('create_project',name='Renewal',request_id='project-1')['project']['id'],p['project']['id'])
  updated=self.call('edit_project',project_id=p['project']['id'],expected_revision=p['revision'],name='Acme renewal')
  self.assertEqual(updated['project']['description'],'Retain')
  with self.assertRaises(ValueError):self.call('edit_project',project_id=p['project']['id'],expected_revision=p['revision'],description='stale')
  task=self.create(project_id=p['project']['id']);self.assertEqual(task['task']['project_id'],p['project']['id'])
 def test_checklist_updates_move_and_waiting(self):
  task=self.create();identifier=task['task']['id']
  step=self.call('add_subtask',task_id=identifier,text='Review pricing',request_id='step-1')
  step=self.call('add_subtask',task_id=identifier,text='Review pricing',request_id='step-1')
  self.assertEqual(len(step['task']['subtasks']),1)
  completed=self.call('set_subtask_completed',task_id=identifier,subtask_id=step['task']['subtasks'][0]['id'],completed=True)
  self.assertTrue(completed['task']['subtasks'][0]['completed'])
  note=self.call('add_task_update',task_id=identifier,text='Pricing received',request_id='note-1')
  note=self.call('add_task_update',task_id=identifier,text='Pricing received',request_id='note-1')
  self.assertEqual(len(note['task']['updates']),1)
  waiting=self.call('set_task_next_step',task_id=identifier,expected_revision=note['revision'],waiting_on='Pat',next_step='Review')
  revised=self.call('set_task_next_step',task_id=identifier,expected_revision=waiting['revision'],next_step='Send')
  self.assertEqual(revised['task']['waiting_on'],'Pat')
  self.assertTrue(self.call('move_task',task_id=identifier,lane_id='done')['task']['completed'])
  self.assertFalse(self.call('move_task',task_id=identifier,lane_id='todo')['task']['completed'])
 def test_invalid_inputs_never_write(self):
  for fields in [{'priority':'critical'},{'co_owners':'Pat'},{'due_date':'not-a-date'},{'project_id':'missing'},{'source_url':'javascript:alert(1)'},{'description':'x'*4001}]:
   with self.assertRaises(ValueError):self.create(**fields)
  self.assertEqual(tasks.load_tasks()['my_tasks'],[])
 def test_email_evidence_required_and_deduplication(self):
  self.engine.get_email_details.return_value={'id':'mail1','body':'Please prepare a proposal.','subject':'Proposal'}
  with self.assertRaises(ValueError):self.create(email_id='mail1',evidence='Invented')
  one=self.create(email_id='mail1',evidence='prepare a proposal')
  two=self.call('create_task',text='Prepare proposal',request_id='another',email_id='mail1',evidence='prepare a proposal')
  self.assertEqual(one['task']['id'],two['task']['id'])
