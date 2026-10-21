import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from email import policy
from email.parser import BytesParser
from outlook_plugin import mail_archive as archive
class Immediate:
 def __init__(self,target,**kw):self.target=target
 def start(self):self.target()
class ArchiveTests(unittest.TestCase):
 def test_snapshot_preserves_attachment_and_never_overwrites_with_preview(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);profile=root/'profile';(profile/'Files').mkdir(parents=True);(profile/'Files/test.txt').write_text('Attachment fixture')
   row={'id':'one','subject':'Synthetic subject','body':'Full fixture body','body_complete':True,'sender':'a@example.com','received_time':'2026-10-21T12:00:00Z','attachments':[{'path':'~/Files/test.txt','downloaded':True,'name':'test.txt'}]}
   class Engine:
    def get_active_backend(self):return self
    def profile(self):return profile
    def get_emails(self,**kw):return [row]
    def get_email_details(self,id):return row
   with patch.object(archive,'ROOT',root/'archive'),patch.object(archive.threading,'Thread',Immediate):
    result=archive.archive(Engine());self.assertEqual(result['state'],'complete');self.assertEqual(result['attachments'],1)
    saved=next((root/'archive').rglob('*.eml'));before=saved.read_bytes();parsed=BytesParser(policy=policy.default).parsebytes(before)
    self.assertEqual(next(parsed.iter_attachments()).get_payload(decode=True),b'Attachment fixture')
    row.update(body='',preview='Short preview',body_complete=False);archive.archive(Engine());self.assertEqual(saved.read_bytes(),before)
 def test_attachment_cannot_escape_files_directory(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'Files').mkdir();(root/'secret').write_text('do not read')
   self.assertIsNone(archive.attachment_path(root,'~/Files/../secret'))
   (root/'Files/link').symlink_to(root/'secret')
   self.assertIsNone(archive.attachment_path(root,'~/Files/link'))
