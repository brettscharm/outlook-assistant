import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import tasks,config
class BoardTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  for obj,field,file in [(tasks,'TASKS_FILE','tasks'),(config,'CONFIG_PATH','config')]:
   p=patch.object(obj,field,Path(tmp.name)/file);p.start();self.addCleanup(p.stop)
 def test_move_completion_reopen_and_ownership(self):
  task=tasks.add_task('others','Send quote','Pat')['others_tasks'][0]
  moved=tasks.move_task(task['id'],'progress')['others_tasks'][0]
  self.assertEqual(moved['assignee'],'Pat');self.assertFalse(moved['completed'])
  self.assertTrue(tasks.move_task(task['id'],'done')['others_tasks'][0]['completed'])
  reopened=tasks.move_task(task['id'],'progress')['others_tasks'][0]
  self.assertFalse(reopened['completed']);self.assertEqual(reopened['lane_id'],'progress')
  self.assertEqual(tasks.load_tasks()['others_tasks'][0]['lane_id'],'progress')
 def test_configure_and_protect_occupied_lane(self):
  lanes=tasks.board_lanes()+[{'id':'waiting','name':'Waiting'}]
  tasks.save_board_lanes(lanes)
  task=tasks.add_task('my','Send quote')['my_tasks'][0];tasks.move_task(task['id'],'waiting')
  with self.assertRaises(ValueError):tasks.save_board_lanes(lanes[:-1])
  tasks.move_task(task['id'],'todo');tasks.save_board_lanes(lanes[:-1])
  with self.assertRaises(ValueError):tasks.move_task(task['id'],'waiting')
 def test_legacy_defaults_and_validation(self):
  self.assertEqual(tasks.task_lane({'completed':True}),'done')
  self.assertEqual(tasks.task_lane({}),'todo')
  with self.assertRaises(ValueError):tasks.save_board_lanes([{'id':'todo','name':' '},{'id':'done','name':'Done'}])
  with self.assertRaises(ValueError):tasks.save_board_lanes([{'id':'todo','name':'A'},{'id':'todo','name':'B'}])

 def test_new_task_owner_defaults_to_saved_user(self):
  config.update_config({'user_context':{'full_name':'Test User'}})
  self.assertEqual(tasks.add_task('my','Review proposal')['my_tasks'][0]['assignee'],'Test User')
  self.assertEqual(tasks.add_task('my','Call customer','Pat')['my_tasks'][0]['assignee'],'Pat')
 def test_task_sources_persist_and_edits_preserve_them(self):
  task=tasks.add_task('my','Reply',source_type='slack',source_url='https://example.slack.com/archives/C1/p123')['my_tasks'][0]
  tasks.edit_task(task['id'],'Reply today','Me','my','',description='Read https://example.com/doc')
  saved=tasks.load_tasks()['my_tasks'][0]
  self.assertEqual(saved['source_type'],'slack');self.assertEqual(saved['source_url'],task['source_url'])
  tasks.edit_task(task['id'],'Reply today','Me','my','',source_type='other',source_url='')
  self.assertEqual(tasks.load_tasks()['my_tasks'][0]['source_url'],'')
 def test_task_source_rejects_unsafe_urls(self):
  for value in ['javascript:alert(1)','file:///etc/passwd','https://example.com/a b']:
   with self.assertRaises(ValueError):tasks.add_task('my','Bad link',source_type='other',source_url=value)
 def test_priority_persists_preserves_and_clears(self):
  task=tasks.add_task('my','Send quote',priority='high')['my_tasks'][0]
  edited=tasks.edit_task(task['id'],'Send final quote','Me','my','')['my_tasks'][0]
  self.assertEqual(edited['priority'],'high')
  tasks.move_task(task['id'],'progress')
  self.assertEqual(tasks.load_tasks()['my_tasks'][0]['priority'],'high')
  tasks.edit_task(task['id'],'Send final quote','Me','my','',priority='none')
  self.assertEqual(tasks.load_tasks()['my_tasks'][0]['priority'],'none')
  with self.assertRaises(ValueError):tasks.edit_task(task['id'],'Bad edit','Me','my','',priority='urgent')
  self.assertEqual(tasks.load_tasks()['my_tasks'][0]['text'],'Send final quote')
  with self.assertRaises(ValueError):tasks.add_task('my','Bad task',priority='urgent')
