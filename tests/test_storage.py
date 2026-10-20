import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import storage,drafts
class StorageTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'saved.json'
    def tearDown(self):self.tmp.cleanup()
    def test_recovers_previous_save_and_preserves_damaged_original(self):
        storage.write_json(self.path,{'value':1});storage.write_json(self.path,{'value':2});self.path.write_text('{broken')
        self.assertEqual(storage.read_json(self.path,{}),{'value':1})
        damaged=list(storage.backups(self.path)[0].parent.glob('*.damaged-*'));self.assertEqual(len(damaged),1);self.assertEqual(damaged[0].read_text(),'{broken')
        self.assertEqual(self.path.stat().st_mode&0o777,0o600);self.assertEqual(damaged[0].parent.stat().st_mode&0o777,0o700)
    def test_failed_replacement_keeps_existing_data(self):
        storage.write_json(self.path,{'value':1});real=os.replace
        def replace(src,dst):
            if Path(dst)==self.path:raise OSError('simulated interrupted write')
            return real(src,dst)
        with patch.object(storage.os,'replace',side_effect=replace):
            with self.assertRaises(OSError):storage.write_json(self.path,{'value':2})
        self.assertEqual(json.loads(self.path.read_text()),{'value':1})
    def test_saved_data_survives_process_kill(self):
        code='from outlook_plugin.storage import write_json;from pathlib import Path;import os,signal,sys;write_json(Path(sys.argv[1]),{"saved":True});os.kill(os.getpid(),signal.SIGKILL)'
        result=subprocess.run([sys.executable,'-c',code,str(self.path)],timeout=10,capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertEqual(storage.read_json(self.path,{}),{'saved':True})
    def test_draft_conflict_cannot_overwrite_newer_copy(self):
        with patch.object(drafts,'DRAFTS_FILE',self.path):
            first=drafts.save_changes({'changes':[{'id':'email1','revision':0,'text':'Saved text'}]});self.assertEqual(first['saved']['email1'],1)
            second=drafts.save_changes({'changes':[{'id':'email1','revision':0,'text':'Stale text'}]});self.assertEqual(second['conflicts'],['email1']);self.assertEqual(drafts.load()['entries']['email1']['text'],'Saved text')
            drafts.save_changes({'changes':[{'id':'email1','revision':1,'deleted':True}]});self.assertTrue(drafts.load()['entries']['email1']['deleted'])
    def test_rich_draft_roundtrip_and_legacy_plain_text(self):
        with patch.object(drafts,'DRAFTS_FILE',self.path):
            html='<p><strong>Hello</strong></p><ul><li>Next step</li></ul>'
            drafts.save_changes({'changes':[{'id':'rich','revision':0,'text':'Hello\nNext step','html':html},{'id':'legacy','revision':0,'text':'Plain draft'}]})
            saved=drafts.load()['entries']
            self.assertEqual(saved['rich']['html'],html)
            self.assertEqual(saved['legacy']['text'],'Plain draft')
            self.assertEqual(saved['legacy']['html'],'')
            with self.assertRaises(ValueError):drafts.save_changes({'changes':[{'id':'rich','revision':1,'html':'a'*150001}]})
            self.assertEqual(drafts.load()['entries']['rich']['html'],html)
