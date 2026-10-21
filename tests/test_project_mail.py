import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import projects,config,tasks,project_mail as mail,mcp_server
from outlook_plugin.mail_filters import visible_messages
class Engine:
 def __init__(self):self.rows=[dict(id=str(i),subject='Email '+str(i),sender='Pat <pat@example.com>',received_time=f'2026-10-{i%20+1:02}T12:00:00Z',body='renewal details') for i in range(55)]
 def get_active_backend(self):return self
 def get_emails(self,**kwargs):return self.rows
 def get_email_details(self,id):return next((r for r in visible_messages(self.rows) if r['id']==id),None)
class ProjectMailTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  for obj,key,name in [(config,'CONFIG_PATH','config'),(tasks,'TASKS_FILE','tasks')]:
   p=patch.object(obj,key,Path(tmp.name)/name);p.start();self.addCleanup(p.stop)
  self.p=projects.save({'name':'Renewal'})[0];self.engine=Engine()
 def task(self,email='1'):
  return tasks.add_task('my','Review '+email,project_id=self.p['id'],source={'email_id':email})['my_tasks'][-1]
 def test_task_and_direct_union_survives_edits_and_completed_tasks(self):
  task=self.task();tasks.toggle_task(task['id'])
  mail.link(self.engine,self.p['id'],'1');mail.link(self.engine,self.p['id'],'2');mail.link(self.engine,self.p['id'],'2')
  projects.save({'id':self.p['id'],'name':'Renamed'})
  rows=mail.listing(self.engine,self.p['id'])['items'];self.assertEqual(len(rows),2)
  one=next(r for r in rows if r['id']=='1');self.assertEqual(one['task_ids'],[task['id']]);self.assertTrue(one['direct'])
  mail.link(self.engine,self.p['id'],'1',True)
  one=next(r for r in mail.listing(self.engine,self.p['id'])['items'] if r['id']=='1');self.assertFalse(one['direct']);self.assertTrue(one['task_ids'])
  mail.link(self.engine,self.p['id'],'2',True);self.assertEqual(mail.listing(self.engine,self.p['id'])['total'],1)
  self.assertEqual(len(self.engine.rows),55)
 def test_pagination_search_and_project_isolation(self):
  for i in range(55):mail.link(self.engine,self.p['id'],str(i))
  a=mail.listing(self.engine,self.p['id'],offset=0);b=mail.listing(self.engine,self.p['id'],offset=25);c=mail.listing(self.engine,self.p['id'],offset=50)
  self.assertEqual([len(x['items']) for x in (a,b,c)],[25,25,5]);self.assertEqual(len({r['id'] for x in (a,b,c) for r in x['items']}),55)
  self.assertEqual(mail.listing(self.engine,self.p['id'],query='renewal')['total'],55)
  other=projects.save({'name':'Other'})[-1];self.assertEqual(mail.listing(self.engine,other['id'])['total'],0)
 def test_unavailable_and_excluded_never_leak_content(self):
  mail.link(self.engine,self.p['id'],'1');self.engine.rows=[]
  row=mail.listing(self.engine,self.p['id'])['items'][0];self.assertFalse(row['available']);self.assertEqual(row['subject'],'Email unavailable')
  self.engine=Engine();config.update_config({'excluded_domains':['example.com']})
  row=mail.listing(self.engine,self.p['id'])['items'][0];self.assertFalse(row['available']);self.assertEqual(row['sender'],'')
  self.assertEqual(mail.listing(self.engine,self.p['id'],discover=True)['items'],[])
  with self.assertRaises(ValueError):mail.link(self.engine,self.p['id'],'2')
  mail.link(self.engine,self.p['id'],'1',True)
 def test_mcp_link_and_listing(self):
  mcp_server.handle_tool_call(self.engine,'link_project_email',{'project_id':self.p['id'],'email_id':'2'})
  result=mcp_server.handle_tool_call(self.engine,'list_project_emails',{'project_id':self.p['id']})
  self.assertEqual(result['items'][0]['id'],'2')
  with self.assertRaises(ValueError):mail.link(self.engine,'missing','2')
