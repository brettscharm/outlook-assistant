import io,unittest
from unittest.mock import patch
from outlook_plugin import bob_install as b,ai_agent as a
class BobInstallTests(unittest.TestCase):
 def test_release_checks_supported_version_and_caches(self):
  with patch.object(b,'_RELEASE',{'checked':0,'version':'','error':''}),patch.object(b.urllib.request,'urlopen',return_value=io.BytesIO(b'2.0.2')) as fetch:
   self.assertEqual(b.release()['version'],'2.0.2');b.release();self.assertEqual(fetch.call_count,1)
  with patch.object(b,'_RELEASE',{'checked':0,'version':'','error':''}),patch.object(b.urllib.request,'urlopen',return_value=io.BytesIO(b'3.0.0')):
   self.assertEqual(b.release()['version'],'');self.assertTrue(b.release()['error'])
 def test_missing_node_starts_private_runtime_setup(self):
  from outlook_plugin import node_install
  class Immediate:
   def __init__(self,target,**kw):self.target=target
   def start(self):self.target()
  with patch.object(b,'_STATE',{'state':'idle','message':''}),patch.object(a,'node_executable',return_value=None),patch.object(node_install,'install',side_effect=ValueError('Synthetic download failure')) as install,patch.object(b.threading,'Thread',Immediate),patch.object(b.subprocess,'Popen') as launch:
   self.assertEqual(b.start()['state'],'failed');install.assert_called_once();launch.assert_not_called()
   self.assertFalse(a._BOB_LOCK.locked())
 def test_busy_bob_never_installs(self):
  with patch.object(a,'node_executable',return_value='/fake/node'),patch.object(b.Path,'is_file',return_value=True),patch.object(a,'_BOB_LOCK') as lock,patch.object(b.subprocess,'Popen') as launch:
   lock.acquire.return_value=False
   with self.assertRaisesRegex(ValueError,'busy'):b.start()
   launch.assert_not_called()
 def test_installer_uses_private_prefix_and_no_key(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import Mock
  class Immediate:
   def __init__(self,target,**kw):self.target=target
   def start(self):self.target()
  with tempfile.TemporaryDirectory() as d,patch.object(b,'PREFIX',Path(d)/'bob'),patch.object(b,'_STATE',{'state':'idle','message':''}),patch.object(a,'node_executable',return_value='/fake/node'),patch.object(b.Path,'is_file',return_value=True),patch.object(b,'release',return_value={'version':'2.0.2'}),patch.object(b.urllib.request,'urlopen',return_value=io.BytesIO(b'#!/bin/bash\nexit 0\n')),patch.object(b.threading,'Thread',Immediate),patch.object(b.subprocess,'Popen') as launch,patch.object(a,'bob_compatibility',return_value={'ready':True,'detail':'Bob ready'}),patch.dict(b.os.environ,{'BOB_API_KEY':'secret'}):
   launch.return_value=Mock(returncode=0)
   result=b.start();self.assertEqual(result['state'],'complete')
   self.assertNotIn('BOB_API_KEY',launch.call_args.kwargs['env'])
   self.assertEqual(launch.call_args.kwargs['env']['NPM_CONFIG_PREFIX'],str(Path(d)/'bob'))
   self.assertEqual(launch.call_args.args[0][-4:],['--pm','npm','--version','2.0.2'])
   self.assertFalse(a._BOB_LOCK.locked())
