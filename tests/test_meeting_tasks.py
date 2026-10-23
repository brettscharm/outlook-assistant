import copy
import json
import unittest
from unittest.mock import patch
from outlook_plugin import meeting_tasks, projects


class MeetingTasksTest(unittest.TestCase):
    def setUp(self):
        self.store={'suggestions':{},'processed':{}}
        self.meeting={'id':'m','title':'Kickoff','transcript':'Alex Smith: I will send the proposal. Sam: I will book the call.', 'recording_url':'https://example.com/recording'}
        self.rows=[{'id':'p','meetings':[self.meeting]}]
        self.answer={'tasks':[{'text':'Send the proposal','owner':'Alex Smith','evidence':'I will send the proposal.','owner_evidence':'Alex Smith: I will send the proposal.','description':'Send the proposal discussed in the kickoff.'}]}
        self.patches=[patch.object(projects,'list_projects',return_value=self.rows),patch.object(meeting_tasks.task_workflow,'load',side_effect=lambda:copy.deepcopy(self.store)),patch.object(meeting_tasks.task_workflow,'save',side_effect=self.save),patch.object(meeting_tasks,'read_config',return_value={'user_context':{'full_name':'Alex Smith'}}),patch.object(meeting_tasks.BobAIAgent,'_call_llm',side_effect=lambda *a,**k:json.dumps(self.answer))]
        for p in self.patches:p.start();self.addCleanup(p.stop)
    def save(self,data):self.store=data
    def run_extract(self):return meeting_tasks.extract({'project_id':'p','meeting_id':'m'})
    def test_project_owner_and_evidence(self):
        self.assertEqual(self.run_extract()['added'],1)
        task=next(iter(self.store['suggestions'].values()))
        self.assertEqual((task['type'],task['project_id'],task['source_type']),('my','p','meeting'))
        self.assertEqual(task['email_id'],'')
        self.assertEqual(task['source_url'],'https://example.com/recording')
    def test_dismissal_survives_reanalysis(self):
        self.run_extract();next(iter(self.store['suggestions'].values()))['status']='dismissed'
        self.assertEqual(self.run_extract()['added'],0)
        self.assertEqual(next(iter(self.store['suggestions'].values()))['status'],'dismissed')
    def test_unverified_action_rejected(self):
        self.answer['tasks'][0]['evidence']='Invented promise'
        self.assertEqual(self.run_extract(),{'added':0,'rejected':1})
    def test_unverified_owner_and_deadline_removed(self):
        self.answer['tasks'][0].update(owner='Invented Person',due_date='2026-11-01',due_evidence='next week')
        self.run_extract();task=next(iter(self.store['suggestions'].values()))
        self.assertEqual((task['owner'],task['type'],task['due_date']),('Unassigned','others',''))
    def test_no_transcript_does_not_call_bob(self):
        self.meeting['transcript']=''
        with self.assertRaisesRegex(ValueError,'transcript'):self.run_extract()
        meeting_tasks.BobAIAgent._call_llm.assert_not_called()
    def test_meeting_roundtrip(self):
        value=dict(self.meeting,recording_file_id='file1')
        self.assertEqual(projects.validate_meetings([value])[0]['transcript'],value['transcript'])
        self.assertEqual(projects.validate_meetings([value])[0]['recording_file_id'],'file1')
    def test_oversized_transcript_rejected(self):
        with self.assertRaises(ValueError):projects.validate_meetings([dict(self.meeting,transcript='x'*500001)])

    def test_accept_keeps_project_and_recording_link(self):
        self.run_extract();task=next(iter(self.store['suggestions'].values()))
        with patch.object(meeting_tasks.task_workflow,'load_tasks',return_value={}), patch.object(meeting_tasks.task_workflow,'add_task') as add, patch.object(meeting_tasks.task_workflow,'snapshot',return_value={}):
            meeting_tasks.task_workflow.action({'id':task['id'],'action':'accept'})
        self.assertEqual(add.call_args.kwargs['project_id'],'p')
        self.assertEqual(add.call_args.kwargs['source_type'],'meeting')
        self.assertEqual(add.call_args.kwargs['source_url'],'https://example.com/recording')
    def test_reworded_title_same_evidence_is_not_duplicated(self):
        self.run_extract();self.answer['tasks'][0]['text']='Prepare and send the proposal'
        self.assertEqual(self.run_extract()['added'],0)

    def test_anonymous_speaker_is_not_assigned_as_a_person(self):
        self.meeting['transcript']='Speaker 1: I will send the proposal.'
        self.answer['tasks'][0].update(owner='Speaker 1',owner_evidence=self.meeting['transcript'])
        self.run_extract()
        self.assertEqual(next(iter(self.store['suggestions'].values()))['owner'],'Unassigned')

    def test_named_speaker_updates_pending_but_not_accepted(self):
        self.answer['tasks'][0].update(owner='',owner_evidence='')
        self.run_extract()
        self.answer['tasks'][0].update(owner='Alex Smith',owner_evidence='Alex Smith: I will send the proposal.')
        self.assertEqual(self.run_extract()['added'],0)
        old=next(iter(self.store['suggestions'].values()))
        self.assertEqual(old['owner'],'Alex Smith')
        old['status']='accepted';old['owner']='User edited'
        self.run_extract()
        self.assertEqual(next(iter(self.store['suggestions'].values()))['owner'],'User edited')

    def test_long_transcript_is_processed_in_sections(self):
        self.meeting['transcript']='Alex Smith: I will send the proposal.\n'*1500
        self.run_extract()
        self.assertGreater(meeting_tasks.BobAIAgent._call_llm.call_count,1)
        self.assertEqual(len(self.store['suggestions']),1)
