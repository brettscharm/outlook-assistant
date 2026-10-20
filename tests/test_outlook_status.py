import subprocess,unittest
from unittest.mock import Mock,patch
from outlook_plugin import outlook_status as s
class OutlookStatusTests(unittest.TestCase):
 def setUp(self):
  s._CHECKED=None;s._RUNNING=None
 def tearDown(self):s._CHECKED=None;s._RUNNING=None
 def test_running_closed_and_unknown(self):
  for code,expected in [(0,True),(1,False),(2,None)]:
   s._CHECKED=None
   with patch.object(s.sys,'platform','darwin'),patch.object(s.subprocess,'run',return_value=Mock(returncode=code)) as run:
    self.assertIs(s.running(),expected);self.assertIs(s.running(),expected);self.assertEqual(run.call_count,1)
    self.assertEqual(run.call_args[0][0],['/usr/bin/pgrep','-x','Microsoft Outlook'])
 def test_timeout_is_unknown_not_closed(self):
  with patch.object(s.sys,'platform','darwin'),patch.object(s.subprocess,'run',side_effect=subprocess.TimeoutExpired('pgrep',3)):
   self.assertIsNone(s.running())
 def test_open_is_explicit_and_invalidates_cache(self):
  s._CHECKED=1
  with patch.object(s.sys,'platform','darwin'),patch.object(s.subprocess,'run',return_value=Mock(returncode=0)) as run:
   self.assertTrue(s.open_outlook()['opened']);self.assertIsNone(s._CHECKED)
   self.assertEqual(run.call_args[0][0],['/usr/bin/open','-b','com.microsoft.Outlook'])
