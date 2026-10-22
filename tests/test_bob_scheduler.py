import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from unittest.mock import patch
from outlook_plugin.bob_scheduler import Scheduler,machine_capacity

class SchedulerTests(unittest.TestCase):
    def test_reserved_capacity_and_total_limit(self):
        s=Scheduler(4,load=lambda:False)
        with ExitStack() as stack:
            for _ in range(2):stack.enter_context(s.slot('workspace_search'))
            with self.assertRaises(RuntimeError):
                with s.slot('tasks',timeout=0):pass
            for _ in range(2):stack.enter_context(s.slot('project_search'))
            self.assertEqual(s.snapshot()['running'],4)
            with self.assertRaises(RuntimeError):
                with s.slot('assistant',timeout=0):pass
        self.assertEqual(s.snapshot()['running'],0);self.assertEqual(s.snapshot()['queued'],0)
    def test_search_overtakes_queued_scan(self):
        s=Scheduler(2,load=lambda:False);order=[];release=threading.Event()
        def use(profile):
            with s.slot(profile,timeout=3):order.append(profile);release.wait(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            with s.slot('assistant'),s.slot('assistant'):
                scan=pool.submit(use,'tasks')
                with s.condition:self.assertTrue(s.condition.wait_for(lambda:len(s.waiting)==1,timeout=2))
                search=pool.submit(use,'project_search')
                with s.condition:self.assertTrue(s.condition.wait_for(lambda:len(s.waiting)==2,timeout=2))
            release.set();scan.result(3);search.result(3)
        self.assertEqual(order[0],'project_search')
    def test_load_holds_background_but_allows_interactive(self):
        s=Scheduler(4,load=lambda:True)
        with s.slot('assistant'):
            with self.assertRaises(RuntimeError):
                with s.slot('workspace_search',timeout=0):pass
            with s.slot('project_search',timeout=0):self.assertEqual(s.snapshot()['running'],2)
    def test_maintenance_is_exclusive_and_exception_releases(self):
        s=Scheduler(3,load=lambda:False)
        with self.assertRaises(ValueError):
            with s.slot('assistant'):
                self.assertFalse(s.begin_maintenance());raise ValueError('test')
        self.assertTrue(s.begin_maintenance())
        with self.assertRaises(RuntimeError):
            with s.slot('assistant',timeout=0):pass
        s.end_maintenance()
        with s.slot('assistant',timeout=0):self.assertEqual(s.snapshot()['running'],1)
    def test_small_mac_gets_lower_limit(self):
        with patch('outlook_plugin.bob_scheduler.os.cpu_count',return_value=8),patch('outlook_plugin.bob_scheduler.subprocess.check_output',return_value=str(8*1024**3)):
            self.assertEqual(machine_capacity(),3)
        with patch('outlook_plugin.bob_scheduler.os.cpu_count',return_value=16),patch('outlook_plugin.bob_scheduler.subprocess.check_output',return_value=str(32*1024**3)):
            self.assertEqual(machine_capacity(),8)
