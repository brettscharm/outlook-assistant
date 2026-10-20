import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from outlook_plugin import config,bob_status
from outlook_plugin.ai_agent import BobAIAgent
class BobStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        p=patch.object(config,'CONFIG_PATH',Path(self.tmp.name)/'config.json');p.start();self.addCleanup(p.stop)
        env=patch.dict('os.environ',{'BOB_TEAM_ID':''});env.start();self.addCleanup(env.stop)
    def test_distinguishes_auth_permission_quota_network_and_unknown(self):
        for error,expected in [('API key has been revoked','revoked'),('token expired','expired'),('HTTP 401 unauthorized','invalid'),('HTTP 403 forbidden','permission'),('budget exceeded','quota'),('HTTP 429','rate_limit'),('fetch failed','network'),('unrecognized error','error')]:
            self.assertEqual(bob_status.classify(error),expected)
    def test_new_key_and_team_do_not_inherit_old_status(self):
        bob_status.remember('old-secret',None,'revoked')
        self.assertEqual(bob_status.current('old-secret')['state'],'revoked')
        self.assertEqual(bob_status.current('new-secret')['state'],'unchecked')
        self.assertNotIn('old-secret',config.CONFIG_PATH.read_text())
        self.assertNotIn('credential',bob_status.current('old-secret'))
        config.update_config({'bob_team_id':'different'})
        self.assertEqual(bob_status.current('old-secret')['state'],'unchecked')
    @patch('outlook_plugin.ai_agent.usage.record')
    @patch('outlook_plugin.ai_agent.node_executable',return_value='/tmp/node')
    @patch('outlook_plugin.ai_agent.bob_executable',return_value='/tmp/bob')
    @patch('outlook_plugin.ai_agent.subprocess.run')
    def test_failed_call_records_safe_status_and_success_recovers(self,run,*unused):
        run.return_value=Mock(returncode=1,stdout=json.dumps({'status':'error','error':{'message':'API key revoked secret-value private-message'}}),stderr='')
        agent=BobAIAgent('secret-value')
        with self.assertRaisesRegex(RuntimeError,'revoked') as caught:agent._call_llm('private-message')
        self.assertNotIn('secret-value',str(caught.exception));self.assertNotIn('private-message',config.CONFIG_PATH.read_text())
        self.assertEqual(bob_status.current('secret-value')['state'],'revoked')
        run.return_value=Mock(returncode=0,stdout=json.dumps({'status':'success','last_message':'OK','stats':{}}),stderr='')
        self.assertEqual(agent._call_llm('synthetic'),'OK')
        self.assertEqual(bob_status.current('secret-value')['state'],'connected')
