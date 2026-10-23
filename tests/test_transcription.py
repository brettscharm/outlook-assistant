import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from outlook_plugin import transcription as t, projects, task_files, meeting_tasks
from outlook_plugin.storage import write_json, read_json
from outlook_plugin.speech_worker import assign_speakers

class TranscriptionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.rows=[{'id':'p','name':'Project','meetings':[]}]
        self.files=[{'id':'f','name':'Call.m4a','recording':True,'suffix':'.m4a'}]
        self.config={'projects':self.rows}
        for p in [patch.object(t,'ROOT',self.root),patch.object(task_files,'listing',return_value=self.files),patch.object(projects,'list_projects',side_effect=lambda:copy.deepcopy(self.rows)),patch.object(t,'update_config',side_effect=self.update)]:p.start();self.addCleanup(p.stop)
    def update(self,data):self.rows=copy.deepcopy(data['projects'])
    def job(self):return t.enqueue('p','f')
    def result(self,job):
        result={'segments':[{'start':0,'end':4,'speaker':'Speaker 1','text':'My name is Alex. I will send the proposal.'}], 'speaker_names':{}}
        write_json(t.folder(job['id'])/'result.json',result);return result
    def test_idempotent_enqueue(self):
        first=self.job();self.assertEqual(first['id'],self.job()['id']);self.assertEqual(len(t.listing()),1)
    def test_file_must_be_project_recording(self):
        with self.assertRaises(ValueError):t.enqueue('p','missing')
        self.files[0]['recording']=False
        with self.assertRaises(ValueError):self.job()
    def test_transcript_then_tasks_and_retry_uses_saved_audio_result(self):
        job=self.job();self.result(job)
        with patch.object(t,'runtime') as runtime,patch.object(meeting_tasks,'extract',return_value={'added':2,'rejected':0}) as extract:
            t.process(job,threading.Event());self.assertEqual(extract.call_args.args[0]['project_id'],'p');runtime.assert_not_called()
        self.assertEqual(t.load(job['id'])['state'],'complete');self.assertEqual(t.load(job['id'])['added'],2)
        self.assertIn('Speaker 1:',self.rows[0]['meetings'][0]['transcript'])
        self.assertEqual(self.rows[0]['meetings'][0]['recording_file_id'],'f')
    def test_failed_bob_keeps_transcript_and_retry_does_not_duplicate_meeting(self):
        job=self.job();self.result(job)
        with patch.object(meeting_tasks,'extract',side_effect=ValueError('Bob unavailable')):
            with self.assertRaises(ValueError):t.process(job,threading.Event())
        self.assertTrue(self.rows[0]['meetings'][0]['transcript'])
        with patch.object(meeting_tasks,'extract',return_value={'added':0}):t.process(t.load(job['id']),threading.Event())
        self.assertEqual(len(self.rows[0]['meetings']),1)
    def test_crash_between_project_and_job_write_does_not_duplicate(self):
        job=self.job();result=self.result(job);t.persist_transcript(job,result)
        job['meeting_ids']=[];job.pop('published_transcript',None)
        t.persist_transcript(job,result);self.assertEqual(len(self.rows[0]['meetings']),1)
    def test_preserves_user_edited_transcript(self):
        job=self.job();result=self.result(job);t.persist_transcript(job,result)
        self.rows[0]['meetings'][0]['transcript']='My manual correction'
        with self.assertRaisesRegex(ValueError,'preserved'):t.persist_transcript(job,result)
        self.assertEqual(self.rows[0]['meetings'][0]['transcript'],'My manual correction')
    def test_speaker_confirmation_updates_project_and_queues_tasks(self):
        job=self.job();result=self.result(job);t.persist_transcript(job,result)
        job['state']='complete';t.save(job)
        updated=t.rename_speakers({'id':job['id'],'names':{'Speaker 1':'Alex Smith'}})
        self.assertEqual(updated['state'],'queued');self.assertIn('Alex Smith:',self.rows[0]['meetings'][0]['transcript'])
        self.assertEqual(t.detail(job['id'])['name_hints']['Speaker 1'],'Alex')
    def test_speaker_validation_and_active_work(self):
        job=self.job();self.result(job);job['state']='complete';t.save(job)
        for names in [{'Not a speaker':'Alex'},{'Speaker 1':'Bad\nName'}]:
            with self.assertRaises(ValueError):t.rename_speakers({'id':job['id'],'names':names})
        with t._WORK:
            with self.assertRaisesRegex(ValueError,'Wait'):t.rename_speakers({'id':job['id'],'names':{}})
    def test_removed_project_does_not_lose_result(self):
        job=self.job();result=self.result(job);self.rows=[]
        with self.assertRaisesRegex(ValueError,'retained'):t.persist_transcript(job,result)
        self.assertTrue((t.folder(job['id'])/'result.json').exists())
    def test_status_omits_transcript(self):
        job=self.job();t.persist_transcript(job,self.result(job));self.assertNotIn('published_transcript',t.listing()[0])
    def test_retry_queues_errors_but_does_not_duplicate_running_job(self):
        job=self.job();job['state']='error';t.save(job)
        self.assertEqual(t.enqueue('p','f',retry=True)['state'],'queued')
        self.assertEqual(len(t.listing()),1)
    def test_paths_reject_traversal(self):
        with self.assertRaises(ValueError):t.folder('../private')
    def test_speaker_overlap_and_recurring_identity(self):
        turns=[{'start':0,'end':1,'speaker':'Speaker 1'},{'start':1,'end':2,'speaker':'Speaker 2'},{'start':2,'end':3,'speaker':'Speaker 1'}]
        words=[{'start':i+.1,'end':i+.8,'text':' word'} for i in range(3)]
        self.assertEqual([s['speaker'] for s in assign_speakers(words,turns)],['Speaker 1','Speaker 2','Speaker 1'])
        turns.append({'start':2,'end':3,'speaker':'Speaker 2'})
        self.assertEqual(assign_speakers(words,turns)[-1]['speaker'],'Overlapping speakers')
        self.assertEqual(assign_speakers(words,[])[0]['speaker'],'Unknown speaker')
    def test_restart_resumes_without_losing_published_edit_guard(self):
        from outlook_plugin import recorder
        job=self.job();job.update(state='processing',published_transcript='Existing transcript');t.save(job)
        shutdown=threading.Event();seen=[]
        def process(restored,stop):seen.append(restored);stop.set()
        with patch.object(recorder,'snapshot'),patch.object(t,'process',side_effect=process):t.scheduler(shutdown)
        self.assertEqual(len(seen),1)
        self.assertEqual(seen[0]['published_transcript'],'Existing transcript')
        self.assertEqual(seen[0]['state'],'queued')
    def test_empty_audio_completes_without_bob(self):
        job=self.job();write_json(t.folder(job['id'])/'result.json',{'segments':[],'speaker_names':{}})
        with patch.object(meeting_tasks,'extract') as extract:t.process(job,threading.Event());extract.assert_not_called()
        self.assertEqual(t.load(job['id'])['message'],'No speech detected')
