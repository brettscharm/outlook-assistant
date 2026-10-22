import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
from outlook_plugin import ai_agent


class ChatQueueTests(unittest.TestCase):
    def setUp(self):
        for target, value in [('bob_executable', '/fake/bob'), ('node_executable', '/fake/node'),
                              ('bob_compatibility', {'ready': True}), ('read_config', {})]:
            p = patch.object(ai_agent, target, return_value=value)
            p.start(); self.addCleanup(p.stop)
        for target in ['outlook_plugin.ai_profiles.begin', 'outlook_plugin.ai_profiles.finish',
                       'outlook_plugin.ai_agent.usage.record', 'outlook_plugin.ai_agent.bob_status.remember']:
            p = patch(target); p.start(); self.addCleanup(p.stop)
        p = patch('outlook_plugin.ai_profiles.guidance', return_value='')
        p.start(); self.addCleanup(p.stop)

    def test_chat_waits_for_busy_bob_and_runs_once(self):
        lock = threading.Lock()
        lock.acquire()
        waiting = threading.Event()
        class ObservedLock:
            def acquire(self, **kwargs):
                waiting.set()
                return lock.acquire(**kwargs)
            def release(self): lock.release()
        result = Mock(returncode=0, stdout=json.dumps({'status': 'success', 'last_message': 'OK'}), stderr='')
        with patch.object(ai_agent, '_BOB_LOCK', ObservedLock()), patch.object(ai_agent.subprocess, 'run', return_value=result) as run:
            with ThreadPoolExecutor(max_workers=1) as pool:
                response = pool.submit(ai_agent.BobAIAgent('synthetic')._call_llm, 'Synthetic question')
                try:
                    self.assertTrue(waiting.wait(2))
                    self.assertFalse(response.done())
                    run.assert_not_called()
                finally:
                    lock.release()
                self.assertEqual(response.result(timeout=2), 'OK')
                run.assert_called_once()
            self.assertFalse(lock.locked())

    def test_wait_timeout_does_not_launch_bob(self):
        with patch.object(ai_agent, '_BOB_LOCK') as lock, patch.object(ai_agent.subprocess, 'run') as run:
            lock.acquire.return_value = False
            with self.assertRaisesRegex(RuntimeError, 'message is saved'):
                ai_agent.BobAIAgent('synthetic')._call_llm('Synthetic question')
            lock.acquire.assert_called_once_with(timeout=180)
            lock.release.assert_not_called()
            run.assert_not_called()

    def test_troubleshooting_omits_saved_context(self):
        result=Mock(returncode=0,stdout=json.dumps({'status':'success','last_message':'Check Outlook.'}),stderr='')
        with patch.object(ai_agent,'read_config',return_value={'user_context':{'role':'PRIVATE-ROLE'},'domain_companies':{'private.example':'PRIVATE-COMPANY'}}), patch.object(ai_agent.subprocess,'run',return_value=result) as run:
            ai_agent.BobAIAgent('synthetic')._call_llm('Diagnostic checks only',profile='troubleshooting')
            prompt=run.call_args.kwargs['input']
            self.assertNotIn('PRIVATE-',prompt)
            self.assertIn('--disable-tool-groups',run.call_args.args[0])

    def test_project_search_runs_while_scan_lock_held(self):
        lock=threading.Lock();lock.acquire()
        result=Mock(returncode=0,stdout=json.dumps({'status':'success','last_message':'Search answer','stats':{'session_costs':1}}),stderr='')
        with patch.object(ai_agent,'_BOB_LOCK',lock),patch.object(ai_agent.subprocess,'run',return_value=result) as run:
            self.assertEqual(ai_agent.BobAIAgent('synthetic')._call_llm('Question',profile='project_search'),'Search answer')
            self.assertTrue(lock.locked());self.assertFalse(ai_agent._BOB_SEARCH_LOCK.locked())
            self.assertIn('--workspace',run.call_args.args[0]);ai_agent.usage.record.assert_called_once()
        lock.release()

    def test_search_failure_releases_only_its_slot(self):
        lock=threading.Lock();lock.acquire()
        with patch.object(ai_agent,'_BOB_LOCK',lock),patch.object(ai_agent.subprocess,'run',side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):ai_agent.BobAIAgent('synthetic')._call_llm('Question',profile='project_search')
            self.assertFalse(ai_agent._BOB_SEARCH_LOCK.locked());self.assertTrue(lock.locked())
        lock.release()

    def test_second_search_does_not_launch_another_shell(self):
        with patch.object(ai_agent,'_BOB_SEARCH_LOCK') as lock,patch.object(ai_agent.subprocess,'run') as run:
            lock.acquire.return_value=False
            with self.assertRaisesRegex(RuntimeError,'project search'):ai_agent.BobAIAgent('synthetic')._call_llm('Question',profile='project_search')
            run.assert_not_called();lock.release.assert_not_called()

    def test_scan_and_search_overlap_in_separate_workspaces(self):
        barrier=threading.Barrier(2);workspaces=[];prompts=[]
        def run(command,**kwargs):
            workspaces.append(kwargs['cwd']);prompts.append(kwargs['input'])
            barrier.wait(timeout=3)
            return Mock(returncode=0,stdout=json.dumps({'status':'success','last_message':'OK'}),stderr='')
        with patch.object(ai_agent.subprocess,'run',side_effect=run):
            with ThreadPoolExecutor(max_workers=2) as pool:
                scan=pool.submit(ai_agent.BobAIAgent('synthetic')._call_llm,'SCAN_ONLY',profile='tasks')
                search=pool.submit(ai_agent.BobAIAgent('synthetic')._call_llm,'SEARCH_ONLY',profile='project_search')
                self.assertEqual(scan.result(timeout=5),'OK');self.assertEqual(search.result(timeout=5),'OK')
        self.assertEqual(len(set(workspaces)),2)
        self.assertEqual(sum('SCAN_ONLY' in p for p in prompts),1)
        self.assertEqual(sum('SEARCH_ONLY' in p for p in prompts),1)
        self.assertFalse(ai_agent._BOB_LOCK.locked());self.assertFalse(ai_agent._BOB_SEARCH_LOCK.locked())
