import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import task_progress as p, tasks, config

class ProgressTests(unittest.TestCase):
 def setUp(self):
  folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
  for obj,key,name in [(tasks,'TASKS_FILE','tasks'),(config,'CONFIG_PATH','config')]:
   mock=patch.object(obj,key,Path(folder.name)/name);mock.start();self.addCleanup(mock.stop)
  self.task=tasks.add_task('my','Prepare proposal')['my_tasks'][0];self.id=self.task['id']
 def test_updates_idempotence_and_waiting_preserve_owner(self):
  for _ in range(2):p.change(self.id,'add_update',{'text':'Received pricing','request_id':'one'})
  p.change(self.id,'set_waiting',{'waiting_on':'Legal','next_step':'Send proposal'})
  row=tasks.load_tasks()['my_tasks'][0]
  self.assertEqual(len(row['updates']),1);self.assertEqual(row['assignee'],self.task['assignee']);self.assertEqual(row['waiting_on'],'Legal')
 def test_checklist_does_not_complete_parent(self):
  p.change(self.id,'add_subtask',{'text':'Review pricing','request_id':'one'})
  for _ in range(2):p.change(self.id,'set_subtask',{'subtask_id':'one','completed':True})
  row=tasks.load_tasks()['my_tasks'][0];self.assertTrue(row['subtasks'][0]['completed']);self.assertFalse(row['completed'])
  with self.assertRaises(ValueError):p.change(self.id,'set_subtask',{'subtask_id':'one','completed':'false'})
 def test_handoff_is_idempotent_excludes_history_and_mail(self):
  p.change(self.id,'add_update',{'text':'Private update','request_id':'one'})
  p.change(self.id,'add_subtask',{'text':'Review','request_id':'step'})
  payload=p.export_task(self.id);self.assertNotIn('updates',payload['task']);self.assertNotIn('email_id',payload['task'])
  p.import_task(payload);p.import_task(payload)
  rows=tasks.load_tasks()['my_tasks'];self.assertEqual(len(rows),2)
  imported=next(t for t in rows if t['id']!=self.id)
  self.assertEqual(imported['subtasks'][0]['text'],'Review');self.assertFalse(imported['subtasks'][0]['completed'])
 def test_bad_import_is_atomic(self):
  payload=p.export_task(self.id);payload['subtasks']=['x'*501]
  with self.assertRaises(ValueError):p.import_task(payload)
  self.assertEqual(len(tasks.load_tasks()['my_tasks']),1)
