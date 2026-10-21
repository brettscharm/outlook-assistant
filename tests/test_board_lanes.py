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
