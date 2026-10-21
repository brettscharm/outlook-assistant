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

 def test_multiple_opportunity_links_persist_and_validate(self):
  links=[{'kind':'isc','label':'Opportunity 123','url':'https://example.ibm.com/opportunity/123'},{'kind':'gainsight','label':'Renewal','url':'https://example.gainsightcloud.com/renewal/456'}]
  p=projects.save({'name':'Customer renewal','links':links})[0]
  projects.save({'id':p['id'],'name':'Updated renewal'})
  self.assertEqual(projects.list_projects()[0]['links'],links)
  for url in ('javascript:alert(1)','https://user:password@example.com','http://example.com'):
   with self.assertRaises(ValueError):projects.save({'id':p['id'],'name':'Updated renewal','links':[dict(links[0],url=url)]})
  self.assertEqual(projects.list_projects()[0]['links'],links)
  projects.save({'id':p['id'],'name':'Updated renewal','links':[]})
  self.assertEqual(projects.list_projects()[0]['links'],[])

 def test_project_meetings_persist_and_validate(self):
  meeting={'id':'meeting1','title':'Discovery','occurred_at':'2026-10-20T10:00:00-04:00','notes':'Next steps','recording_url':'https://example.sharepoint.com/recording'}
  p=projects.save({'name':'Customer meetings','meetings':[meeting]})[0]
  projects.save({'id':p['id'],'name':'Customer meetings','description':'Updated'})
  self.assertEqual(projects.list_projects()[0]['meetings'][0]['recording_url'],meeting['recording_url'])
  for bad in [dict(meeting,title=''),dict(meeting,recording_url='javascript:alert(1)'),dict(meeting,occurred_at='2026-10-20T10:00')]:
   with self.assertRaises(ValueError):projects.save({'id':p['id'],'name':p['name'],'meetings':[bad]})
  self.assertEqual(len(projects.list_projects()[0]['meetings']),1)
  projects.save({'id':p['id'],'name':p['name'],'meetings':[]})
  self.assertEqual(projects.list_projects()[0]['meetings'],[])

 def test_any_hex_project_color_persists_without_losing_legacy_colors(self):
  for color in ('#008080','#FF0044','#ffffff','#000000','purple'):
   existing=projects.list_projects()
   p=projects.save({'id':existing[0]['id'] if existing else None,'name':'Colors','color':color})[0]
   self.assertEqual(p['color'],color)
   projects.save({'id':p['id'],'name':'Colors','description':'Updated'})
   self.assertEqual(projects.list_projects()[0]['color'],color)
  for color in ('red','url(evil)','#12345z','#abc',{},None):
   with self.assertRaises(ValueError):projects.save({'id':p['id'],'name':'Colors','color':color})
