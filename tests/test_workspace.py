import json
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from outlook_plugin import workspace, config, tasks, task_workflow, email_chat

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.patches=[patch.object(module,name,self.root/file) for module,name,file in [(config,'CONFIG_PATH','config.json'),(tasks,'TASKS_FILE','tasks.json'),(task_workflow,'WORKFLOW_FILE','review.json'),(email_chat,'CHAT_FILE','chat.json'),(workspace,'LOGIN_FILE','agents/start.plist')]]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def test_backup_excludes_credentials_preserves_content(self):
        config.update_config({'bob_api_key':'secret-for-test','bob_team_id':'private-team','outlook_profile':'private-path','user_context':{'role':'Sales'}})
        tasks.save_tasks({'my_tasks':[{'id':'1','text':'Call Pat'}],'others_tasks':[]})
        data=workspace.export_data();raw=json.dumps(data)
        for value in ['secret-for-test','private-team','private-path']:self.assertNotIn(value,raw)
        self.assertEqual(data['tasks']['my_tasks'][0]['text'],'Call Pat')
    def test_style_preserves_other_context_and_key(self):
        config.update_config({'bob_api_key':'secret-for-test','user_context':{'full_name':'Pat','role':'Sales'}})
        workspace.save_style('Short and warm')
        cfg=config.read_config();self.assertEqual(cfg['user_context']['role'],'Sales');self.assertEqual(cfg['bob_api_key'],'secret-for-test');self.assertEqual(cfg['user_context']['writing_style'],'Short and warm')
    def test_startup_is_valid_plist_and_removable(self):
        with patch.object(workspace.sys,'platform','darwin'):
            self.assertTrue(workspace.set_startup(True)['enabled'])
            data=plistlib.loads(workspace.LOGIN_FILE.read_bytes());self.assertTrue(data['RunAtLoad']);self.assertIn('--no-browser',data['ProgramArguments']);self.assertNotIn('KeepAlive',data)
            self.assertEqual(workspace.LOGIN_FILE.stat().st_mode & 0o777,0o600)
            self.assertFalse(workspace.set_startup(False)['enabled'])
    def test_corrupt_task_file_is_not_overwritten(self):
        tasks.TASKS_FILE.write_text('{broken')
        with self.assertRaises(RuntimeError):tasks.load_tasks()
        self.assertEqual(tasks.TASKS_FILE.read_text(),'{broken')
    def test_learning_validates_before_using_bob(self):
        ai=Mock()
        with self.assertRaises(ValueError):workspace.learn_style(ai,'short')
        ai._call_llm.assert_not_called()
        ai._call_llm.return_value='Keep it concise.'
        self.assertEqual(workspace.learn_style(ai,'Hello Pat, thanks for the update. Please send the revised proposal when you have a moment. Best, Alex.'),{'guide':'Keep it concise.'})

    def test_frozen_startup_prefers_installed_service(self):
        service=self.root/'Applications/Outlook Assistant.app/Contents/MacOS/Outlook Assistant Service'
        service.parent.mkdir(parents=True);service.write_text('test')
        with patch.object(workspace,'INSTALLATIONS',[service.parents[2]]),patch.object(workspace.sys,'frozen',True,create=True),patch.object(workspace.sys,'platform','darwin'):
            workspace.set_startup(True)
        data=plistlib.loads(workspace.LOGIN_FILE.read_bytes())
        self.assertEqual(data['ProgramArguments'][0],str(service))
