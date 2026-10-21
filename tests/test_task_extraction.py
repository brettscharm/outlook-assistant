import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin.ai_agent import BobAIAgent
from outlook_plugin import tasks

class ExtractionTests(unittest.TestCase):
    def test_requires_known_source_and_grounded_quote(self):
        messages=[dict(id='one',subject='Review',content='Please review the proposal by Friday.')]
        valid=dict(text='Review proposal',type='my',email_id='one',evidence='review the proposal by Friday')
        candidates=[valid,valid,dict(valid,email_id='invented'),dict(valid,evidence='Pay the invoice'),dict(valid,type='unknown')]
        agent=BobAIAgent('fake')
        with patch.object(agent,'_call_llm',return_value=json.dumps({'tasks':candidates})):
            result=agent.extract_tasks(messages)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['email_subject'],'Review')
    def test_empty_mail_skips_bob_and_bad_json_surfaces(self):
        agent=BobAIAgent('fake')
        with patch.object(agent,'_call_llm',return_value='bad') as call:
            self.assertEqual(agent.extract_tasks([]),[]);call.assert_not_called()
            with self.assertRaises(RuntimeError):agent.extract_tasks([dict(id='1',subject='a',content='b')])
    def test_saved_link_survives_toggle_and_duplicate_is_ignored(self):
        with tempfile.TemporaryDirectory() as d,patch.object(tasks,'TASKS_FILE',Path(d)/'tasks.json'):
            source=dict(email_id='one',email_subject='Review',evidence='Please review')
            result=tasks.add_task('my','Review proposal',source=source)
            result=tasks.add_task('my',' review  proposal ',source=source)
            self.assertEqual(len(result['my_tasks']),1)
            item=result['my_tasks'][0]
            result=tasks.toggle_task(item['id'])
            self.assertTrue(result['my_tasks'][0]['completed'])
            self.assertEqual(result['my_tasks'][0]['email_id'],'one')
            self.assertEqual(tasks.TASKS_FILE.stat().st_mode&0o777,0o600)

    def test_scheduling_completion_rejects_promises_tentative_and_cancellation(self):
        task={'id':'schedule','text':'Schedule Acme kickoff','type':'my'}
        agent=BobAIAgent('fake')
        for quote in ('I will schedule the Acme kickoff tomorrow.','The Acme kickoff is tentative.','The Acme kickoff was cancelled.','The Acme kickoff is not yet scheduled.'):
            source={'id':'one','subject':'Acme','content':quote}
            answer={'tasks':[],'completed':[{'task_id':'schedule','email_id':'one','evidence':quote}]}
            with patch.object(agent,'_call_llm',return_value=json.dumps(answer)):
                agent.extract_tasks([source],active_tasks=[task])
            self.assertEqual(agent.last_completions,[],quote)
        quote='The Acme kickoff is scheduled for Friday. I sent the invitation.'
        with patch.object(agent,'_call_llm',return_value=json.dumps({'tasks':[],'completed':[{'task_id':'schedule','email_id':'one','evidence':quote}]})):
            agent.extract_tasks([{'id':'one','subject':'Acme','content':quote}],active_tasks=[task])
        self.assertEqual(agent.last_completions[0]['task_id'],'schedule')
        self.assertNotIn('completed',task)  # Detection never mutates the saved task.
    def test_scheduling_rules_apply_even_with_custom_task_guidance(self):
        agent=BobAIAgent('fake')
        with patch.object(agent,'_call_llm',return_value='{"tasks":[]}') as call:
            agent.extract_tasks([{'id':'one','subject':'Meeting','content':'Arrange a call.'}])
        prompt=call.call_args.args[0]
        self.assertIn('Assign the named scheduler',prompt)
        self.assertIn('deadline to SEND',prompt)
        self.assertIn('Completion remains a review suggestion',prompt)
