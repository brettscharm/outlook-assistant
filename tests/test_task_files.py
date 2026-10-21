import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import task_files as f

class FileTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for p in (patch.object(f,'ROOT',Path(self.tmp.name)),patch.object(f,'load_tasks',return_value={'my':[{'id':'task1'}]}),patch.object(f,'list_projects',return_value=[{'id':'project1'}])):
   p.start();self.addCleanup(p.stop)
 def upload(self,kind='task',owner='task1',name='Plan.docx'):
  return f.change(dict(kind=kind,owner=owner,action='add',name=name,content=base64.b64encode(b'document bytes').decode()))
 def test_saved_copy_open_remove_and_owner_isolation(self):
  row=self.upload()[0];self.assertEqual(f.listing('task','task1'),[row]);self.assertEqual(f.listing('project','project1'),[])
  path=f.directory('task','task1')/(row['id']+'.docx');self.assertEqual(path.read_bytes(),b'document bytes')
  with patch.object(f.subprocess,'run') as run:
   f.change(dict(kind='task',owner='task1',action='open',id=row['id']))
   self.assertEqual(run.call_args.args[0],['/usr/bin/open',str(path)])
  f.change(dict(kind='task',owner='task1',action='remove',id=row['id']))
  self.assertFalse(path.exists());self.assertEqual(f.listing('task','task1'),[])
 def test_rejects_bad_names_unknown_owners_and_large_files(self):
  for name in ('../file.pdf','thing.app','run.command','a\\b.docx'):
   with self.assertRaises(ValueError):self.upload(name=name)
  with self.assertRaises(ValueError):self.upload(owner='../task1')
  with self.assertRaises(ValueError):self.upload(owner='unknown')
  with patch.object(f,'MAX_BYTES',2):
   with self.assertRaises(ValueError):self.upload()
 def test_same_names_have_separate_copies(self):
  self.upload('project','project1','Plan.pdf');rows=self.upload('project','project1','Plan.pdf')
  self.assertEqual(len(rows),2);self.assertNotEqual(rows[0]['id'],rows[1]['id'])
