import json
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock,patch
from zoneinfo import ZoneInfo
from outlook_plugin import workspace_search as s

class WorkspaceSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.patches=[patch.object(s,'FILE',Path(self.tmp.name)/'search.json'),patch.object(s,'read_config',return_value={'domain_companies':{},'bob_api_key':'DO_NOT_EXPOSE'}),patch.object(s.tasks,'load_tasks',return_value={}),patch.object(s.projects,'list_projects',return_value=[]),patch.object(s.task_workflow,'load',return_value={'suggestions':{}}),patch.object(s.drafts,'load',return_value={'entries':{}}),patch.object(s.calendar_cache,'_hydrate'),patch.object(s.calendar_cache,'_CACHE',{'events':[]})]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.engine=Mock();self.engine.get_emails.return_value=[]
    def test_timezone_boundaries(self):
        zone=ZoneInfo('America/New_York');day=date(2026,10,1)
        self.assertFalse(s.in_range('2026-10-01T03:59:00Z',day,day,zone))
        self.assertTrue(s.in_range('2026-10-02T03:59:00Z',day,day,zone))
        self.assertFalse(s.in_range('2026-10-02T04:00:00Z',day,day,zone))
    def test_reversed_range_rejected(self):
        with self.assertRaises(ValueError):s.options({'question':'Q','from':'2026-10-22','to':'2026-10-01'})
    def test_period_and_undated_transcripts(self):
        rows=[{'id':'p','name':'P','description':'Background','meetings':[{'id':'in','title':'Current','occurred_at':'2026-10-15','transcript':'Hello'},{'id':'out','title':'Old','occurred_at':'2026-09-01','transcript':'Old'},{'id':'unknown','title':'Unknown','transcript':'Unknown'}]}]
        with patch.object(s.projects,'list_projects',return_value=rows):docs,coverage=s.collect(self.engine,date(2026,10,1),date(2026,10,31),ZoneInfo('UTC'))
        self.assertEqual({d['key'] for d in docs},{'p','in'});self.assertEqual(coverage['undated'],1)
        self.assertNotIn('DO_NOT_EXPOSE',json.dumps(docs))
    def test_parallel_reviews_and_verified_synthesis(self):
        docs=[{'id':'unused','kind':'email','key':str(i),'title':'Demo','content':'Evidence '+str(i),'project_id':'','context':False} for i in range(24)]
        barrier=threading.Barrier(2);active=0;maximum=0;lock=threading.Lock()
        class AI:
            def _call_llm(self,prompt,**kwargs):
                nonlocal active,maximum
                self_data=json.loads(prompt.split('\n',1)[1]);source=self_data['sources'][0]
                if 'findings' not in self_data:
                    with lock:active+=1;maximum=max(maximum,active)
                    barrier.wait(timeout=3)
                    with lock:active-=1
                return json.dumps({'answer':'Finding ['+source['id']+']','citations':[{'id':source['id'],'quote':source['content']}]})
        with patch.object(s,'collect',return_value=(docs,{'warnings':[],'documents':24,'undated':0,'by_type':{'email':24}})):
            result=s.run(self.engine,{'question':'Demo','timezone':'UTC'},AI)
        self.assertEqual(maximum,2);self.assertTrue(result['sources']);self.assertEqual(s.snapshot()['results'][0]['answer'],result['answer'])
    def test_invented_source_rejected(self):
        with self.assertRaises(ValueError):s.checked('{"answer":"Fact [S1]","citations":[{"id":"S1","quote":"Fake"}]}',{})
    def test_search_lock_blocks_duplicate_start(self):
        with patch.object(s,'_BOB_SEARCH_LOCK') as lock:
            lock.acquire.return_value=False
            with self.assertRaisesRegex(ValueError,'workspace search'):s.start(self.engine,{'question':'Q'})
            lock.release.assert_not_called()
