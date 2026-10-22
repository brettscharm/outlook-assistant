import unittest
from unittest.mock import patch
from outlook_plugin import recordings as r

class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.projects=[{'id':'p','name':'Acme','meetings':[{'id':'m','title':'Kickoff','recording_file_id':'f','recording_url':'https://example.com/recording','transcript':'Alex: Hello','occurred_at':'2026-10-20T10:00:00Z'},{'id':'transcript','title':'Notes call','transcript':'Saved text'},{'id':'missing','title':'Missing','recording_file_id':'gone'}]},{'id':'q','name':'Other','meetings':[]}]
        self.files=[{'id':'f','name':'Kickoff.mp4','recording':True,'size':500},{'id':'g','name':'Audio.m4a','recording':True,'size':400},{'id':'d','name':'Notes.pdf','size':100}]
        for p in [patch.object(r.projects,'list_projects',side_effect=lambda:self.projects),patch.object(r.tasks,'load_tasks',return_value={'my':[{'id':'task','text':'Follow up','project_id':'q'}]}),patch.object(r.task_files,'listing',side_effect=lambda kind,owner:self.files if owner=='p' else [{'id':'t','name':'Task.wav','recording':True,'size':10}] if kind=='task' else [])]:p.start();self.addCleanup(p.stop)
    def test_all_sources_and_no_duplicate_attachment(self):
        result=r.listing();self.assertEqual(result['total'],5)
        meeting=result['items'][0];self.assertEqual(meeting['meeting_id'],'m');self.assertTrue(meeting['has_transcript']);self.assertEqual(meeting['file']['id'],'f')
        self.assertEqual(sum((item.get('file') or {}).get('id')=='f' for item in result['items']),1)
        self.assertTrue(next(i for i in result['items'] if i.get('meeting_id')=='missing')['missing_file'])
        self.assertFalse(any((i.get('file') or {}).get('id')=='d' for i in result['items']))
    def test_project_filter_includes_task_recordings(self):
        items=r.listing(project_id='q')['items'];self.assertEqual(len(items),1);self.assertEqual(items[0]['owner_kind'],'task')
    def test_search_and_pagination(self):
        self.assertEqual(r.listing(query='Acme')['total'],4)
        first=r.listing(limit=2);second=r.listing(limit=2,offset=2)
        self.assertEqual(first['total'],5);self.assertFalse({i['id'] for i in first['items']}&{i['id'] for i in second['items']})
    def test_missing_index_warns_without_hiding_transcripts(self):
        with patch.object(r.task_files,'listing',side_effect=OSError('missing')):result=r.listing()
        self.assertTrue(result['warnings']);self.assertTrue(any(i['has_transcript'] for i in result['items']))
