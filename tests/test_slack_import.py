import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from datetime import date
from outlook_plugin import slack_import as s
from outlook_plugin.workspace_search import in_range

class SlackImportTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);p=patch.object(s,'FILE',Path(tmp.name)/'slack.json');p.start();self.addCleanup(p.stop)
 def payload(self,**kw):return dict(workspace='Example',channel='#team',**kw)
 def test_reimports_updates_and_workspace_identity(self):
  data=self.payload(messages=[{'ts':'1761000000.000001','text':'Send proposal','user':'U1'}])
  self.assertEqual(s.import_messages(data)['added'],1)
  self.assertEqual(s.import_messages(data)['skipped'],1)
  data['messages'][0]['text']='Send updated proposal'
  self.assertEqual(s.import_messages(data)['updated'],1)
  data['workspace']='Another';self.assertEqual(s.import_messages(data)['added'],1)
  self.assertEqual(s.listing()['total'],2)
 def test_users_resolve_old_messages_and_mentions(self):
  s.import_messages(self.payload(messages=[{'text':'Ask <@U1> about <https://example.com|proposal>','user':'U1','ts':'1761000000.123456'}]))
  s.import_messages(dict(workspace='Example',messages=[{'id':'U1','profile':{'real_name':'Alex Jones'}}]))
  row=s.documents()[0];self.assertEqual(row['sender'],'Alex Jones');self.assertIn('@Alex Jones',row['text']);self.assertIn('https://example.com',row['text'])
  self.assertTrue(in_range(row['occurred_at'],date(2025,10,1),date(2025,10,31),ZoneInfo('UTC')))
 def test_paste_stable_undated_and_reload(self):
  data=self.payload(text='A conversation',url='https://example.slack.com/archives/C1/p123')
  s.import_messages(data);s.import_messages(data);self.assertEqual(s.listing()['total'],1)
  row=s.documents()[0];self.assertEqual(row['occurred_at'],'');self.assertFalse(in_range('',date(2025,10,1),date(2025,10,31),ZoneInfo('UTC')))
  self.assertEqual(s.listing(row['id'])['total'],1)
 def test_invalid_batch_is_atomic(self):
  with self.assertRaises(ValueError):s.import_messages(self.payload(messages=[{'text':'Good','ts':'1761000000.1'},{'text':'Bad','ts':'NaN'}]))
  self.assertEqual(s.listing()['total'],0)
 def test_input_validation(self):
  for extra in [{'text':'x','url':'javascript:alert(1)'},{'text':'x','url':'https://slack.com.evil.test/'},{'messages':{}},{'text':'x'*100001},{'text':'x','messages':[{'text':'y'}]}]:
   with self.subTest(extra=list(extra)):
    with self.assertRaises(ValueError):s.import_messages(self.payload(**extra))
 def test_pagination_search(self):
  s.import_messages(self.payload(messages=[{'text':'Message '+str(i),'ts':str(1761000000+i)} for i in range(35)]))
  self.assertEqual(len(s.listing()['items']),30);self.assertEqual(len(s.listing(offset=30)['items']),5);self.assertEqual(s.listing('Message 34')['total'],1)
