import unittest
from unittest.mock import Mock,patch
from outlook_plugin import reply_writing as w
from outlook_plugin.ai_agent import BobAIAgent

class ReplyWritingTests(unittest.TestCase):
 def test_polish_preserves_user_draft_and_tone_in_request(self):
  ai=Mock();ai._call_llm.return_value='<p>Polished</p>'
  result=w.polish(ai,{'body':'Source email'},{'draft':'I can send 3 samples on Friday.','html':'<p>I can send <b>3</b> samples on Friday.</p>','tone':'firm'})
  self.assertEqual(result,'<p>Polished</p>');prompt=ai._call_llm.call_args.args[0]
  self.assertIn('3 samples on Friday',prompt);self.assertIn('Requested tone: firm',prompt);self.assertIn('Preserve the draft',prompt);self.assertIn('Do not invent',prompt)
  self.assertEqual(ai._call_llm.call_args.kwargs['profile'],'writer')
 def test_validation_prevents_invalid_or_empty_requests(self):
  for data in [{'draft':''},{'draft':'Hi','tone':'rude'},{'draft':'x'*50001},{'draft':'Hi','html':[]},{'draft':'Hi','intent':False}]:
   ai=Mock()
   with self.assertRaises(ValueError):w.polish(ai,{},data)
   ai._call_llm.assert_not_called()
 def test_generate_passes_tone_through_all_drafting_stages(self):
  with patch('outlook_plugin.agent_team.draft',return_value='ok') as draft:
   self.assertEqual(BobAIAgent('synthetic').draft_smart_reply({'body':'Hello'},[],intent='Reply briefly',tone='casual'),'ok')
   self.assertIn('Requested tone: casual',draft.call_args.args[1]);self.assertIn('Requested tone: casual',draft.call_args.args[3])
 def test_default_friendly_and_missing_source_supported(self):
  ai=Mock();w.polish(ai,{}, {'draft':'My own draft'})
  self.assertIn('Requested tone: friendly',ai._call_llm.call_args.args[0])
