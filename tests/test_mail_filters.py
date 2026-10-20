import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import config,task_workflow
from outlook_plugin.mail_filters import normalize_domains
from outlook_plugin.local_store import LocalStoreBridge
from outlook_plugin.engine import OutlookEngine

class FiltersTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  p=patch.object(config,'CONFIG_PATH',Path(self.tmp.name)/'config');p.start();self.addCleanup(p.stop)
  self.rows=[dict(id=str(i),sender='Person <x@'+domain+'>',subject='Test',body='Full content',preview='Preview',folder_id=folder,folder=folder,folder_kind=folder,read='unread',received_time='2026-10-20T12:00:00Z',body_complete=True) for i,(domain,folder) in enumerate([('example.com','inbox'),('news.example.com','sent'),('notexample.com','archive'),('other.org','trash')])]
  self.bridge=LocalStoreBridge()
  p=patch.object(self.bridge,'_load',return_value={'rows':self.rows,'store_updated':1,'checked':1,'profile':'synthetic','partial':False});p.start();self.addCleanup(p.stop)
 def test_normalization_and_invalid_rules(self):
  self.assertEqual(normalize_domains('@Example.COM, example.com\nnews.org'),['example.com','news.org'])
  for bad in ['https://example.com','name@example.com','*.com','-bad.com']:
   with self.assertRaises(ValueError):normalize_domains(bad)
 def test_all_folders_and_no_limit(self):
  self.assertEqual(len(self.bridge.get_emails(folder='all',limit=None)),4)
 def test_filter_before_pagination_and_direct_access(self):
  config.update_config({'excluded_domains':['example.com']})
  self.assertEqual([m['id'] for m in self.bridge.get_emails(limit=1)],['2'])
  self.assertEqual([m['id'] for m in self.bridge.get_emails(limit=1,offset=1)],['3'])
  self.assertIsNone(self.bridge.get_email_details('0'))
  self.assertEqual(self.bridge.status()['excluded_count'],2)
  self.assertEqual(len(self.bridge.list_folders()),2)
  config.update_config({'excluded_domains':[]})
  self.assertIsNotNone(self.bridge.get_email_details('0'))
 def test_task_candidates_exclude_blocked_sender(self):
  config.update_config({'excluded_domains':['example.com']})
  engine=OutlookEngine();engine.local_store=self.bridge;engine.local_only=True
  rows=task_workflow.candidate_messages(engine,{'since':'2026-10-01'})
  self.assertEqual({m['id'] for m in rows},{'2','3'})
