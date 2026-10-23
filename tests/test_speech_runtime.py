import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch,Mock
from outlook_plugin import speech_runtime as r

class SpeechRuntimeTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        for p in [patch.object(r.platform,'system',return_value='Darwin'),patch.object(r.platform,'machine',return_value='arm64'),patch.object(r.platform,'mac_ver',return_value=('14.0','','')),patch.object(r.shutil,'disk_usage',return_value=Mock(free=10**10))]:p.start();self.addCleanup(p.stop)
    def test_ready_runtime_requires_no_install(self):
        env=self.root/'runtime-v2';(env/'bin').mkdir(parents=True);(env/'bin/python3').touch()
        (env/'ready').write_text(hashlib.sha256(Path(r.__file__).with_name('speech-requirements.txt').read_bytes()).hexdigest())
        with patch.object(r.subprocess,'run') as run:
            self.assertEqual(r.install(self.root),env/'bin/python3');run.assert_not_called()
    def test_bad_archive_never_extracts_or_executes(self):
        commands=[]
        def run(args,**kwargs):
            commands.append(args)
            Path(args[args.index('--output')+1]).write_bytes(b'wrong download')
        with patch.object(r.subprocess,'run',side_effect=run):
            with self.assertRaisesRegex(ValueError,'verification'):r.install(self.root)
        self.assertEqual(len(commands),1)
    def test_download_failure_is_actionable(self):
        with patch.object(r.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['curl'])):
            with self.assertRaisesRegex(ValueError,'recording is saved'):r.install(self.root)
    def test_requires_free_disk_and_supported_mac(self):
        with patch.object(r.platform,'machine',return_value='x86_64'):
            with self.assertRaisesRegex(ValueError,'Apple silicon'):r.install(self.root)
        with patch.object(r.shutil,'disk_usage',return_value=Mock(free=1)):
            with self.assertRaisesRegex(ValueError,'3 GB'):r.install(self.root)
