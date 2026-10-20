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
