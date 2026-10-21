import json
import re
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch, Mock
from http.server import ThreadingHTTPServer
from outlook_plugin import config, usage
from outlook_plugin.ai_agent import BobAIAgent
from outlook_plugin.local_store import LocalStoreBridge
from outlook_plugin.app_server import AppRequestHandler

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.patch=patch.object(config,'CONFIG_PATH',Path(self.tmp.name)/'config.json');self.patch.start();self.addCleanup(self.patch.stop)
        self.usage_patch=patch.object(usage,'USAGE_FILE',Path(self.tmp.name)/'usage.json');self.usage_patch.start();self.addCleanup(self.usage_patch.stop)
    def test_context_preserves_secret_and_private_permissions(self):
        config.update_config({'bob_api_key':'secret'})
        config.update_config({'user_context':{'role':'Engineer'}})
        self.assertEqual(config.read_config()['bob_api_key'],'secret')
        self.assertEqual(config.CONFIG_PATH.stat().st_mode&0o777,0o600)
    @patch('outlook_plugin.ai_agent.bob_compatibility',return_value={'ready':True})
    @patch('outlook_plugin.ai_agent.node_executable',return_value='/tmp/node')
    @patch('outlook_plugin.ai_agent.bob_executable',return_value='/tmp/bob')
    @patch('outlook_plugin.ai_agent.subprocess.run')
    def test_bob_uses_stdin_environment_and_no_tools(self,run,exe,node,compatibility):
        run.return_value=Mock(returncode=0,stdout=json.dumps({'status':'success','last_message':'Real answer','stats':{'session_costs':.1}}))
        agent=BobAIAgent('secret');self.assertEqual(agent._call_llm('private content'),'Real answer')
        args,kw=run.call_args;self.assertNotIn('secret',' '.join(args[0]));self.assertNotIn('private content',' '.join(args[0]));self.assertEqual(kw['env']['BOB_API_KEY'],'secret');self.assertIn('private content',kw['input']);self.assertIn('--disable-tool-groups',args[0]);self.assertNotIn('--max-cost',args[0])
        run.return_value=Mock(returncode=1,stdout='bad',stderr='')
        with self.assertRaises(RuntimeError):agent._call_llm('test')
    def test_cache_search_pagination_and_body_details(self):
        rows=[{'id':str(i),'folder_id':'8','folder':'Inbox','folder_kind':'inbox','read':'unread' if i%2 else 'read','body':'needle' if i==3 else 'text','subject':'x'} for i in range(7)]
        b=LocalStoreBridge()
        with patch.object(b,'_load',return_value={'rows':rows}):
            self.assertEqual([m['id'] for m in b.get_emails(limit=2,offset=2)],['2','3'])
            self.assertEqual([m['id'] for m in b.get_emails(search_term='needle')],['3'])
            self.assertEqual(len(b.get_emails(unread_only=True)),3)
            self.assertNotIn('body',b.get_emails()[0]);self.assertEqual(b.get_email_details('3')['body'],'needle')
    @patch('outlook_plugin.app_server.profiles',return_value=[])
    def test_http_secret_redaction_and_cross_origin_block(self,_profiles):
        config.update_config({'bob_api_key':'secret'})
        server=ThreadingHTTPServer(('127.0.0.1',0),AppRequestHandler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base=f'http://127.0.0.1:{server.server_port}'
        with urllib.request.urlopen(base+'/api/config') as r:
            self.assertNotIn('secret',r.read().decode());self.assertIsNone(r.headers.get('Access-Control-Allow-Origin'))
        with urllib.request.urlopen(base+'/',timeout=5) as r:
            html=r.read().decode()
        for script in re.findall(r'<script src="([^"]+)"',html):
            with urllib.request.urlopen(base+script,timeout=5) as r:
                self.assertTrue(r.read(),script)
        with urllib.request.urlopen(base+'/onboarding-ui.js',timeout=5) as r:
            self.assertIn('walkthrough',r.read().decode())
        with urllib.request.urlopen(base+'/api/onboarding',timeout=5) as r:
            self.assertEqual(json.load(r)['step'],0)
        req=urllib.request.Request(base+'/api/config',headers={'Origin':'https://evil.example'})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,403)
        req=urllib.request.Request(base+'/api/config',data=b'{}',headers={'Content-Type':'text/plain'})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,415)

class UpdateTests(unittest.TestCase):
    def test_dirty_checkout_is_never_overwritten(self):
        from outlook_plugin.updater import check_and_apply_update
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'.git').mkdir()
            with patch('outlook_plugin.updater.subprocess.run',return_value=Mock(stdout=' M README.md',returncode=0)) as run:
                updated,msg=check_and_apply_update(d,True)
                self.assertFalse(updated);self.assertIn('Local changes',msg);self.assertEqual(run.call_count,1)
    def test_reject_tar_traversal(self):
        import io,tarfile
        from outlook_plugin.updater import check_and_apply_update
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'outlook_plugin').mkdir();(root/'outlook_plugin/app_server.py').write_text('original')
            def download(url,path):
                with tarfile.open(path,'w:gz') as tar:
                    info=tarfile.TarInfo('../../escape');info.size=3;tar.addfile(info,io.BytesIO(b'bad'))
            with patch('outlook_plugin.updater.get_latest_github_commit',return_value='abc'),patch('outlook_plugin.updater.urllib.request.urlretrieve',side_effect=download):
                updated,msg=check_and_apply_update(d,True)
            self.assertFalse(updated);self.assertIn('Unsafe',msg);self.assertEqual((root/'outlook_plugin/app_server.py').read_text(),'original')

    def test_reject_older_download(self):
        import io,tarfile
        from outlook_plugin.updater import check_and_apply_update
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'outlook_plugin').mkdir();(root/'outlook_plugin/app_server.py').write_text('original')
            def download(url,path):
                with tarfile.open(path,'w:gz') as tar:
                    for name,content in [('app_server.py',b'old'),('__init__.py',b'__version__ = "1.2.0"')]:
                        info=tarfile.TarInfo('release/outlook_plugin/'+name);info.size=len(content);tar.addfile(info,io.BytesIO(content))
            with patch('outlook_plugin.updater.get_latest_github_commit',return_value='abc'),patch('outlook_plugin.updater.urllib.request.urlretrieve',side_effect=download):
                updated,msg=check_and_apply_update(d,True)
            self.assertFalse(updated);self.assertIn('older',msg);self.assertEqual((root/'outlook_plugin/app_server.py').read_text(),'original')

    def test_large_formatted_draft_can_save_without_raising_other_limits(self):
        from outlook_plugin import drafts
        with tempfile.TemporaryDirectory() as tmp,patch.object(drafts,'DRAFTS_FILE',Path(tmp)/'drafts.json'):
            server=ThreadingHTTPServer(('127.0.0.1',0),AppRequestHandler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                base='http://127.0.0.1:'+str(server.server_port)
                body=json.dumps({'changes':[{'id':'large','revision':0,'text':'x'*40000,'html':'<p>'+'x'*110000+'</p>'}]}).encode()
                request=urllib.request.Request(base+'/api/drafts',data=body,headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(request) as response:self.assertEqual(response.status,200)
                self.assertEqual(len(drafts.load()['entries']['large']['html']),110007)
                request=urllib.request.Request(base+'/api/config',data=body,headers={'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request)
                self.assertEqual(caught.exception.code,413)
            finally:server.shutdown();server.server_close();thread.join()
