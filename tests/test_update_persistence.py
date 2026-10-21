import io,json,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import updater,__version__

class UpdatePersistenceTests(unittest.TestCase):
    def download(self,url,path):
        with tarfile.open(path,'w:gz') as tar:
            for name,content in [('app_server.py',b'new code'),('__init__.py',('__version__ = "'+__version__+'"').encode())]:
                item=tarfile.TarInfo('release/outlook_plugin/'+name);item.size=len(content);tar.addfile(item,io.BytesIO(content))
    def test_update_preserves_workspace_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'outlook_plugin').mkdir();(root/'outlook_plugin/app_server.py').write_text('old code')
            saved={name:b'{"keep":"my data"}' for name in ['tasks.json','config.json','drafts.json']}
            for name,body in saved.items():(root/name).write_bytes(body)
            with patch.object(updater,'get_latest_github_commit',return_value='test-commit'),patch.object(updater.urllib.request,'urlretrieve',side_effect=self.download):
                updated,message=updater.check_and_apply_update(root,True)
            self.assertTrue(updated,message);self.assertEqual((root/'outlook_plugin/app_server.py').read_text(),'new code')
            for name,body in saved.items():self.assertEqual((root/name).read_bytes(),body)
    def test_failed_package_swap_rolls_back_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'outlook_plugin').mkdir();(root/'outlook_plugin/app_server.py').write_text('old code')
            real=updater.os.replace
            def replace(src,dst):
                if Path(src).name=='.outlook_plugin_next':raise OSError('simulated interrupted update')
                return real(src,dst)
            with patch.object(updater,'get_latest_github_commit',return_value='test-commit'),patch.object(updater.urllib.request,'urlretrieve',side_effect=self.download),patch.object(updater.os,'replace',side_effect=replace):
                updated,message=updater.check_and_apply_update(root,True)
            self.assertFalse(updated);self.assertEqual((root/'outlook_plugin/app_server.py').read_text(),'old code')
