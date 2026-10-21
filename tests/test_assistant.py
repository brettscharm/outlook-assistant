import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import assistant,email_chat,tasks,config
from test_email_chat import Engine
class AssistantTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  for obj,name,file in [(email_chat,'CHAT_FILE','chat'),(tasks,'TASKS_FILE','tasks'),(config,'CONFIG_PATH','config')]:
   p=patch.object(obj,name,Path(tmp.name)/file);p.start();self.addCleanup(p.stop)
 def test_creation_requires_apply_and_is_idempotent(self):
  class AI:
   def _call_llm(self,*args):return json.dumps({'answer':'Ready to add this task.','actions':[{'kind':'create_task','text':'Call Pat'}]})
  data=assistant.ask(Engine(),'Add a task to call Pat',ai=AI());action=data['messages'][-1]['actions'][0]
  self.assertEqual(tasks.load_tasks()['my_tasks'],[])
  assistant.apply(action['id']);assistant.apply(action['id'])
  self.assertEqual(len(tasks.load_tasks()['my_tasks']),1)
 def test_stale_task_is_not_overwritten(self):
  task=tasks.add_task('my','Original')['my_tasks'][0]
  action=assistant.proposal({'kind':'move_task','task_id':task['id'],'lane_id':'done'},{task['id']:task},tasks.board_lanes(),set())
  email_chat.save({'messages':[{'actions':[action]}]});tasks.edit_task(task['id'],'Edited','Me','my','')
  with self.assertRaises(ValueError):assistant.apply(action['id'])
  self.assertFalse(tasks.load_tasks()['my_tasks'][0]['completed'])
 def test_reject_unknown_actions_and_domains(self):
  for raw in [{'kind':'send_email'},{'kind':'link_company','domains':['unknown.com'],'company':'Acme'},{'kind':'move_task','task_id':'unknown','lane_id':'done'}]:
   with self.assertRaises(ValueError):assistant.proposal(raw,{},tasks.board_lanes(),{'known.com'})
 def test_company_link_requires_apply(self):
  action=assistant.proposal({'kind':'link_company','domains':['example.com'],'company':'Example'},{},tasks.board_lanes(),{'example.com'})
  email_chat.save({'messages':[{'actions':[action]}]});assistant.apply(action['id'])
  self.assertEqual(config.read_config()['domain_companies']['example.com'],'Example')
