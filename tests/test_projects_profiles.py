import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import projects,ai_profiles,config,tasks
class LocalFeatures(unittest.TestCase):
 def setUp(self):
  d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup)
  for obj,key,name in [(config,'CONFIG_PATH','config'),(tasks,'TASKS_FILE','tasks')]:
   p=patch.object(obj,key,Path(d.name)/name);p.start();self.addCleanup(p.stop)
 def test_project_membership_survives_edit_and_move(self):
  project=projects.save({'name':'Renewal'})[0]
  task=tasks.add_task('my','Send proposal',project_id=project['id'])['my_tasks'][0]
  tasks.edit_task(task['id'],'Send final proposal','Me','my','')
  tasks.move_task(task['id'],'done')
  self.assertEqual(tasks.load_tasks()['my_tasks'][0]['project_id'],project['id'])
  projects.save({'id':project['id'],'name':'FY27 renewal'})
  self.assertEqual(projects.list_projects()[0]['name'],'FY27 renewal')
  with self.assertRaises(ValueError):tasks.add_task('my','Invalid',project_id='missing')
  with self.assertRaises(ValueError):projects.save({'name':'FY27 renewal'})
 def test_profiles_restore_and_activity_do_not_include_prompts(self):
  ai_profiles.save({'id':'writer','instructions':'Use short sentences.','examples':'Hello.'})
  self.assertIn('Use short sentences.',ai_profiles.guidance('writer'))
  ai_profiles.save({'id':'writer','reset':True})
  self.assertNotIn('Use short sentences.',ai_profiles.guidance('writer'))
  key=ai_profiles.begin('tasks');ai_profiles.finish(key,True)
  row=next(r for r in ai_profiles.activity() if r['id']==key)
  self.assertEqual(row['state'],'finished');self.assertNotIn('prompt',row)
  with self.assertRaises(ValueError):ai_profiles.save({'id':'unknown'})
