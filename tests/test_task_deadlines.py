import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import tasks,calendar_cache
class TaskDeadlineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  p=patch.object(tasks,'TASKS_FILE',Path(self.tmp.name)/'tasks.json');p.start();self.addCleanup(p.stop)
  self.event={'meeting_id':'meeting1','subject':'Planning','start_time':'2026-11-02T15:00:00+00:00'}
 def test_meeting_color_persist_reschedule_and_missing(self):
  with patch.object(calendar_cache,'snapshot',return_value={'events':[self.event]}):
   rows=tasks.add_task('my','Prepare',color='blue',deadline={'kind':'meeting','meeting_id':'meeting1','offset_minutes':30})
  task=rows['my_tasks'][0];self.assertEqual(task['color'],'blue');self.assertEqual(task['deadline']['due_at'],'2026-11-02T14:30:00+00:00')
  tasks.refresh_meeting_deadlines([dict(self.event,start_time='2026-11-03T16:00:00+00:00')])
  self.assertEqual(tasks.load_tasks()['my_tasks'][0]['deadline']['due_at'],'2026-11-03T15:30:00+00:00')
  tasks.refresh_meeting_deadlines([]);self.assertEqual(tasks.load_tasks()['my_tasks'][0]['deadline']['availability'],'unavailable')
  with patch.object(calendar_cache,'snapshot',return_value={'events':[]}):
   rows=tasks.edit_task(task['id'],'Still editable','Me','my','',deadline={'kind':'meeting','meeting_id':'meeting1','offset_minutes':30})
  self.assertEqual(rows['my_tasks'][0]['text'],'Still editable')
  rows=tasks.edit_task(task['id'],'Date task','Me','my','2026-11-04',deadline={'kind':'date'})
  self.assertEqual(rows['my_tasks'][0]['deadline'],{'kind':'date'})
 def test_invalid_color_and_unknown_meeting_do_not_save(self):
  with self.assertRaises(ValueError):tasks.add_task('my','Bad',color='invalid')
  with patch.object(calendar_cache,'snapshot',return_value={'events':[]}):
   with self.assertRaises(ValueError):tasks.add_task('my','Bad',deadline={'kind':'meeting','meeting_id':'missing'})
  self.assertEqual(tasks.load_tasks()['my_tasks'],[])
