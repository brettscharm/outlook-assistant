import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import config,projects
class CalendarProjects(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  p=patch.object(config,'CONFIG_PATH',Path(tmp.name)/'config');p.start();self.addCleanup(p.stop)
  self.project=projects.save({'name':'Acme','description':'Keep this','meetings':[{'title':'Past call','notes':'Keep notes'}]})[0]
  self.meeting={'title':'Planning','calendar_id':'event1','occurred_at':'2026-10-22T13:00:00Z','meeting_url':'https://example.com/call'}
 def test_append_idempotent_and_preserves_project(self):
  data={'project_id':self.project['id'],'meeting':self.meeting}
  projects.add_calendar_meeting(data);rows=projects.add_calendar_meeting(data)
  self.assertEqual(len(rows[0]['meetings']),2);self.assertEqual(rows[0]['description'],'Keep this');self.assertEqual(rows[0]['meetings'][0]['notes'],'Keep notes')
  projects.add_calendar_meeting(dict(data,meeting=dict(self.meeting,occurred_at='2026-10-22T09:00:00-04:00')))
  self.assertEqual(len(projects.list_projects()[0]['meetings']),2)
 def test_recurring_occurrences_stay_separate(self):
  for day in (22,23):projects.add_calendar_meeting({'project_id':self.project['id'],'meeting':dict(self.meeting,occurred_at=f'2026-10-{day}T13:00:00Z')})
  self.assertEqual(len(projects.list_projects()[0]['meetings']),3)
 def test_unknown_project_rejected(self):
  with self.assertRaisesRegex(ValueError,'Project not found'):projects.add_calendar_meeting({'project_id':'missing','meeting':self.meeting})
