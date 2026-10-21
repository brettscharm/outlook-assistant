import json,unittest
from outlook_plugin.task_workflow import dismissal_context
class DismissalContextTests(unittest.TestCase):
 def rows(self,n):return {str(i):{'text':'Unrelated action '+str(i),'reason':'not_role','status':'dismissed','dismissed_at':i} for i in range(n)}
 def test_more_than_twenty_and_full_history_counts(self):
  examples,summary=dismissal_context(self.rows(150),[])
  self.assertEqual(len(examples),100);self.assertEqual(summary['total'],150);self.assertEqual(summary['by_reason']['Not relevant to my role'],150)
  self.assertEqual(examples[0]['text'],'Unrelated action 149')
 def test_old_relevant_feedback_survives_new_unrelated_items(self):
  rows=self.rows(250);rows['0'].update(text='Renewal proposal for Acme',email_id='m1')
  examples,summary=dismissal_context(rows,[{'id':'m1','subject':'Acme renewal'}])
  self.assertEqual(examples[0]['text'],'Renewal proposal for Acme');self.assertEqual(summary['total'],250)
 def test_quick_restored_and_invalid_feedback_excluded(self):
  rows=self.rows(4);rows['0']['reason']='quick';rows['1']['status']='review';rows['2']['reason']='unknown'
  examples,summary=dismissal_context(rows,[])
  self.assertEqual(len(examples),1);self.assertEqual(summary['total'],1)
 def test_deduplication_and_prompt_size(self):
  rows=self.rows(200)
  for i,item in enumerate(rows.values()):item['text']=('A'*3000)+str(i)
  examples,summary=dismissal_context(rows,[])
  self.assertEqual(len(examples),1);self.assertEqual(summary['total'],200)
  for i,item in enumerate(rows.values()):item['text']=str(i)+'A'*3000
  examples,_=dismissal_context(rows,[])
  self.assertLessEqual(sum(len(json.dumps(e,ensure_ascii=False)) for e in examples),24000)
