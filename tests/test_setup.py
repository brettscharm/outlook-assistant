import unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import setup_check
from outlook_plugin.engine import OutlookEngine
class SetupTests(unittest.TestCase):
    def test_clean_mac_has_actionable_missing_requirements(self):
        with patch.object(setup_check.platform,'system',return_value='Darwin'),patch.object(setup_check.platform,'mac_ver',return_value=('15.0','','')),patch.object(setup_check.platform,'machine',return_value='arm64'),patch.object(setup_check.local_store,'profiles',return_value=[]),patch.object(setup_check,'read_config',return_value={}),patch.object(setup_check,'get_bob_api_key',return_value=''),patch.object(setup_check,'bob_executable',return_value=None):
            result=setup_check.check();rows={r['id']:r for r in result['checks']}
            self.assertFalse(result['ready']);self.assertTrue(rows['mac']['ready']);self.assertFalse(rows['outlook']['ready']);self.assertFalse(rows['bob']['ready']);self.assertFalse(rows['key']['ready'])
    def test_multiple_profiles_require_selection(self):
        with patch.object(setup_check.local_store,'profiles',return_value=[Path('/one'),Path('/two')]),patch.object(setup_check,'read_config',return_value={}):
            rows={r['id']:r for r in setup_check.check()['checks']};self.assertFalse(rows['outlook']['ready'])
    def test_gui_local_mode_never_probes_applescript(self):
        engine=OutlookEngine();engine.local_only=True
        with patch.object(engine.mac_bridge,'is_available',side_effect=AssertionError('Must not probe legacy Outlook')):
            self.assertIs(engine.get_active_backend(),engine.local_store)

    def test_node_runtime_requires_version_24(self):
        from outlook_plugin import ai_agent
        from unittest.mock import Mock
        with patch.object(ai_agent,'executable_directories',return_value=[]),patch.object(ai_agent.shutil,'which',return_value='/fake/node'),patch.object(ai_agent.os.path,'isfile',return_value=True),patch.object(ai_agent.os,'access',return_value=True),patch.object(ai_agent.subprocess,'run',return_value=Mock(returncode=0,stdout='v22.0.0')) as run:
            self.assertIsNone(ai_agent.node_executable())
            run.return_value=Mock(returncode=0,stdout='v24.1.0')
            self.assertEqual(ai_agent.node_executable(),'/fake/node')

    def test_bob_versions_are_checked_without_credentials(self):
        from outlook_plugin import ai_agent as a
        from unittest.mock import Mock
        import subprocess
        with patch.dict(a.os.environ,{'BOB_API_KEY':'private-test-key'}), patch.object(a.subprocess,'run') as run:
            for output, ready in [('2.0.2',True),('Bob Shell v2.1.0',True),('1.9.0',False),('3.0.0',False),('unrecognized output',False)]:
                run.return_value=Mock(returncode=0,stdout=output)
                self.assertEqual(a.bob_compatibility('/fake/bob','/fake/node')['ready'],ready)
                self.assertNotIn('BOB_API_KEY',run.call_args.kwargs['env'])
                self.assertEqual(run.call_args.args[0],['/fake/bob','--version'])
            run.side_effect=subprocess.TimeoutExpired('bob',8)
            self.assertFalse(a.bob_compatibility('/fake/bob','/fake/node')['ready'])

    def test_incompatible_bob_never_sends_prompt(self):
        from outlook_plugin import ai_agent as a
        with patch.object(a,'bob_executable',return_value='/fake/bob'),patch.object(a,'node_executable',return_value='/fake/node'),patch.object(a,'bob_compatibility',return_value={'ready':False,'detail':'Unsupported Bob version'}),patch.object(a.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'Unsupported Bob'):
                a.BobAIAgent('test-key')._call_llm('private message')
            run.assert_not_called()
