import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import config, onboarding, bob_status

class WalkthroughTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(config, 'CONFIG_PATH', Path(self.tmp.name) / 'config.json')
        p.start(); self.addCleanup(p.stop)

    def test_progress_survives_reload_and_preserves_settings(self):
        config.update_config({'bob_api_key':'private', 'user_context':{'role':'Sales'}})
        self.assertEqual(onboarding.current(), {'step':0,'dismissed':False,'completed':False})
        onboarding.save({'step':3,'dismissed':True})
        self.assertEqual(onboarding.current()['step'],3)
        self.assertTrue(onboarding.current()['dismissed'])
        onboarding.save({'step':5,'completed':True})
        self.assertTrue(onboarding.current()['completed'])
        self.assertEqual(config.read_config()['user_context'],{'role':'Sales'})
        self.assertNotIn('private',str(onboarding.current()))

    def test_invalid_progress_does_not_write(self):
        for data in ({'step':-1},{'step':6},{'step':True},{'completed':'yes'},{'bob_api_key':'bad'}):
            with self.assertRaises(ValueError): onboarding.save(data)
        self.assertFalse(config.CONFIG_PATH.exists())

    def test_quota_is_distinct_from_temporary_rate_limits(self):
        for error in ('insufficient Bobcoins','quota exhausted','HTTP 429 usage limit reached'):
            self.assertEqual(bob_status.classify(error),'quota')
        self.assertEqual(bob_status.classify('HTTP 429 rate limit'),'rate_limit')
        self.assertIn('Open Bob and request more usage',bob_status.MESSAGES['quota'][1])
