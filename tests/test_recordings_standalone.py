import copy
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from outlook_plugin import recorder, recordings, transcription, task_files, projects, tasks, meeting_tasks
from outlook_plugin.storage import read_json, write_json

class StandaloneRecordingsTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.projects=[]
        def update(data):self.projects=copy.deepcopy(data['projects'])
        for p in [patch.object(task_files,'ROOT',self.root/'attachments'),patch.object(recorder,'ROOT',self.root/'captures'),patch.object(recorder,'FILE',self.root/'session.json'),patch.object(transcription,'ROOT',self.root/'speech'),patch.object(projects,'list_projects',side_effect=lambda:copy.deepcopy(self.projects)),patch.object(task_files,'list_projects',side_effect=lambda:copy.deepcopy(self.projects)),patch.object(tasks,'load_tasks',return_value={}),patch.object(transcription,'update_config',side_effect=update),patch.object(recorder,'supported',return_value=True),patch.object(recorder.subprocess,'run',return_value=Mock(returncode=0)),patch.object(recorder.shutil,'disk_usage',return_value=Mock(free=10**10))]:
            p.start();self.addCleanup(p.stop)
        recorder.release_update()
    def capture(self):
        recorder.start({'title':'Unassigned call'})
        session=read_json(recorder.FILE,{})
        folder=recorder._folder(session)
        (folder/'recording.m4a').write_bytes(b'synthetic media')
        write_json(folder/'status.json',{'state':'complete'})
        self.assertEqual(recorder.snapshot()['state'],'complete')
        return session,transcription.listing()[0]
    def transcribe(self,job):
        result={'segments':[{'start':0,'end':2,'speaker':'Speaker 1','text':'I will send the proposal.'}]}
        write_json(transcription.folder(job['id'])/'result.json',result)
        with patch.object(meeting_tasks,'extract_recording',return_value={'added':1}) as extract:
            transcription.process(job,threading.Event());extract.assert_called_once()
        return transcription.load(job['id'])
    def test_no_project_capture_library_transcript_and_retry(self):
        session,job=self.capture();recorder.snapshot()
        self.assertEqual(len(transcription.listing()),1)
        rows=recordings.listing()['items'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['project_id'],'');self.assertEqual(rows[0]['owner_kind'],'library')
        job=self.transcribe(job)
        self.assertEqual(job['state'],'complete');self.assertIn('proposal',job['published_transcript'])
        self.assertEqual(self.projects,[])
        self.assertEqual(transcription.enqueue('',session['id'],retry=True)['id'],job['id'])
    def test_assign_preserves_file_and_job_and_publishes_transcript(self):
        session,job=self.capture();job=self.transcribe(job)
        self.projects=[{'id':'p','name':'Example','meetings':[]}]
        file=task_files.listing('library','recordings')[0]
        source=task_files.file_path(task_files.directory('library','recordings'),file)
        transcription.assign_recording(session['id'],'p')
        self.assertEqual(source.read_bytes(),b'synthetic media')
        self.assertEqual(len(transcription.listing()),1)
        self.assertEqual(transcription.load(job['id'])['project_id'],'p')
        self.assertIn('proposal',self.projects[0]['meetings'][0]['transcript'])
        rows=recordings.listing(project_id='p')['items'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['owner_kind'],'library')
        self.assertEqual(rows[0]['file']['id'],session['id'])
        recorder.snapshot();self.assertEqual(len(transcription.listing()),1)
    def test_assignment_rejects_active_and_missing_project(self):
        session,job=self.capture();self.projects=[{'id':'p','name':'Example','meetings':[]}]
        with self.assertRaises(ValueError):transcription.assign_recording(session['id'],'missing')
        with self.assertRaisesRegex(ValueError,'finish'):transcription.assign_recording(session['id'],'p')
        self.assertEqual(transcription.load(job['id'])['project_id'],'')
    def test_library_owner_cannot_be_arbitrary_path(self):
        for owner in ['../escape','','other']:
            with self.assertRaises(ValueError):task_files.directory('library',owner)
    def test_upload_without_project(self):
        import io
        rows=task_files.upload('library','recordings','Call.m4a',io.BytesIO(b'call'),4)
        self.assertEqual(recordings.listing()['items'][0]['file']['id'],rows[0]['id'])

    def test_task_extraction_without_project_has_stable_evidence(self):
        import json
        store={'suggestions':{}}
        job={'id':'a'*32,'project_id':'','title':'Call','published_transcript':'Alex: I will send the proposal.','occurred_at':''}
        answer={'tasks':[{'text':'Send the proposal','owner':'Alex','evidence':'I will send the proposal.','owner_evidence':'Alex: I will send the proposal.'}]}
        with patch.object(meeting_tasks.BobAIAgent,'_call_llm',return_value=json.dumps(answer)),patch.object(meeting_tasks.task_workflow,'load',return_value=store),patch.object(meeting_tasks.task_workflow,'save'),patch.object(meeting_tasks,'read_config',return_value={}):
            self.assertEqual(meeting_tasks.extract_recording(job)['added'],1)
            row=next(iter(store['suggestions'].values()))
            self.assertEqual(row['project_id'],'');self.assertEqual(row['owner'],'Alex')
            row['status']='dismissed';job['project_id']='p'
            self.assertEqual(meeting_tasks.extract_recording(job)['added'],0)
            self.assertEqual(row['status'],'dismissed')
