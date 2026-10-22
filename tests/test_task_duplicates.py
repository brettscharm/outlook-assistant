import unittest
from outlook_plugin.task_workflow import same_action
class DuplicateTests(unittest.TestCase):
 def row(self,**kwargs):
  return dict(dict(email_id='one',email_subject='Action required: Cloud account invitation',text='Accept cloud invite for account example-320',evidence='You have been invited to join the following cloud account: example-320',due_date='2026-11-16',type='my'),**kwargs)
 def test_new_message_same_request(self):
  a=self.row();b=self.row(email_id='two',text='Join cloud account example-320')
  self.assertTrue(same_action(a,b))
  self.assertTrue(same_action(a,self.row(email_id='three',evidence='Join now.')))
 def test_new_deadline_owner_or_account_not_hidden(self):
  a=self.row()
  for b in [self.row(email_id='two',due_date='2026-12-16'),self.row(email_id='two',type='others',owner='Jane'),self.row(email_id='two',text='Accept cloud invite for account different-999',evidence='Join a different account'),self.row(email_id='two',due_date='')]:self.assertFalse(same_action(a,b))
 def test_generic_recurring_requests_remain(self):
  a=self.row(text='Send report',evidence='Send report')
  self.assertFalse(same_action(a,dict(a,email_id='two')))
 def test_reply_prefixes_and_punctuation(self):
  self.assertTrue(same_action(self.row(),self.row(email_id='two',email_subject='Re: Fwd: Action required: Cloud account invitation',text='Accept cloud invite for account example-320!')))
 def test_saved_hints_do_not_modify_originals(self):
  from outlook_plugin.task_duplicates import annotate
  a=self.row(id='a');b=self.row(id='b',email_id='two');c=self.row(id='c',email_id='three',completed=True)
  data={'my_tasks':[a,b,c],'others_tasks':[]};result=annotate(data)
  self.assertEqual(result['my_tasks'][0]['possible_duplicates'],['b'])
  self.assertNotIn('possible_duplicates',a);self.assertNotIn('possible_duplicates',result['my_tasks'][2])
