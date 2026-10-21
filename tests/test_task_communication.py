import unittest
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
from outlook_plugin import task_communication as c
class CommunicationTests(unittest.TestCase):
 def test_draft_encodes_content_and_never_sends(self):
  data={'recipients':['pat@example.com'],'subject':'Task & next step','body':'Please review\nhttps://example.com/?a=1&b=2'}
  with patch.object(c.subprocess,'run') as run:
   self.assertEqual(c.open_draft(data),{'opened':True})
   args=run.call_args.args[0]
   self.assertEqual(args[0],'/usr/bin/open')
   self.assertEqual(parse_qs(urlparse(args[1]).query)['body'],[data['body']])
 def test_bad_recipient_rejected(self):
  for recipients in [[],['pat@example.com\nbcc:someone@example.com'],'pat@example.com']:
   with self.assertRaises(ValueError):c.draft_url({'recipients':recipients})
