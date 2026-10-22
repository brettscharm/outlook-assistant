import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from outlook_plugin import email_summary as s
class SummaryTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);p=patch.object(s,'FILE',Path(tmp.name)/'summary.json');p.start();self.addCleanup(p.stop)
  self.engine=Mock();self.engine.get_email_details.return_value={'id':'e','body':'Alex: Please send the proposal by Friday.','body_complete':True}
  self.ai=Mock();self.ai._call_llm.return_value=json.dumps({'bullets':[{'text':'Send the proposal by Friday.','quote':'Please send the proposal by Friday.'}]})
 def test_cache_and_changed_body(self):
  first=s.summarize(self.engine,{'email_id':'e'},self.ai);self.assertFalse(first['partial']);self.assertEqual(s.summarize(self.engine,{'email_id':'e'},self.ai),first);self.ai._call_llm.assert_called_once()
  self.engine.get_email_details.return_value['body']+=' New detail.';s.summarize(self.engine,{'email_id':'e'},self.ai);self.assertEqual(self.ai._call_llm.call_count,2)
 def test_fabrication_rejected(self):
  self.ai._call_llm.return_value='{"bullets":[{"text":"False","quote":"invented"}]}'
  with self.assertRaises(ValueError):s.summarize(self.engine,{'email_id':'e'},self.ai)
 def test_exclusion_checked_before_cache(self):
  s.summarize(self.engine,{'email_id':'e'},self.ai)
  with patch.object(s,'visible_messages',return_value=[]):
   with self.assertRaises(ValueError):s.summarize(self.engine,{'email_id':'e'},self.ai)
 def test_preview_label(self):
  self.engine.get_email_details.return_value['body_complete']=False
  self.assertTrue(s.summarize(self.engine,{'email_id':'e'},self.ai)['partial'])
