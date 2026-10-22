import tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
from outlook_plugin import tasks,task_reminders as r
class ReminderTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  p=patch.object(tasks,'TASKS_FILE',Path(self.tmp.name)/'tasks');p.start();self.addCleanup(p.stop)
  self.now=datetime(2026,10,22,12,tzinfo=timezone.utc)
 def task(self,repeat=0):
  return tasks.add_task('my','Reminder test',reminder={'at':(self.now-timedelta(days=2)).isoformat(),'repeat_days':repeat})['my_tasks'][0]
 def test_restart_and_once_only(self):
  self.task();calls=[];r.check(self.now,calls.append);r.check(self.now+timedelta(hours=1),calls.append);self.assertEqual(calls,['Reminder test'])
 def test_completed_skipped_and_repeat_catches_up_once(self):
  t=self.task(1);tasks.toggle_task(t['id']);calls=[];r.check(self.now,calls.append);self.assertFalse(calls);tasks.toggle_task(t['id']);r.check(self.now,calls.append);r.check(self.now,calls.append);self.assertEqual(len(calls),1);r.check(self.now+timedelta(days=1),calls.append);self.assertEqual(len(calls),2)
 def test_clear_and_unrelated_edit_preserve_delivery(self):
  t=self.task();r.check(self.now,lambda _:None);saved=tasks.load_tasks()['my_tasks'][0];reminder=saved['reminder'];tasks.edit_task(t['id'],'Changed','Me','my','',reminder={'at':reminder['at'],'repeat_days':0});self.assertEqual(tasks.load_tasks()['my_tasks'][0]['reminder'],reminder);tasks.edit_task(t['id'],'Changed','Me','my','',reminder={});self.assertEqual(tasks.load_tasks()['my_tasks'][0]['reminder'],{})
 def test_invalid_values_and_shell_safety(self):
  for value in [{'at':'bad'},{'at':'2026-10-22T12:00:00'},{'at':self.now.isoformat(),'repeat_days':-1}]:
   with self.assertRaises(ValueError):r.validate(value)
  title='Task " & do shell script "bad'
  with patch.object(subprocess,'run') as run:r.notify(title)
  self.assertEqual(run.call_args.args[0][-1],title);self.assertNotIn(title,run.call_args.args[0][-2])
 def test_delivery_failure_retries(self):
  self.task()
  def fail(_):raise OSError('unavailable')
  r.check(self.now,fail);self.assertNotIn('notified_at',tasks.load_tasks()['my_tasks'][0]['reminder'])
