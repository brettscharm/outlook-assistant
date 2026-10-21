import threading,unittest
from unittest.mock import Mock
from outlook_plugin.agent_team import draft
from outlook_plugin.ai_agent import _BOB_LOCK
class TeamTests(unittest.TestCase):
 def test_two_specialists_then_editor_under_one_lease(self):
  barrier=threading.Barrier(2);calls=[]
  class AI:
   def _call_llm(self,prompt,profile,**kw):
    self_check=kw['_coordinated'];calls.append(profile)
    if profile!='editor':barrier.wait(timeout=2)
    return '<p>Verified draft</p>' if profile=='editor' else profile
  self.assertEqual(draft(AI(),'Synthetic prompt',{'body':'Synthetic fact'},'Reply'),'<p>Verified draft</p>')
  self.assertEqual(set(calls[:2]),{'writer','reviewer'});self.assertEqual(calls[-1],'editor');self.assertFalse(_BOB_LOCK.locked())
 def test_failure_releases_lease_and_does_not_run_editor(self):
  ai=Mock();ai._call_llm.side_effect=RuntimeError('Synthetic failure')
  with self.assertRaises(RuntimeError):draft(ai,'Synthetic',{},'Reply')
  self.assertFalse(_BOB_LOCK.locked());self.assertNotIn('editor',[call.kwargs['profile'] for call in ai._call_llm.call_args_list])
