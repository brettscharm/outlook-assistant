import base64,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from outlook_plugin import config,tasks,drafts,task_files,task_workflow,mcp_server as m

class WorkspaceTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  for module,key,name in [(config,'CONFIG_PATH','config'),(tasks,'TASKS_FILE','tasks'),(drafts,'DRAFTS_FILE','drafts'),(task_workflow,'WORKFLOW_FILE','review'),(task_files,'ROOT','files')]:
   p=patch.object(module,key,Path(tmp.name)/name);p.start();self.addCleanup(p.stop)
  self.engine=Mock();config.update_config({'bob_api_key':'DO-NOT-EXPOSE','user_context':{'full_name':'Test User','role':'Engineer'}})
 def call(self,tool_name,**args):return m.handle_tool_call(self.engine,tool_name,args)
 def task(self):return self.call('create_task',text='Test task',request_id='task')
 def test_preferences_partial_stale_and_secrets(self):
  p=self.call('get_preferences');self.assertNotIn('DO-NOT-EXPOSE',json.dumps(p))
  edited=self.call('edit_preferences',expected_revision=p['revision'],priorities='Renewals',excluded_domains=['example.com'])
  self.assertEqual(edited['preferences']['role'],'Engineer')
  self.assertEqual(config.read_config()['bob_api_key'],'DO-NOT-EXPOSE')
  with self.assertRaises(ValueError):self.call('edit_preferences',expected_revision=p['revision'],role='Stale')
  with self.assertRaises(ValueError):self.call('edit_preferences',expected_revision=edited['revision'],bob_api_key='bad')
 def test_companies_and_profiles(self):
  self.call('link_company',domains=['example.com','example.org'],company='Example')
  self.call('pin_company',domain='example.com',starred=True)
  c=self.call('list_companies');self.assertEqual(c['domains']['example.org'],'Example');self.assertTrue(c['favorites'])
  p=self.call('list_ai_profiles')['profiles'][0]
  changed=self.call('edit_ai_profile',profile_id=p['profile']['id'],expected_revision=p['revision'],examples='Be concise')
  self.assertEqual(changed['profile']['instructions'],p['profile']['instructions'])
  with self.assertRaises(ValueError):self.call('edit_ai_profile',profile_id=p['profile']['id'],expected_revision=p['revision'],examples='stale')
 def test_drafts_preserve_and_conflict(self):
  d=self.call('get_draft',draft_id='email1');self.assertEqual(d['revision'],0)
  d=self.call('edit_draft',draft_id='email1',revision=0,text='Hello',html='<b>Hello</b>')
  d=self.call('edit_draft',draft_id='email1',revision=d['revision'],subject='Subject')
  self.assertEqual(d['text'],'Hello');self.assertEqual(d['html'],'<b>Hello</b>')
  with self.assertRaises(ValueError):self.call('edit_draft',draft_id='email1',revision=0,text='stale')
  self.call('edit_draft',draft_id='email1',revision=d['revision'],deleted=True)
  self.assertEqual(self.call('list_drafts')['total'],0)
 def test_board_entries_delete_and_project_links(self):
  p=self.call('create_project',name='Project',request_id='p',links=[{'kind':'isc','label':'Opportunity','url':'https://example.com/op/1'}])
  p=self.call('edit_project',project_id=p['project']['id'],expected_revision=p['revision'],description='Details')
  self.assertEqual(len(p['project']['links']),1)
  t=self.task();t=self.call('edit_task',task_id=t['task']['id'],expected_revision=t['revision'],project_id=p['project']['id'])
  with self.assertRaises(ValueError):self.call('delete_project',project_id=p['project']['id'],expected_revision=p['revision'])
  t=self.call('add_subtask',task_id=t['task']['id'],text='First',request_id='s')
  t=self.call('edit_task_entry',task_id=t['task']['id'],expected_revision=t['revision'],entry_id=t['task']['subtasks'][0]['id'],kind='subtasks',text='Edited')
  self.assertEqual(t['task']['subtasks'][0]['text'],'Edited')
  board=self.call('get_task_board');lanes=board['lanes'];lanes[0]['name']='Ready'
  self.assertEqual(self.call('edit_task_board',expected_revision=board['revision'],lanes=lanes)['lanes'][0]['name'],'Ready')
  with self.assertRaises(ValueError):self.call('delete_task',task_id=t['task']['id'],expected_revision='0'*64)
  self.call('delete_task',task_id=t['task']['id'],expected_revision=t['revision'])
  self.call('delete_project',project_id=p['project']['id'],expected_revision=p['revision'])
  self.assertEqual(self.call('list_projects')['total'],0)
 def test_attachments_scope_chunks_and_removal(self):
  t=self.task()['task'];owner={'kind':'task','owner':t['id']}
  rows=self.call('add_attachment',**owner,name='note.txt',content=base64.b64encode(b'abcdef').decode())
  chunk=self.call('read_attachment',**owner,file_id=rows[0]['id'],length=3)
  self.assertEqual(base64.b64decode(chunk['content']),b'abc');self.assertEqual(chunk['next_offset'],3)
  chunk=self.call('read_attachment',**owner,file_id=rows[0]['id'],offset=3)
  self.assertEqual(base64.b64decode(chunk['content']),b'def');self.assertIsNone(chunk['next_offset'])
  for args in [dict(owner,owner='../outside'),dict(owner,file_id='../outside')]:
   with self.assertRaises(ValueError):self.call('read_attachment',**dict({'file_id':rows[0]['id']},**args))
  with self.assertRaises(ValueError):self.call('add_attachment',**owner,name='../note.txt',content='YQ==')
  with self.assertRaises(ValueError):self.call('add_attachment',**owner,name='note.txt',content='!'*10)
  self.assertEqual(self.call('remove_attachment',**owner,file_id=rows[0]['id']),[])
 def test_review_restore_and_scan_settings(self):
  task_workflow.save({'suggestions':{'s':{'id':'s','status':'review','type':'my','text':'Action','owner':'Test User'}},'processed':{}})
  s=self.call('get_review_task',suggestion_id='s')
  s=self.call('review_task',suggestion_id='s',expected_revision=s['revision'],action='dismiss',reason='not_role')
  self.assertEqual(s['suggestion']['status'],'dismissed')
  s=self.call('review_task',suggestion_id='s',expected_revision=s['revision'],action='restore')
  self.assertEqual(self.call('list_review_tasks')['total'],1)
  s=self.call('review_task',suggestion_id='s',expected_revision=s['revision'],action='accept',priority='high')
  self.assertEqual(self.call('list_tasks')['items'][0]['priority'],'high')
  settings=self.call('get_task_scan_settings')
  updated=self.call('edit_task_scan_settings',expected_revision=settings['revision'],interval=60)
  self.assertEqual(updated['settings']['interval'],60)
  with patch.object(task_workflow,'start',return_value={'running':True}) as start:
   self.call('start_task_scan');start.assert_called_once_with(self.engine)
 def test_calendar_range_and_schema_coverage(self):
  with patch('outlook_plugin.calendar_cache.snapshot',return_value={'events':[{'id':'meeting','url':'https://teams.microsoft.com/example'}],'checked':1}) as snapshot:
   data=self.call('get_calendar_range',start='2026-10-21T00:00:00-04:00',end='2026-10-22T00:00:00-04:00')
   self.assertEqual(data['items'][0]['id'],'meeting');self.assertNotIn('events',data)
  names=[t['name'] for t in m.TOOLS_DEFINITION];self.assertEqual(len(names),len(set(names)))
  for tool in m.TOOLS_DEFINITION:self.assertFalse(tool['inputSchema']['additionalProperties'])
