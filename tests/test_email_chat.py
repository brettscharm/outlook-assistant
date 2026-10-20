import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import email_chat as chat

class Engine:
    def get_emails(self,**kw):return [{'id':'1'},{'id':'2'}]
    def get_email_details(self,id):return {'id':id,'subject':'Acme renewal' if id=='1' else 'Lunch','sender':'Pat','body':'Renew by November 12' if id=='1' else 'Lunch tomorrow','received_time':'2026-10-20'}
class AI:
    def _call_llm(self,*a,**kw):return '{"answer":"Renew by November 12.","source_ids":["1"]}'
class ChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=patch.object(chat,'CHAT_FILE',Path(self.tmp.name)/'chat.json');self.p.start()
    def tearDown(self):self.p.stop();self.tmp.cleanup()
    def test_persistence_and_sources(self):
        result=chat.ask(Engine(),'Acme renewal',AI());self.assertEqual(result,chat.history());self.assertEqual(result['messages'][1]['sources'][0]['id'],'1');self.assertNotIn('content',result['messages'][1]['sources'][0]);self.assertEqual(chat.CHAT_FILE.stat().st_mode & 0o777,0o600)
    def test_reject_invented_source(self):
        with patch.object(AI,'_call_llm',return_value='{"answer":"Fake","source_ids":["unknown"]}'):
            with self.assertRaises(ValueError):chat.ask(Engine(),'Acme',AI())
        self.assertEqual(chat.history()['messages'],[])
    def test_no_match_and_clear(self):
        result=chat.ask(Engine(),'zzzzzz',AI());self.assertEqual(result['messages'][1]['used'],0);self.assertEqual(chat.clear()['messages'],[])
    def test_followup_retrieves_previous_topic(self):
        messages,_,_=chat.retrieve(Engine(),'when is it due',[{'role':'user','text':'Acme renewal'}]);self.assertEqual(messages[0]['id'],'1')
