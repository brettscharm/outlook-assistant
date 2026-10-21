"""Loopback-only local UI. Mail is read-only; Bob runs only on explicit requests."""
import http.server
import json
import os
import sys
import threading
import urllib.parse
import uuid
from pathlib import Path
from . import __version__
from .ai_agent import BobAIAgent, bob_executable, get_bob_api_key, save_bob_api_key, _BOB_LOCK
from .config import read_config, update_config
from .engine import OutlookEngine
from .local_store import profiles, LocalStoreBridge
from .contacts import group_contacts, link_company, link_companies, suggest_company, set_favorite
from .tasks import board_lanes, save_board_lanes, move_task, load_tasks, add_task, toggle_task, delete_task, edit_task
from . import task_files, meeting_mail, calendar_cache, mail_archive, task_progress, bob_install, projects, ai_profiles, task_workflow, email_chat, workspace, setup_check, drafts, storage, usage, bob_status, outlook_status, onboarding
from .updater import check_and_apply_update

PORT = 8484
STATIC_DIR = Path(__file__).parent/'static'
INSTANCE = uuid.uuid4().hex


class AppRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.engine = OutlookEngine()
        self.engine.local_only = True
        self.ai = BobAIAgent()
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, *args):
        pass  # Do not log subjects or search queries.

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        super().end_headers()

    def _send_json(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _allowed(self):
        port = self.server.server_port
        hosts = {f'localhost:{port}',f'127.0.0.1:{port}'}
        origin = self.headers.get('Origin')
        if self.headers.get('Host') not in hosts or (origin and origin not in {'http://'+h for h in hosts}) or self.headers.get('Sec-Fetch-Site')=='cross-site':
            self._send_json({'error':'Only the local app may access this endpoint.'},403)
            return False
        return True

    def do_OPTIONS(self):
        self._send_json({'error':'Cross-origin access is disabled.'},403)

    def do_GET(self):
        if not self._allowed(): return
        try:
            self._get()
        except (ValueError, TypeError) as exc:
            self._send_json({'error':str(exc)},400)
        except Exception as exc:
            self._send_json({'error':str(exc)},503)

    def _get(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        q = urllib.parse.parse_qs(parsed.query)
        if path=='/api/bob-install':return self._send_json(bob_install.snapshot())
        if path=='/api/bob-release':
            from .ai_agent import bob_compatibility
            release=bob_install.release();installed=bob_compatibility().get('version','')
            available=bool(release['version'] and installed and tuple(map(int,release['version'].split('.')))>tuple(map(int,installed.split('.'))))
            return self._send_json({**release,'installed':installed,'update_available':available})
        if path=='/api/task-files':return self._send_json(task_files.listing(q.get('kind',[''])[0],q.get('owner',[''])[0]))
        if path=='/api/projects':return self._send_json(projects.list_projects())
        if path=='/api/ai-profiles':return self._send_json({'profiles':ai_profiles.profiles(),'activity':ai_profiles.activity()})
        if path=='/api/drafts': return self._send_json(drafts.load())
        if path=='/api/bob-status': return self._send_json(bob_status.current(get_bob_api_key()))
        if path=='/api/onboarding': return self._send_json(onboarding.current())
        if path=='/api/usage': return self._send_json(usage.snapshot())
        if path=='/api/storage': return self._send_json({'directory':str(drafts.DRAFTS_FILE.parent),'backup_directory':str(storage.backups(drafts.DRAFTS_FILE)[0].parent),'recoveries':storage.RECOVERIES})
        if path=='/api/source-status':return self._send_json(outlook_status.sources())
        if path=='/api/setup': return self._send_json(setup_check.check())
        if path=='/api/startup': return self._send_json(workspace.startup_status())
        if path=='/api/backup': return self._send_json(workspace.export_data())
        if path=='/api/mcp-config':
            from .mcp_server import connection_info
            return self._send_json(connection_info())
        if path=='/api/task-review':
            return self._send_json(task_workflow.snapshot(q.get('email_id',[None])[0]))
        if path=='/api/health':
            return self._send_json({'version':__version__,'instance':INSTANCE,'outlook_running':outlook_status.running(),'teams_running':outlook_status.teams_running()})
        if path=='/api/status':
            try: status = self.engine.get_status()
            except (RuntimeError, OSError) as exc: status = {'active_backend':'local_cache','mail_error':str(exc)}
            status.update(outlook_running=outlook_status.running(),bob_configured=bool(get_bob_api_key()),bob_installed=bool(bob_executable()),version=__version__)
            return self._send_json(status)
        if path=='/api/version':
            available,msg=check_and_apply_update(auto_pull=False)
            return self._send_json({'version':__version__,'update_available':available,'message':msg})
        if path=='/api/config':
            cfg=read_config()
            return self._send_json({'bob_configured':bool(get_bob_api_key()),'bob_installed':bool(bob_executable()),
                                   'bob_team_id':cfg.get('bob_team_id',''),'bob_key_name':cfg.get('bob_key_name',''),'user_context':cfg.get('user_context',{}),'writing_samples':cfg.get('writing_samples',''),
                                   'excluded_domains':cfg.get('excluded_domains',[]),'outlook_profile':cfg.get('outlook_profile',''),'profiles':[str(p) for p in profiles()]})
        if path=='/api/contacts':
            backend=self.engine.get_active_backend()
            if not isinstance(backend,LocalStoreBridge): raise RuntimeError('Contacts currently requires the local Outlook cache reader.')
            cfg=read_config()
            groups=group_contacts(backend.get_emails(folder='all',limit=None),cfg.get('domain_companies',{}))
            accounts=cfg.get('user_context',{}).get('accounts','')
            companies=sorted(set([row.split('\t')[0].strip() for row in accounts.splitlines() if row.strip()]+list(cfg.get('domain_companies',{}).values())),key=str.casefold)
            for group in groups:
                group['suggestion']=suggest_company(group['domain'],companies,cfg.get('domain_companies',{})) if not group['company'] else None
            return self._send_json({'groups':groups,'companies':companies,'favorites':cfg.get('favorite_companies',[]),'source':'Cached email senders'})
        if path=='/api/folders': return self._send_json(self.engine.list_folders())
        if path=='/api/accounts': return self._send_json(self.engine.list_accounts())
        if path=='/api/task-lanes': return self._send_json(board_lanes())
        if path=='/api/archive':return self._send_json(mail_archive.status())
        if path=='/api/tasks': return self._send_json(load_tasks())
        if path=='/api/emails':
            backend=self.engine.get_active_backend()
            args=dict(folder=q.get('folder',['all'])[0],limit=max(1,min(200,int(q.get('limit',['50'])[0]))),
                      unread_only=q.get('unread_only',['false'])[0]=='true',search_term=q.get('search',[None])[0])
            if isinstance(backend,LocalStoreBridge): args['offset']=max(0,int(q.get('offset',['0'])[0]))
            return self._send_json(backend.get_emails(**args))
        if path=='/api/email':
            item=self.engine.get_email_details(q.get('id',[''])[0])
            return self._send_json(item if item else {'error':'Message not found.'},200 if item else 404)
        if path=='/api/meeting-mail':return self._send_json(meeting_mail.discover(self.engine))
        if path=='/api/calendar':
            ranged='from' in q or 'to' in q
            data=calendar_cache.snapshot(force=q.get('refresh',[''])[0]=='1',start=q.get('from',[None])[0],end=q.get('to',[None])[0])
            from .tasks import refresh_meeting_deadlines
            if not ranged:refresh_meeting_deadlines(data['events'])
            return self._send_json(data)
        if path.startswith('/api/'):
            return self._send_json({'error':'Unknown endpoint.'},404)
        if path not in ('/','/index.html','/app.js','/tasks-ui.js','/review-bulk.js','/task-files.js','/workspace-ui.js','/organize-ui.js','/calendar-ui.js','/onboarding-ui.js','/rich-editor.js','/style.css','/app-icon.png'):
            return self._send_json({'error':'Not found.'},404)
        return super().do_GET()

    def do_POST(self):
        if not self._allowed(): return
        try:
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self._send_json({'error':'JSON required.'},415)
            size=int(self.headers.get('Content-Length','0'))
            limit=36_000_000 if urllib.parse.urlparse(self.path).path=='/api/task-files' else 1500000 if urllib.parse.urlparse(self.path).path in ('/api/drafts','/api/mcp') else 100000
            if size<0 or size>limit: return self._send_json({'error':'Request too large.'},413)
            data=json.loads(self.rfile.read(size) or '{}')
            if not isinstance(data,dict): raise ValueError('Expected an object.')
            self._post(urllib.parse.urlparse(self.path).path,data)
        except (ValueError,TypeError) as exc:
            self._send_json({'error':str(exc)},400)
        except Exception as exc:
            self._send_json({'error':str(exc)},503)

    def _post(self,path,data):
        if path=='/api/onboarding': return self._send_json(onboarding.save(data))
        if path=='/api/task-files':return self._send_json(task_files.change(data))
        if path=='/api/bob-install':return self._send_json(bob_install.start())
        if path=='/api/projects':return self._send_json(projects.save(data))
        if path=='/api/ai-profiles':return self._send_json(ai_profiles.save(data))
        if path=='/api/ai-profile-test':
            key=data.get('id');sample=data.get('sample','')
            if key not in ai_profiles.DEFAULTS or not isinstance(sample,str) or not 1<=len(sample.strip())<=6000:raise ValueError('Choose an assistant and enter sample text (up to 6,000 characters).')
            return self._send_json({'answer':self.ai._call_llm('Demonstrate this assistant on the user-provided sample below. Return a readable example only; do not execute changes or invent source facts.\n'+sample,profile=key)})
        if path=='/api/context-autosave':
            fields=data.get('fields',{})
            if not isinstance(fields,dict) or any(k not in ('full_name','email_addresses','role','accounts','priorities','writing_style','writing_samples') or not isinstance(v,str) or len(v)>(24000 if k=='writing_samples' else 12000) for k,v in fields.items()): raise ValueError('Invalid context fields.')
            from .config import _LOCK as config_lock
            with config_lock:
                cfg=read_config();ctx=dict(cfg.get('user_context',{}));ctx.update({k:v for k,v in fields.items() if k!='writing_samples'})
                changes={'user_context':ctx}
                if 'writing_samples' in fields:changes['writing_samples']=fields['writing_samples']
                update_config(changes)
            return self._send_json({'saved':True})
        if path=='/api/drafts': return self._send_json(drafts.save_changes(data))
        if path=='/api/startup': return self._send_json(workspace.set_startup(data.get('enabled')))
        if path=='/api/writing-learn': return self._send_json(workspace.learn_style(self.ai,data.get('examples')))
        if path=='/api/writing-style': return self._send_json(workspace.save_style(data.get('guide')))
        if path=='/api/mcp':
            from .mcp_server import dispatch
            return self._send_json(dispatch(data,self.engine))
        if path=='/api/task-scan-settings':return self._send_json(task_workflow.settings(data))
        if path=='/api/task-scan':return self._send_json(task_workflow.start(self.engine,data,email_id=data.get('email_id')))
        if path=='/api/task-scan-stop':return self._send_json(task_workflow.stop())
        if path=='/api/task-email-draft':
            from .task_communication import open_draft
            return self._send_json(open_draft(data))
        if path=='/api/task-review':return self._send_json(task_workflow.action(data))
        if path=='/api/contact-favorite':return self._send_json({'favorites':set_favorite(data.get('domain',''),data.get('starred'))})
        if path=='/api/contact-company':
            links=link_companies(data['domains'],data.get('company','')) if 'domains' in data else link_company(data.get('domain',''),data.get('company',''))
            return self._send_json({'saved':True,'domain_companies':links})
        if path=='/api/config':
            changes={}
            if 'excluded_domains' in data:
                from .mail_filters import normalize_domains
                changes['excluded_domains']=normalize_domains(data['excluded_domains'])
            if data.get('bob_api_key','').strip(): changes['bob_api_key']=data['bob_api_key'].strip()
            if 'bob_key_name' in data:
                if not isinstance(data['bob_key_name'],str) or len(data['bob_key_name'].strip())>80: raise ValueError('Use a key name of up to 80 characters.')
                changes['bob_key_name']=data['bob_key_name'].strip()
            if 'bob_team_id' in data: changes['bob_team_id']=str(data['bob_team_id']).strip()[:200]
            if 'outlook_profile' in data:
                profile=data['outlook_profile']
                if profile and profile not in [str(p) for p in profiles()]: raise ValueError('Unknown Outlook profile.')
                changes['outlook_profile']=profile
            if 'user_context' in data:
                ctx=data['user_context']
                if not isinstance(ctx,dict): raise ValueError('Invalid context.')
                changes['user_context']={k:str(ctx.get(k,''))[:12000] for k in ('full_name','email_addresses','role','accounts','priorities','writing_style')}
            update_config(changes)
            return self._send_json({'status':'saved'})
        if path=='/api/open-teams':return self._send_json(outlook_status.open_teams())
        if path=='/api/open-outlook':return self._send_json(outlook_status.open_outlook())
        if path=='/api/bob-test':
            answer=self.ai._call_llm('Respond with exactly BOB_CONNECTION_OK.')
            return self._send_json({'connected':answer.strip()=='BOB_CONNECTION_OK','usage':self.ai.last_usage})
        if path=='/api/sync':
            backend=self.engine.get_active_backend()
            if isinstance(backend,LocalStoreBridge): backend._load(force=True)
            from .tasks import refresh_meeting_deadlines
            calendar_error=''
            if any(t.get('deadline',{}).get('kind')=='meeting' for rows in load_tasks().values() for t in rows if not t.get('completed')):
                try:refresh_meeting_deadlines(calendar_cache.snapshot(force=True)['events'])
                except Exception:calendar_error='Mail synced, but meeting deadlines could not refresh. Open Calendar to retry.'
            return self._send_json({'status':'synced','calendar_error':calendar_error,'tasks':task_workflow.sync_tasks(self.engine,automatic=data.get('automatic') is True)})
        if path=='/api/briefing':
            emails=self.engine.get_emails(folder='inbox',limit=40,unread_only=True)
            briefing=self.ai.generate_ai_briefing([],emails)
            briefing['usage']=self.ai.last_usage
            return self._send_json(briefing)
        if path=='/api/smart-reply':
            email=self.engine.get_email_details(str(data.get('email_id','')))
            if not email: return self._send_json({'error':'Message not found.'},404)
            reply=self.ai.draft_smart_reply(email,[],intent=str(data.get('intent','Draft a helpful reply without making commitments.'))[:3000])
            return self._send_json({'reply':reply,'usage':self.ai.last_usage})
        if path=='/api/extract-tasks':
            rows=self.engine.get_emails(folder=str(data.get('folder','inbox')),limit=30,
                search_term=str(data.get('search',''))[:500],unread_only=bool(data.get('unread',False)))
            messages=[]
            for row in rows:
                message=self.engine.get_email_details(str(row['id']))
                if message:
                    content=(message.get('body') or message.get('preview') or '')[:6000]
                    messages.append(dict(id=str(message['id']),subject=message.get('subject',''),
                        sender=message.get('sender',''),received_time=message.get('received_time',''),content=content))
            suggestions=self.ai.extract_tasks(messages)
            existing=load_tasks()
            known={(t.get('email_id'),' '.join(t['text'].lower().split())) for group in existing.values() for t in group}
            suggestions=[t for t in suggestions if (t['email_id'],' '.join(t['text'].lower().split())) not in known]
            return self._send_json({'suggestions':suggestions,'scanned':len(messages),'usage':self.ai.last_usage})
        if path=='/api/task-lanes':return self._send_json(save_board_lanes(data.get('lanes')))
        if path=='/api/archive':return self._send_json(mail_archive.archive(self.engine))
        if path=='/api/task-progress':return self._send_json(task_progress.change(str(data.get('id','')),data.get('action'),data))
        if path=='/api/task-handoff':return self._send_json(task_progress.export_task(str(data.get('id',''))))
        if path=='/api/task-import':return self._send_json(task_progress.import_task(data.get('handoff')))
        if path=='/api/tasks':
            action=data.get('action','add')
            if action=='add':
                text=str(data.get('text','')).strip()[:2000]
                if not text: raise ValueError('Enter a task.')
                source=None
                if data.get('email_id'):
                    message=self.engine.get_email_details(str(data['email_id']))
                    if not message: raise ValueError('The source email is no longer in the local cache.')
                    evidence=str(data.get('evidence',''))[:1200]
                    content=message.get('body') or message.get('preview') or ''
                    if not evidence or ' '.join(evidence.split()) not in ' '.join(content.split()):
                        raise ValueError('The supporting quote could not be verified in the source email.')
                    source=dict(email_id=str(message['id']),email_subject=message.get('subject','(No subject)'),evidence=evidence)
                due=str(data.get('due_date',''))
                if due:
                    from datetime import date
                    date.fromisoformat(due)
                tasks=add_task(data.get('type','my'),text,str(data.get('owner',''))[:200],due,source=source,description=str(data.get('description','')),source_type=data.get('source_type'),source_url=data.get('source_url',''),priority=data.get('priority','none'),project_id=data.get('project_id',''),color=data.get('color','none'),deadline=data.get('deadline'),co_owners=data.get('co_owners'))
            elif action=='edit':tasks=edit_task(str(data.get('id','')),str(data.get('text','')),str(data.get('owner','')),data.get('type','my'),str(data.get('due_date','')),description=data.get('description'),source_type=data.get('source_type'),source_url=data.get('source_url'),priority=data.get('priority'),project_id=data.get('project_id'),color=data.get('color'),deadline=data.get('deadline'),co_owners=data.get('co_owners'))
            elif action=='move':tasks=move_task(str(data.get('id','')),str(data.get('lane_id','')))
            elif action=='toggle': tasks=toggle_task(data.get('id'))
            elif action=='delete': tasks=delete_task(data.get('id'))
            else: raise ValueError('Unknown task action.')
            return self._send_json(tasks)
        if path=='/api/update':
            if mail_archive._LOCK.locked() or task_workflow.snapshot()['job']['running'] or email_chat._LOCK.locked() or _BOB_LOCK.locked():return self._send_json({'updated':False,'message':'Update deferred until the current AI work completes.'})
            updated,msg=check_and_apply_update(auto_pull=True)
            self._send_json({'updated':updated,'message':msg})
            if updated:
                self.server.restart=True
                threading.Thread(target=self.server.shutdown,daemon=True).start()
            return
        self._send_json({'error':'Unknown endpoint.'},404)


def start_app_server(port=PORT,open_browser=True):
    workspace.initialize_storage()
    server=http.server.ThreadingHTTPServer(('127.0.0.1',port),AppRequestHandler)
    server.daemon_threads=True
    server.restart=False
    scan_shutdown=threading.Event()
    scan_engine = OutlookEngine()
    scan_engine.local_only = True
    threading.Thread(target=task_workflow.scheduler,args=(scan_engine,scan_shutdown),daemon=True).start()
    print(f'Outlook Assistant: http://localhost:{port}',flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(f'http://localhost:{port}')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        scan_shutdown.set()
        server.server_close()
    if server.restart:
        args = ['--port',str(port),'--no-browser']
        if not getattr(sys,'frozen',False): args = ['-m','outlook_plugin.cli','app'] + args
        os.execv(sys.executable,[sys.executable]+args)
