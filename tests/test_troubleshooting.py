import json,unittest
from unittest.mock import Mock,patch
from outlook_plugin import troubleshooting as t
from outlook_plugin.local_store import LocalStoreBridge

class TroubleshootingTests(unittest.TestCase):
 def setUp(self):
  self.engine=Mock();self.ai=Mock();self.backend=Mock(spec=LocalStoreBridge)
  self.engine.get_active_backend.return_value=self.backend
  p=patch.object(t.outlook_status,'running',return_value=True);p.start();self.addCleanup(p.stop)
 def test_recovery_refreshes_and_skips_bob(self):
  self.engine.get_email_details.return_value={'body':'Private content'}
  result=t.run(self.engine,self.ai,{'message_id':'1'})
  self.backend._load.assert_called_once_with(force=True)
  self.ai._call_llm.assert_not_called();self.assertTrue(result['resolved'])
  self.assertNotIn('Private content',json.dumps(result))
 def test_missing_message_gets_advice_not_false_success(self):
  self.engine.get_email_details.return_value=None
  self.ai._call_llm.return_value='Open Outlook and retry. If still missing, contact Brett.'
  result=t.run(self.engine,self.ai,{'message_id':'private-id','issue':'Message not found'})
  self.assertFalse(result['resolved']);self.assertIn('contact Brett',result['message'])
  prompt=self.ai._call_llm.call_args.args[0]
  self.assertNotIn('private-id',prompt);self.assertIn('not in visible cache',prompt)
 def test_raw_helper_errors_never_leave_process(self):
  self.backend._load.side_effect=RuntimeError('secret mailbox path and credential')
  self.ai._call_llm.return_value='Check Outlook.'
  result=t.run(self.engine,self.ai,{'issue':'Cannot read mail'})
  self.assertNotIn('secret',json.dumps(result));self.assertNotIn('secret',self.ai._call_llm.call_args.args[0])
 def test_bob_failure_offers_contact_without_raw_error(self):
  self.ai._call_llm.side_effect=RuntimeError('sensitive error')
  result=t.run(self.engine,self.ai,{})
  self.assertFalse(result['resolved']);self.assertIn('contact Brett',result['message']);self.assertNotIn('sensitive',result['message'])
 def test_bad_input_has_no_side_effect(self):
  for data in [{'issue':'x'*2001},{'message_id':[]},{'issue':{}}]:
   with self.assertRaises(ValueError):t.run(self.engine,self.ai,data)
  self.backend._load.assert_not_called();self.ai._call_llm.assert_not_called()
