import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from outlook_plugin import call_prompts as c

class CallPromptTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.now=1000;self.config={};self.recording=False
        patches=[patch.object(c,'FILE',Path(temp.name)/'reminders.json'),patch.object(c,'_INSTANCE','test'),patch.object(c,'_LAST_HEARTBEAT',0),patch.object(c,'_ERROR',''),patch.object(c.time,'time',side_effect=lambda:self.now),patch.object(c,'read_config',side_effect=lambda:self.config),patch.object(c,'update_config',side_effect=lambda values:self.config.update(values)),patch.object(c,'supported',return_value=True),patch.object(c.recorder,'snapshot',side_effect=lambda:{'active':self.recording}),patch.object(c.projects,'list_projects',return_value=[{'id':'p','name':'Project'}])]
        for p in patches:p.start();self.addCleanup(p.stop)
    def observe(self,apps=['teams'],**kw):return c.command(dict(action='observe',instance='test',apps=apps,**kw))
    def candidate(self):self.observe();self.now+=10;return self.observe()['candidate']
    def test_debounce_and_project_choice(self):
        self.assertIsNone(self.observe()['candidate']);self.now+=5;self.assertIsNone(self.observe()['candidate']);self.now+=5
        result=self.observe();self.assertEqual(result['candidate']['name'],'Microsoft Teams');self.assertEqual(result['projects'][0]['id'],'p')
    def test_once_per_session_survives_reads_and_short_mute(self):
        candidate=self.candidate();c.command({'action':'shown','id':candidate['id']})
        self.now+=30;self.observe([]);self.now+=30
        self.assertIsNone(self.observe()['candidate'])
        self.assertTrue(c.snapshot()['running'])
    def test_new_session_after_inactivity(self):
        candidate=self.candidate();c.command({'action':'shown','id':candidate['id']});self.now+=91
        self.assertIsNone(self.observe()['candidate']);self.now+=10
        self.assertNotEqual(self.observe()['candidate']['id'],candidate['id'])
    def test_disabled_and_recording_never_offer_or_start_capture(self):
        with patch.object(c.recorder,'start') as start:
            c.command({'action':'settings','enabled':False});self.candidate();self.assertIsNone(self.observe()['candidate'])
            c.command({'action':'settings','enabled':True});self.recording=True;self.assertIsNone(self.observe()['candidate']);self.recording=False
            self.assertIsNone(self.observe()['candidate']);start.assert_not_called()
    def test_stale_helper_and_unrecognized_apps_rejected(self):
        with self.assertRaises(ValueError):c.command({'action':'observe','instance':'old','apps':['teams']})
        with self.assertRaises(ValueError):self.observe(['recorder'])
        with self.assertRaises(ValueError):c.command({'action':'settings','enabled':'yes'})
    def test_error_is_visible_without_resetting_dismissal(self):
        candidate=self.candidate();c.command({'action':'dismiss','id':candidate['id']});self.observe(error=True)
        self.assertTrue(c.snapshot()['error']);self.assertIsNone(self.observe()['candidate']);self.assertFalse(c.snapshot()['error'])
    def test_all_active_app_sessions_are_updated(self):
        self.observe(['chrome','teams']);self.now+=10;self.observe(['chrome','teams'])
        from outlook_plugin.storage import read_json
        self.assertEqual({v['last_seen'] for v in read_json(c.FILE,{})['sessions'].values()},{self.now})
    def test_browser_detection_is_not_claimed_as_google_meet(self):
        self.observe(['chrome']);self.now+=10
        self.assertEqual(self.observe(['chrome'])['candidate']['name'],'Google Chrome')

    def test_brief_mic_checks_do_not_accumulate_into_a_prompt(self):
        self.observe();self.now+=5;self.observe([]);self.now+=5
        self.assertIsNone(self.observe()['candidate']);self.now+=5
        self.assertIsNone(self.observe()['candidate']);self.now+=5
        self.assertIsNotNone(self.observe()['candidate'])
