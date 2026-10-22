import tempfile,unittest,hashlib
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import mail_references as m

class MailReferenceTests(unittest.TestCase):
 def setUp(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
  p=patch.object(m,'REFERENCES_FILE',Path(temp.name)/'refs.json');p.start();self.addCleanup(p.stop)
  self.tasks=patch('outlook_plugin.tasks.load_tasks',return_value={'my_tasks':[]});self.tasks.start();self.addCleanup(self.tasks.stop)
  self.review=patch('outlook_plugin.task_workflow.load',return_value={'suggestions':{}});self.review.start();self.addCleanup(self.review.stop)
 def test_changed_id_survives_reload(self):
  m.remember('profile-a',[{'id':'old','message_id':'stable'}])
  row={'id':'new','message_id':'stable'}
  m.remember('profile-a',[row])
  self.assertEqual(m.recover('old','profile-a',[row])['id'],'new')
  self.assertIsNone(m.recover('old','profile-b',[row]))
 def test_review_stable_identity_recovers_legacy_link(self):
  key='message:'+hashlib.sha256(b'stable').hexdigest()
  with patch('outlook_plugin.task_workflow.load',return_value={'suggestions':{'s':{'email_id':'old','source_keys':[key]}}}):
   self.assertEqual(m.recover('old','p',[{'id':'new','message_id':'stable'}])['id'],'new')
 def test_same_subject_quote_does_not_open_different_reply(self):
  old={'email_id':'old','email_subject':'Same subject','evidence':'Long evidence about the request in an email thread'}
  with patch('outlook_plugin.tasks.load_tasks',return_value={'my_tasks':[old]}):
   self.assertIsNone(m.recover('old','p',[{'id':'new','subject':'Same subject','body':old['evidence'],'message_id':'different'}]))
 def test_missing_or_filtered_mail_not_recovered(self):
  m.remember('p',[{'id':'old','message_id':'stable'}])
  self.assertIsNone(m.recover('old','p',[]))
