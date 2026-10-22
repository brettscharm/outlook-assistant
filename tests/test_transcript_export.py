import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from outlook_plugin import transcript_export as export

class TranscriptExportTests(unittest.TestCase):
    def test_preserves_unicode_timestamps_and_newlines(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'call.txt'
            content='00:01:02 José: Hello.\n00:01:05 Alex: Send the proposal.\n'
            with patch.object(export.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=str(path)+'\n')) as run:
                self.assertTrue(export.export({'title':'Call / Acme','transcript':content})['saved'])
            self.assertEqual(path.read_bytes(),content.encode('utf-8'))
            self.assertEqual(run.call_args.args[0][-1],'Call - Acme-transcript.txt')
    def test_cancel_creates_nothing(self):
        with patch.object(export.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='\n')),patch.object(export,'_replace') as write:
            self.assertFalse(export.export({'transcript':'Hello'})['saved']);write.assert_not_called()
    def test_blank_rejected_before_dialog(self):
        with patch.object(export.subprocess,'run') as run:
            with self.assertRaises(ValueError):export.export({'transcript':'  '})
            run.assert_not_called()
