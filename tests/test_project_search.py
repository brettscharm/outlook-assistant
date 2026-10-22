import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from outlook_plugin import project_search as search

class ProjectSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.project={'id':'p','name':'Launch','description':'Launch project','email_ids':['e1'],'meetings':[{'id':'m','title':'Kickoff','transcript':'Alex will deliver the demo on Friday.'}]}
        self.engine=Mock();self.engine.get_email_details.return_value={'id':'e1','subject':'Launch email','body':'Budget is approved.'}
        patches=[patch.object(search,'ROOT',Path(self.temp.name)),patch.object(search.project_mail,'project',return_value=self.project),patch.object(search.tasks,'load_tasks',return_value={'my':[{'id':'t','text':'Prepare demo','project_id':'p'},{'id':'other','text':'Private unrelated task','project_id':'q'}]}),patch.object(search,'visible_messages',side_effect=lambda m:m)]
        for p in patches:p.start();self.addCleanup(p.stop)
    def test_project_scope_and_transcript(self):
        docs,missing=search.documents(self.engine,'p')
        self.assertEqual({d['kind'] for d in docs},{'project','task','meeting','email'})
        self.assertNotIn('other',[d['key'] for d in docs]);self.assertEqual(missing,0)
    def test_full_transcript_searched(self):
        docs=[{'title':'Call','kind':'meeting','key':'m','content':'x '*20000+'The zebra launch is cancelled.'}]
        selected,total=search.retrieve(docs,'zebra')
        self.assertIn('zebra',selected[0]['content']);self.assertGreater(total,10)
    def test_excluded_email_omitted(self):
        with patch.object(search,'visible_messages',return_value=[]):
            docs,missing=search.documents(self.engine,'p')
        self.assertEqual(missing,1);self.assertNotIn('email',[d['kind'] for d in docs])
    def test_verified_answer_persists(self):
        ai=Mock();ai._call_llm.return_value='{"answer":"Launch project [S1]", "citations":[{"id":"S1","quote":"Launch project"}]}'
        result=search.ask(self.engine,{'project_id':'p','question':'Launch project'},ai)
        self.assertEqual(len(result['messages']),2);self.assertEqual(search.history('p'),result)
    def test_fabricated_quote_not_saved(self):
        ai=Mock();ai._call_llm.return_value='{"answer":"Made up [S1]", "citations":[{"id":"S1","quote":"fabrication"}]}'
        with self.assertRaises(ValueError):search.ask(self.engine,{'project_id':'p','question':'Launch project'},ai)
        self.assertEqual(search.history('p')['messages'],[])
    def test_missing_citations_do_not_present_claims(self):
        ai=Mock();ai._call_llm.return_value='{"answer":"Invented answer", "citations":[]}'
        result=search.ask(self.engine,{'project_id':'p','question':'Launch'},ai)
        self.assertNotIn('Invented',result['messages'][-1]['text'])
