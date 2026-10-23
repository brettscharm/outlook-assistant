import json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from outlook_plugin import recorder as r, transcription
from outlook_plugin.storage import write_json,read_json

class RecorderTests(unittest.TestCase):
 def setUp(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name);self.dest=self.root/'attachments';self.dest.mkdir()
  for p in [patch.object(transcription,'ROOT',self.root/'transcription'),patch.object(r,'ROOT',self.root/'recordings'),patch.object(r,'FILE',self.root/'session.json'),patch.object(r,'supported',return_value=True),patch.object(r.task_files,'directory',return_value=self.dest),patch.object(r.subprocess,'run',return_value=Mock(returncode=0)),patch.object(r.shutil,'disk_usage',return_value=Mock(free=10**10))]:p.start();self.addCleanup(p.stop)
  r.release_update()
 def start(self):return r.start({'project_id':'p','title':'Test','video':False,'microphone':True})
 def native(self,state,**kw):
  session=read_json(r.FILE,{});folder=r._folder(session);write_json(folder/'status.json',dict(state=state,message=state,**kw));return session,folder
 def test_start_stop_and_duplicate(self):
  self.assertTrue(self.start()['active'])
  with self.assertRaises(ValueError):self.start()
  r.stop();self.assertTrue((r._folder(read_json(r.FILE,{}))/'stop').exists())
 def test_completed_attachment_persists_and_registers_once(self):
  self.start();session,folder=self.native('complete');(folder/'recording.m4a').write_bytes(b'fixture media')
  self.assertEqual(r.snapshot()['state'],'complete');r.snapshot()
  self.assertEqual(len(transcription.listing()),1)
  self.assertEqual(transcription.listing()[0]['state'],'queued')
  files=read_json(self.dest/'index.json',{})['files'];self.assertEqual(len(files),1);self.assertEqual(files[0]['name'],'Test.m4a');self.assertTrue((self.dest/'recordings'/(session['id']+'.m4a')).is_file())
 def test_recovers_rename_before_index_write(self):
  self.start();session,folder=self.native('complete');target=self.dest/'recordings';target.mkdir();(target/(session['id']+'.m4a')).write_bytes(b'saved')
  self.assertEqual(r.snapshot()['state'],'complete');self.assertEqual(len(read_json(self.dest/'index.json',{})['files']),1)
 def test_failed_registration_keeps_recording(self):
  self.start();session,folder=self.native('complete');(folder/'recording.m4a').write_bytes(b'fixture')
  with patch.object(r.task_files,'directory',side_effect=ValueError('Project missing')):self.assertEqual(r.snapshot()['state'],'failed')
  self.assertTrue((folder/'recording.m4a').exists())
 def test_updates_and_capture_are_mutually_exclusive(self):
  self.assertTrue(r.reserve_update())
  with self.assertRaises(ValueError):self.start()
  r.release_update();self.start();self.assertFalse(r.reserve_update())
 def test_missing_native_process_is_not_reported_as_recording(self):
  self.start();self.native('recording',pid=1234)
  with patch.object(r.os,'kill',side_effect=ProcessLookupError):self.assertEqual(r.snapshot()['state'],'failed')
 def test_validation_and_low_disk_do_not_launch(self):
  for args in [{'project_id':'p','video':'yes'},{'project_id':'p','title':'../bad'}]:
   with self.assertRaises(ValueError):r.start(args)
  with patch.object(r.shutil,'disk_usage',return_value=Mock(free=100)):
   with self.assertRaises(ValueError):self.start()
  r.subprocess.run.assert_not_called()
 def test_launch_timeout(self):
  self.start();saved=read_json(r.FILE,{});saved['created']=time.time()-100;write_json(r.FILE,saved)
  self.assertEqual(r.snapshot()['state'],'failed')
