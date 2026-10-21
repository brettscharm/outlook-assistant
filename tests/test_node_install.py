import io,tarfile,tempfile,unittest
from pathlib import Path
from outlook_plugin.node_install import unpack
class NodeArchiveTests(unittest.TestCase):
 def test_rejects_traversal_and_external_links(self):
  for name,link in [('node/../../escape',''),('node/npm','../../escape')]:
   with tempfile.TemporaryDirectory() as d:
    root=Path(d);archive=root/'test.tar.gz';target=root/'runtime';target.mkdir()
    with tarfile.open(archive,'w:gz') as tar:
     info=tarfile.TarInfo(name)
     if link:info.type=tarfile.SYMTYPE;info.linkname=link
     tar.addfile(info,io.BytesIO(b''))
    with self.assertRaises(ValueError):unpack(archive,target,'node')
 def test_internal_npm_link_and_executable_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);archive=root/'test.tar.gz';target=root/'runtime';target.mkdir()
   with tarfile.open(archive,'w:gz') as tar:
    info=tarfile.TarInfo('node/lib/npm.js');info.size=2;info.mode=0o755;tar.addfile(info,io.BytesIO(b'OK'))
    info=tarfile.TarInfo('node/bin/npm');info.type=tarfile.SYMTYPE;info.linkname='../lib/npm.js';tar.addfile(info)
   unpack(archive,target,'node');self.assertEqual((target/'bin/npm').read_text(),'OK')
