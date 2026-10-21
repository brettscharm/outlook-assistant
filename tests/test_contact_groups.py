import tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from outlook_plugin import config,contact_groups as g,mcp_server

class GroupTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  p=patch.object(config,'CONFIG_PATH',Path(tmp.name)/'config');p.start();self.addCleanup(p.stop)
  config.update_config({'user_context':{'role':'Engineer'},'bob_api_key':'private'})
 def group(self,**kwargs):return g.save(dict(id='group1',revision=0,domain='example.com',name='Engineering',emails=['PAT@example.com','pat@example.com','sam@example.org'],**kwargs))
 def test_persist_dedupe_edit_revision_and_delete(self):
  saved=self.group();self.assertEqual(saved['emails'],['pat@example.com','sam@example.org']);self.assertEqual(g.listing(),[saved])
  with self.assertRaises(ValueError):self.group()
  changed=g.save(dict(saved,name='Product'));self.assertEqual(changed['revision'],2)
  self.assertEqual(config.read_config()['user_context']['role'],'Engineer')
  g.save({'id':saved['id'],'revision':2,'remove':True});self.assertEqual(g.listing(),[])
 def test_invalid_inputs_do_not_write(self):
  base=dict(id='x',revision=0,domain='example.com',name='Team',emails=[])
  for change in [{'emails':['pat@example.com\nbcc:hacker@example.com']},{'emails':'pat@example.com'},{'domain':'bad'},{'name':''},{'id':'../secret'},{'revision':True}]:
   with self.assertRaises(ValueError):g.save(dict(base,**change))
  self.assertEqual(g.listing(),[])
 def test_mcp_access_uses_same_store_and_no_secrets(self):
  item=mcp_server.handle_tool_call(Mock(),'save_contact_group',{'id':'test','revision':0,'domain':'example.com','name':'Team','emails':['a@example.com']})
  self.assertEqual(mcp_server.handle_tool_call(Mock(),'list_contact_groups',{}),[item])
  self.assertNotIn('private',str(item))
