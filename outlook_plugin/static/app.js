'use strict';
const $=id=>document.getElementById(id);
let contactPage=1,contactPageSize=20;
let contactData=[],contactDrafts={},contactsLoading=false,contactsLoaded=false;
const state={folder:'all',unread:false,search:'',emails:[],selected:null,offset:0,request:0,instance:null,busy:false,drafts:{},draftMeta:{},intents:{},lastList:'',pending:0};
let draftHydrated=false,draftHydrating=false,draftSaving=false,draftTimer=null,draftDirty={},draftRevisions={},draftBaseline={},draftConflicts={};
function draftPayload(id){const meta=state.draftMeta[id]||{};return {html:meta.html||'',text:state.drafts[id]||'',intent:state.intents[id]||'',subject:meta.subject||'',sender:meta.sender||'',deleted:!(id in state.drafts)&&!(id in state.intents)};}
function draftStatus(message){for(const id of ['draftSaveStatus','replySaveStatus','savedDraftStatus']){const target=$(id);if(target)target.textContent=message;}}
function storeBrowserDrafts(){try{localStorage.setItem('outlook-reply-drafts',JSON.stringify({drafts:state.drafts,intents:state.intents,meta:state.draftMeta,revisions:draftRevisions,dirty:draftDirty}));}catch{notice('Browser recovery storage is unavailable. Wait for “Saved on this Mac” before leaving.');}}
function persistDrafts(){
 const ids=new Set([...Object.keys(state.drafts),...Object.keys(state.intents),...Object.keys(draftBaseline)]);
 for(const id of ids){const value=JSON.stringify(draftPayload(id));if(value!==draftBaseline[id]){draftDirty[id]=value;draftBaseline[id]=value;}}
 storeBrowserDrafts();if(draftHydrated){draftStatus('Saving drafts on this Mac…');clearTimeout(draftTimer);draftTimer=setTimeout(flushDrafts,500);}
}
try{const saved=JSON.parse(localStorage.getItem('outlook-reply-drafts')||'{}');state.drafts=saved.drafts||{};state.intents=saved.intents||{};state.draftMeta=saved.meta||{};draftRevisions=saved.revisions||{};draftDirty=saved.dirty||{};for(const id of new Set([...Object.keys(state.drafts),...Object.keys(state.intents)]))draftBaseline[id]=JSON.stringify(draftPayload(id));}catch{}
function useDiskDraft(id,item){draftRevisions[id]=item.revision;if(item.deleted){delete state.drafts[id];delete state.intents[id];delete state.draftMeta[id];}else{state.drafts[id]=item.text;state.intents[id]=item.intent;state.draftMeta[id]={html:item.html||'',subject:item.subject,sender:item.sender,saved_at:item.updated_at};}draftBaseline[id]=JSON.stringify(draftPayload(id));}
async function hydrateDrafts(){if(draftHydrating)return;draftHydrating=true;try{const result=await api('/api/drafts');for(const [id,item] of Object.entries(result.entries)){
 if(draftDirty[id])continue;
 if(!draftRevisions[id]&&state.drafts[id]?.trim()&&state.drafts[id]!==item.text){draftDirty[id]=JSON.stringify(draftPayload(id));draftConflicts[id]=item;continue;}
 useDiskDraft(id,item);
 }for(const id of new Set([...Object.keys(state.drafts),...Object.keys(state.intents)])){if(!result.entries[id])draftDirty[id]=JSON.stringify(draftPayload(id));}
 draftHydrated=true;storeBrowserDrafts();await flushDrafts();if(document.querySelector('.view.active')?.id==='drafts')window.renderDrafts?.();
 }catch(e){draftStatus('Not saved to disk: '+e.message+'. Browser recovery copy retained.');}finally{draftHydrating=false;}}
async function flushDrafts(){if(!draftHydrated||draftSaving)return;const ids=[];let batchBytes=20;for(const id of Object.keys(draftDirty).filter(id=>!draftConflicts[id]).slice(0,25)){const bytes=new TextEncoder().encode(draftDirty[id]).length+new TextEncoder().encode(id).length+100;if(ids.length&&batchBytes+bytes>1000000)break;ids.push(id);batchBytes+=bytes;}if(!ids.length){draftStatus(Object.keys(draftConflicts).length?'Some drafts have conflicting saved versions. Review them below.':'Saved on this Mac.');return;}draftSaving=true;state.pending++;
 const snapshot=Object.fromEntries(ids.map(id=>[id,draftDirty[id]]));
 try{const result=await api('/api/drafts',{changes:ids.map(id=>({id,revision:draftRevisions[id]||0,...JSON.parse(snapshot[id])}))});for(const [id,revision] of Object.entries(result.saved)){draftRevisions[id]=revision;if(draftDirty[id]===snapshot[id])delete draftDirty[id];}
 if(result.conflicts.length){const current=await api('/api/drafts');for(const id of result.conflicts)draftConflicts[id]=current.entries[id]||{revision:0,deleted:true,text:'',missing:true};if(document.querySelector('.view.active')?.id==='drafts')window.renderDrafts?.();}
 storeBrowserDrafts();draftStatus(Object.keys(draftConflicts).length?'Draft conflict: review both versions in Drafts.':Object.keys(draftDirty).length?'Saving remaining drafts…':'Saved on this Mac.');
 }catch(e){draftStatus('Not saved to disk: '+e.message+'. Browser recovery copy retained; retrying.');}
 finally{draftSaving=false;state.pending--;if(Object.keys(draftDirty).some(id=>!draftConflicts[id])){clearTimeout(draftTimer);draftTimer=setTimeout(flushDrafts,5000);}}
}
const text=(tag,value,cls)=>{const e=document.createElement(tag);e.textContent=value??'';if(cls)e.className=cls;return e;};
function notice(value,kind='info'){document.querySelectorAll('[data-notice-action]').forEach(e=>e.remove());$('noticeText').textContent=value;$('notice').hidden=!value;$('notice').dataset.kind=kind;$('notice').setAttribute('role',kind==='error'?'alert':'status');}
$('dismissNotice').onclick=()=>notice('');
async function api(path,data){let r;try{r=await fetch(path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}catch{throw Error('Cannot connect to Outlook Assistant. Reopen the Mac app, then try Sync now again. Your saved data is still on this Mac.');}const value=await r.json();if(!r.ok)throw Error(value.error||'Request failed');return value;}
async function busy(button,fn){const old=button.textContent;state.pending++;button.disabled=true;button.textContent='Working…';try{await fn();}catch(e){notice(e.message,'error');}finally{state.pending--;button.disabled=false;button.textContent=old;}}
function view(id){window.assistantViewChanged?.(id);const selected=document.querySelector('[data-view="'+id+'"]');const more=selected?.closest('details');if(more)more.open=!matchMedia('(max-width:760px)').matches;else $('moreNavigation').open=false;$('folderLabel').hidden=id!=='mail';$('folders').hidden=id!=='mail';document.querySelectorAll('.view').forEach(e=>e.classList.toggle('active',e.id===id));document.querySelectorAll('[data-view]').forEach(e=>e.classList.toggle('active',e.dataset.view===id));$('pageTitle').textContent=({'task-review':'Tasks to review',drafts:'Drafts',writing:'Writing style',chat:'Assistant',mail:'Mail',calendar:'Calendar',tasks:'Tasks',briefing:'Briefing',context:'My context',contacts:'Contacts & companies',projects:'Projects',usage:'Usage'})[id];if(id==='calendar')window.loadCalendar?.();if(id==='projects')window.loadProjects?.();if(id==='drafts'){window.renderDrafts?.();hydrateDrafts();}if(id==='writing')window.loadWriting?.();if(id==='usage')window.loadUsage?.();if(id==='tasks'||id==='task-review'){window.openTaskPage?.(id);tasks().catch(e=>notice(e.message));}if(id==='contacts')loadContacts().catch(e=>notice(e.message));}
function date(v,full=false){const d=new Date(v);return isNaN(d)?'Date unavailable':d.toLocaleString(undefined,full?{dateStyle:'medium',timeStyle:'short'}:{month:'short',day:'numeric'});}
async function loadEmails(append=false,preserveCount=false){
 const serial=++state.request;const count=preserveCount?Math.max(50,state.emails.length):50;const start=append?state.emails.length:0;let rows=[],lastBatch=[];
 $('mailCount').textContent='Loading…';
 for(let offset=start;offset<start+count;offset+=200){const limit=Math.min(200,start+count-offset);lastBatch=await api('/api/emails?'+new URLSearchParams({folder:state.folder,limit,offset,unread_only:state.unread,search:state.search}));if(serial!==state.request)return;rows.push(...lastBatch);if(lastBatch.length<limit)break;}
 state.emails=append?[...new Map([...state.emails,...rows].map(m=>[m.id,m])).values()]:rows;$('more').hidden=rows.length<count;renderEmails();
}

function renderEmails(){const root=$('messages');$('mailCount').textContent=state.emails.length+' shown';const fingerprint=JSON.stringify([state.emails,state.selected]);if(fingerprint===state.lastList)return;state.lastList=fingerprint;const scroll=root.parentElement.scrollTop;root.replaceChildren();if(!state.emails.length){root.append(text('p','No matching cached messages.','empty'));return;}for(const m of state.emails){const b=text('button','',`message ${m.id===state.selected?'active':''} ${m.read==='unread'?'unread':''}`);const top=text('div','','sender');top.append(text('strong',m.from?.name||m.from?.address||m.sender),text('time',date(m.received_time)));b.append(top,text('div',m.subject||'(No subject)','subject'),text('div',m.preview||'Open to read the cached message.','preview'));b.onclick=()=>selectEmail(m.id).catch(e=>notice(e.message));root.append(b);}root.parentElement.scrollTop=scroll;}
async function selectEmail(id){state.selected=id;renderEmails();$('mail').classList.add('detail-open');$('reader').setAttribute('aria-busy','true');let m;try{m=await api('/api/email?'+new URLSearchParams({id}));}catch(e){if(state.selected===id){$('reader').removeAttribute('aria-busy');$('mail').classList.remove('detail-open');}throw e;}if(state.selected!==id)return;const root=$('reader');root.removeAttribute('aria-busy');root.scrollTop=0;const back=text('button','Back to messages','back-to-list');back.onclick=()=>{$('mail').classList.remove('detail-open');};root.replaceChildren(back,text('h2',m.subject||'(No subject)'));const meta=text('div','','reader-meta');const name=m.from?.name||m.sender?.replace(/\s*<[^>]*>/g,'').trim()||m.from?.address||m.sender||'?';const detail=text('div','','meta-detail');detail.append(text('strong',name),text('small',m.sender),text('small',date(m.received_time,true)));meta.append(text('span',(name.match(/[\p{L}\p{N}]+/gu)||['?']).slice(0,2).map(x=>x[0]).join('').toUpperCase(),'avatar'),detail);root.append(meta,text('div',m.body_complete?'Cached body · Read-only':'Preview only · The full body is not available in this cache','body-state'),text('div',m.body||m.preview||'No readable content cached.','body-text'));const body=root.querySelector('.body-text');renderEmailLinks(body,body.textContent);if(body.textContent.length>2200){const full=body.textContent;renderEmailLinks(body,full.slice(0,2200)+'…');const expand=text('button','Show full message','expand-message');let expanded=false;expand.onclick=()=>{expanded=!expanded;renderEmailLinks(body,expanded?full:full.slice(0,2200)+'…');expand.textContent=expanded?'Show less':'Show full message';};root.append(expand);}const draft=text('section','','draft');draft.append(text('h3','Draft a reply'));const controls=text('div','','actions');const intent=document.createElement('input');intent.placeholder='Give Bob a short instruction for your reply';intent.setAttribute('aria-label','Reply instructions');intent.value=state.intents[id]||'';intent.oninput=()=>{state.intents[id]=intent.value;persistDrafts();};const generate=text('button','Generate with Bob','primary');const rememberDraft=()=>{state.drafts[id]=box.innerText;state.draftMeta[id]={html:cleanEmailHTML(box.innerHTML),subject:m.subject||'(No subject)',sender:m.sender||'',saved_at:new Date().toISOString()};persistDrafts();};const editor=richEditor(state.drafts[id]||'',state.draftMeta[id]?.html||'',rememberDraft);const box=editor.box;const copy=text('button','Copy reply');copy.onclick=()=>copyRichDraft(box.innerText,box.innerHTML).then(()=>notice('Reply copied.')).catch(()=>notice('Select the draft text and copy it manually.'));generate.onclick=()=>busy(generate,async()=>{const r=await api('/api/smart-reply',{email_id:id,intent:intent.value||'Draft a helpful reply. Do not invent commitments or availability.'});editor.setHTML(r.reply);rememberDraft();notice('Draft generated with IBM Bob. Review before using.');});controls.append(intent,generate);const saveStatus=text('p','Draft changes save automatically.','muted small');saveStatus.id='replySaveStatus';draft.append(controls,editor.wrapper,copy,saveStatus,text('p','Sends this message and your saved context to IBM Bob. Nothing is sent as an email.','muted small'));root.append(draft);if(window.mountEmailTasks)window.mountEmailTasks(id,root);}
async function folders(){const rows=await api('/api/folders');const root=$('folders');root.replaceChildren();$('mobileFolder').replaceChildren();for(const f of [{id:'all',name:'All mail'},...rows]){const option=text('option',f.name);option.value=f.id;option.selected=state.folder===f.id;$('mobileFolder').append(option);const b=text('button','',state.folder===f.id?'active':'');b.append(text('span',f.name),text('small',f.total_messages??''));b.onclick=async()=>{state.folder=f.id;$('mail').classList.remove('detail-open');view('mail');try{await Promise.all([folders(),loadEmails()]);}catch(e){notice(e.message,'error');}};root.append(b);}}
let outlookWarningDismissed=false;
function renderOutlookStatus(running){
 if(running===true)outlookWarningDismissed=false;
 $('outlookWarning').hidden=running!==false||outlookWarningDismissed;
 $('outlookStatus').textContent=running===true?'Outlook open':running===false?'Outlook closed · Cached mail':'Outlook status unavailable';
 $('outlookStatus').dataset.state=running===true?'open':running===false?'closed':'unknown';
 $('outlookStatus').title=running===true?'Outlook is running. New mail appears here after Outlook downloads it.':running===false?'Existing mail remains available. Open Outlook to download new messages.':'The app could not determine whether Outlook is running.';
}
$('dismissOutlookWarning').onclick=()=>{outlookWarningDismissed=true;$('outlookWarning').hidden=true;};
$('openOutlook').onclick=()=>busy($('openOutlook'),async()=>{await api('/api/open-outlook',{});notice('Opening Outlook. New mail will appear after it syncs.');await health();});
async function status(){const s=await api('/api/status');renderOutlookStatus(s.outlook_running);refreshBobStatus();$('version').textContent='Version '+s.version;for(const [id,template] of [['suggestFeature','feature.yml'],['reportProblem','bug.yml']])$(id).href='https://github.com/brettscharm/outlook-assistant/issues/new?'+new URLSearchParams({template,version:s.version});$('freshness').textContent=`Local Outlook cache · ${s.message_count??0} messages · ${s.full_body_count??0} cached bodies · ${s.preview_count??0} previews${s.excluded_count?' · '+s.excluded_count+' excluded':''} · Checked ${new Date().toLocaleTimeString()}`;if(s.partial)notice('Some cache records could not be read. Available messages are shown; coverage is incomplete.');return s;}
let lastSuccessfulSync=null;
function syncTimeLabel(){return lastSuccessfulSync?'Last synced '+lastSuccessfulSync.toLocaleTimeString([],{hour:'numeric',minute:'2-digit',second:'2-digit'}):'Not synced yet';}
async function sync(force=false,automatic=false){if(state.busy)return;state.busy=true;$('sync').disabled=true;$('sync').textContent='Syncing…';$('sync').setAttribute('aria-busy','true');try{const result=force?await api('/api/sync',{automatic}):null;const s=await status();if(s.mail_error)throw new Error(s.mail_error);await Promise.all([folders(),loadEmails(false,true)]);lastSuccessfulSync=Number.isFinite(s.checked)&&s.checked>0?new Date(s.checked*1000):new Date();$('syncTime').textContent=syncTimeLabel();$('syncTime').title='Last successful read of the local Outlook cache: '+lastSuccessfulSync.toLocaleString()+'. Outlook handles downloading new mail.';await refreshSyncedViews();if(result?.tasks){$('syncTime').textContent=syncTimeLabel()+' · '+(result.tasks.state==='running'?'Checking tasks…':result.tasks.state==='busy'?'Bob busy':result.tasks.state==='paused'?'Tasks paused':'Task setup needed');if(!automatic)notice(result.tasks.message,result.tasks.state==='setup'?'error':'');}}catch(e){notice(e.message,'error');$('freshness').textContent='Local cache unavailable · '+e.message;$('syncTime').textContent='Sync failed · '+syncTimeLabel();}finally{state.busy=false;$('sync').disabled=false;$('sync').textContent='Sync now';$('sync').removeAttribute('aria-busy');}}

async function context(){const c=await api('/api/config');for(const key of ['full_name','email_addresses','role','accounts','priorities','writing_style'])$('contextForm').elements[key].value=c.user_context[key]||'';try{const pending=JSON.parse(localStorage.getItem('outlook-context-pending')||'{}');for(const [k,v] of Object.entries(pending)){if($('contextForm').elements[k])$('contextForm').elements[k].value=v;}}catch{}accountListCount();}
async function tasks(){if(window.loadTaskWorkspace)return window.loadTaskWorkspace();}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>view(b.dataset.view));
$('sync').onclick=()=>sync(true);
$('more').onclick=()=>busy($('more'),()=>loadEmails(true));
for(const [id,unread] of [['all',false],['unread',true]])$(id).onclick=()=>{state.unread=unread;$('mail').classList.remove('detail-open');$('all').classList.toggle('selected',!unread);$('unread').classList.toggle('selected',unread);loadEmails().catch(e=>notice(e.message));};
let searchTimer;$('search').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{state.search=$('search').value;$('mail').classList.remove('detail-open');loadEmails().catch(e=>notice(e.message));},250);};
$('contextForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{await api('/api/config',{user_context:Object.fromEntries(new FormData(e.target))});notice('Your context is saved on this Mac.');await tasks();window.refreshSetup?.();});};
document.querySelectorAll('[data-task]').forEach(form=>form.onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{await api('/api/tasks',{action:'add',type:form.dataset.task,text:form.elements.text.value});form.reset();await tasks();});});
$('generateBriefing').onclick=()=>busy($('generateBriefing'),async()=>{$('briefingText').textContent='Bob is reviewing your unread previews and context…';try{const b=await api('/api/briefing',{});$('briefingText').textContent=b.summary;}catch(e){$('briefingText').textContent='Briefing could not be generated.';throw e;}});
$('settingsOpen').onclick=async()=>{try{const c=await api('/api/config');$('key').value='';$('keyName').value=c.bob_key_name||'';$('excludedDomains').value=(c.excluded_domains||[]).join('\n');$('domainSaveStatus').textContent='Changes save automatically.';$('team').value=c.bob_team_id;$('profile').replaceChildren();for(const p of c.profiles){const option=text('option',p.split('/').pop());option.value=p;option.selected=p===c.outlook_profile;$('profile').append(option);}$('settingsStatus').textContent=c.bob_configured?'A Bob API key is saved.':'Add your IBM Bob API key.';selectSettingsSection('bob');$('settings').showModal();refreshBobStatus();window.loadWorkspaceSettings?.();}catch(e){notice(e.message,'error');}};
$('settingsClose').onclick=()=>$('settings').close();
$('settingsForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{await api('/api/config',{bob_api_key:$('key').value,bob_key_name:$('keyName').value,bob_team_id:$('team').value,outlook_profile:$('profile').value,excluded_domains:$('excludedDomains').value});$('key').value='';await refreshMailFilters();$('settingsStatus').textContent='Settings saved.';});};
$('testBob').onclick=()=>busy($('testBob'),async()=>{try{await api('/api/config',{bob_api_key:$('key').value,bob_key_name:$('keyName').value,bob_team_id:$('team').value});$('key').value='';$('settingsStatus').textContent='Testing Bob connection…';const r=await api('/api/bob-test',{});$('settingsStatus').textContent=r.connected?'Connected to IBM Bob. Test request succeeded.':'Bob replied, but the connection check was unexpected.';}catch(e){$('settingsStatus').textContent=e.message;throw e;}finally{await refreshBobStatus();}});

let serviceWarningDismissed=false;
$('dismissServiceWarning').onclick=()=>{serviceWarningDismissed=true;$('serviceWarning').hidden=true;};
async function health(){try{const h=await api('/api/health');renderOutlookStatus(h.outlook_running);$('serviceWarning').hidden=true;serviceWarningDismissed=false;if(state.instance&&state.instance!==h.instance&&($('settings').open||$('taskProgress')?.open||$('projectEditor')?.open||window.agentDirty||$('laneEditor').open||$('taskEditor').open||$('savedDraftEditor').open||state.pending||window.writingDirty||window.contextDirty))return;if(state.instance&&state.instance!==h.instance){if(Object.values(state.drafts).some(Boolean)){sessionStorage.setItem('drafts',JSON.stringify(state.drafts));}sessionStorage.setItem('outlook-ui',JSON.stringify({view:document.querySelector('.view.active')?.id,search:state.search,folder:state.folder,unread:state.unread,context:Object.fromEntries(new FormData($('contextForm'))),intents:state.intents,scanDraft:window.getTaskScanDraft?.()}));location.reload();}state.instance=h.instance;}catch{ $('serviceWarning').hidden=serviceWarningDismissed; }}
try{Object.assign(state.drafts,JSON.parse(sessionStorage.getItem('drafts')||'{}'));sessionStorage.removeItem('drafts');persistDrafts();}catch{}
let restored=null;try{restored=JSON.parse(sessionStorage.getItem('outlook-ui')||'null');sessionStorage.removeItem('outlook-ui');if(restored){state.folder=restored.folder;state.search=restored.search;state.unread=restored.unread;state.intents=restored.intents||{};$('search').value=state.search;$('all').classList.toggle('selected',!state.unread);$('unread').classList.toggle('selected',state.unread);view(restored.view||'mail');}}catch{}
hydrateDrafts();
Promise.all([sync(),context().then(()=>{if(restored?.context)for(const [k,v] of Object.entries(restored.context))$('contextForm').elements[k].value=v;accountListCount();}),tasks(),health()]).catch(e=>notice(e.message));setInterval(health,4000);setInterval(()=>{if(!document.hidden&&!$('settings').open)sync();},60000);

$('mobileFolder').onchange=()=>{state.folder=$('mobileFolder').value;$('mail').classList.remove('detail-open');Promise.all([folders(),loadEmails()]).catch(e=>notice(e.message));};

let lastInteraction=Date.now(),updateChecking=false;
for(const event of ['pointerdown','keydown','input'])document.addEventListener(event,()=>{lastInteraction=Date.now();},{passive:true});
function updateIsIdle(){return !$('taskProgress')?.open&&!window.agentDirty&&!$('projectEditor')?.open&&!window.contextDirty&&!Object.keys(draftDirty).length&&!draftSaving&&!window.writingDirty&&!$('chatQuestion')?.value.trim()&&!Object.keys(contactDrafts).length&& !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)&& !document.hidden&&!state.pending&&!state.busy&&!$('settings').open&&!$('laneEditor').open&&!$('taskEditor').open&&!$('savedDraftEditor').open&&!window.taskScanRunning&&!window.taskFormDirty&&Date.now()-lastInteraction>30000;}
async function autoUpdate(){
 if(updateChecking||!updateIsIdle())return;
 updateChecking=true;
 try{const result=await api('/api/version');if(result.update_available&&updateIsIdle()){const installed=await api('/api/update',{});if(installed.updated)notice('Update installed. Refreshing your workspace…');}}
 catch{/* Retry on the next check; offline use remains available. */}
 finally{updateChecking=false;}
}
setTimeout(autoUpdate,45000);setInterval(autoUpdate,300000);

function accountListCount(){const rows=$('accountList').value.split(/\r?\n/).filter(row=>row.trim());$('accountListCount').textContent=rows.length+' non-empty rows · '+$('accountList').value.length.toLocaleString()+' / 12,000 characters';}
$('accountList').addEventListener('input',accountListCount);
$('tidyAccounts').onclick=()=>{const rows=$('accountList').value.split(/\r?\n/).map(row=>row.trimEnd()).filter(row=>row.trim());$('accountList').value=[...new Set(rows)].join('\n');accountListCount();notice('Blank and identical rows removed. Select Save my context to keep this list.');};

async function loadContacts(force=false){
 if(contactsLoading||(!force&&contactsLoaded))return;
 contactsLoading=true;$('contactCount').textContent='Reading cached senders…';
 try{const result=await api('/api/contacts');contactData=result.groups;contactsLoaded=true;
 $('companyOptions').replaceChildren();for(const company of result.companies){const option=text('option',company);option.value=company;$('companyOptions').append(option);}renderContacts();
 }catch(e){$('contactCount').textContent='Contacts could not be loaded. Try Refresh contacts.';throw e;}finally{contactsLoading=false;}
}
function renderContacts(){
 const query=$('contactSearch').value.toLowerCase().trim();const root=$('contactGroups');root.replaceChildren();
 const matches=contactData.map(group=>{const groupMatch=(group.domain+' '+group.company).toLowerCase().includes(query);return {group,people:group.contacts.filter(p=>groupMatch||(p.name+' '+p.email).toLowerCase().includes(query)),groupMatch};}).filter(row=>row.people.length||row.groupMatch);
 const pages=Math.max(1,Math.ceil(matches.length/contactPageSize));contactPage=Math.min(Math.max(1,contactPage),pages);
 const start=(contactPage-1)*contactPageSize,end=Math.min(start+contactPageSize,matches.length);
 const total=matches.reduce((sum,row)=>sum+row.people.length,0);
 const companies=new Set(matches.map(row=>row.group.company.toLowerCase()).filter(Boolean)).size;
 $('contactCount').textContent=total+' contacts · '+companies+' linked companies · '+matches.length+' domains'+(matches.length?' · Showing '+(start+1)+'–'+end:'');
 for(const {group,people} of matches.slice(start,end)){
  const card=document.createElement('details');card.className='contact-group';card.open=!!query;
  const summary=text('summary','');summary.append(text('strong',group.company||group.domain),text('span',(group.company?group.domain+' · ':'')+people.length+' contacts','muted small'));card.append(summary);
  const form=document.createElement('form');form.className='company-link';
  const input=document.createElement('input');input.setAttribute('list','companyOptions');input.setAttribute('aria-label','Company for '+group.domain);input.placeholder='Choose or type a company';input.maxLength=200;input.value=contactDrafts[group.domain]??group.company;let companyTimer;input.oninput=()=>{contactDrafts[group.domain]=input.value;clearTimeout(companyTimer);companyTimer=setTimeout(()=>form.requestSubmit(),700);};
  const save=text('button','Save company','primary');save.type='submit';const unlink=text('button','Unlink');unlink.type='button';unlink.hidden=!group.company;
  form.onsubmit=e=>{e.preventDefault();busy(save,async()=>{await api('/api/contact-company',{domain:group.domain,company:input.value});group.company=input.value.trim();delete contactDrafts[group.domain];const header=summary.querySelector('strong');header.textContent=group.company||group.domain;summary.querySelector('span').textContent=(group.company?group.domain+' · ':'')+people.length+' contacts';unlink.hidden=!group.company;notice('Company link saved for '+group.domain+'.');});};
  unlink.onclick=()=>busy(unlink,async()=>{await api('/api/contact-company',{domain:group.domain,company:''});input.value='';group.company='';delete contactDrafts[group.domain];summary.querySelector('strong').textContent=group.domain;summary.querySelector('span').textContent=people.length+' contacts';unlink.hidden=true;notice('Company link removed.');});
  form.append(input,save,unlink);card.append(form);
  if(group.suggestion){const suggestion=text('div','','company-link');const accept=text('button','Use '+group.suggestion.company);accept.type='button';suggestion.append(text('span',group.suggestion.reason,'muted small'),accept);accept.onclick=()=>{input.value=group.suggestion.company;contactDrafts[group.domain]=input.value;form.requestSubmit();suggestion.remove();};card.append(suggestion);}
  const related=contactData.filter(g=>group.company&&g.company.toLowerCase()===group.company.toLowerCase()).map(g=>g.domain);
  if(related.length>1)card.append(text('p','Company domains: '+related.join(', '),'company-link muted small'));
  for(const person of people){const row=text('div','','contact-person');const info=text('div','','contact-person-info');info.append(text('strong',person.name),text('span',person.email,'muted small'));const mail=text('button','Search mail');mail.onclick=()=>{state.folder='all';state.unread=false;state.search=person.email;$('search').value=person.email;$('all').classList.add('selected');$('unread').classList.remove('selected');$('mail').classList.remove('detail-open');view('mail');Promise.all([folders(),loadEmails()]).catch(e=>notice(e.message));};row.append(info,text('span',person.message_count+' messages','muted small'),mail);card.append(row);}
  root.append(card);
 }
 if(!matches.length)root.append(text('p','No matches. Try another person, company, or domain.','muted'));
 renderContactPagination(pages,matches.length);
}
$('contactSearch').oninput=()=>{contactPage=1;renderContacts();};
$('refreshContacts').onclick=()=>busy($('refreshContacts'),()=>loadContacts(true));

$('companyDomainsForm').onsubmit=e=>{e.preventDefault();const form=e.currentTarget;const button=form.querySelector('button');busy(button,async()=>{
 const domains=$('linkCompanyDomains').value.split(/[\s,;]+/).filter(Boolean);
 const company=$('linkCompanyName').value.trim();if(!company)throw new Error('Enter a company name.');
 await api('/api/contact-company',{domains,company});form.reset();await loadContacts(true);notice('Domains linked to '+company+'.');
});};

function renderContactPagination(pages,count){
 for(const id of ['contactPaginationTop','contactPaginationBottom']){
  const nav=$(id);nav.replaceChildren();
  const change=page=>{contactPage=page;renderContacts();$('contacts').scrollTop=0;$(id==='contactPaginationBottom'?'contactPaginationTop':id).querySelector('select').focus();};
  for(const [label,page,disabled] of [['First',1,contactPage===1],['Previous',contactPage-1,contactPage===1]]){const button=text('button',label);button.disabled=disabled;button.onclick=()=>change(page);nav.append(button);}
  const select=document.createElement('select');select.setAttribute('aria-label','Contacts page');for(let page=1;page<=pages;page++)select.append(new Option('Page '+page+' of '+pages,String(page)));select.value=String(contactPage);select.disabled=!count;select.onchange=()=>change(Number(select.value));nav.append(select);
  for(const [label,page,disabled] of [['Next',contactPage+1,contactPage===pages],['Last',pages,contactPage===pages]]){const button=text('button',label);button.disabled=disabled;button.onclick=()=>change(page);nav.append(button);}
 }
}
$('contactPageSize').onchange=()=>{contactPageSize=Number($('contactPageSize').value);contactPage=1;renderContacts();};

let dismissedBobIssue='',currentBobIssue='',currentBobMessage='';
try{dismissedBobIssue=sessionStorage.getItem('dismissed-bob-issue')||'';}catch{}
async function refreshBobStatus(){
 try{const result=await api('/api/bob-status');const indicator=$('bobStatus');indicator.dataset.state=result.state;
 $('bobKeyLabel').textContent=result.key_name;
 const labels={connected:'Working',unchecked:'Not tested',missing:'No key',revoked:'Revoked',expired:'Expired',invalid:'Rejected',permission:'Access denied',quota:'Usage limit',rate_limit:'Rate limited',network:'Connection failed',error:'Request failed'};
 $('bobStateLabel').textContent=labels[result.state]||result.title;
 const detail=result.message+(result.checked_at?' Last checked: '+date(result.checked_at,true)+'.':'');indicator.title=detail;indicator.setAttribute('aria-label',result.key_name+': '+(labels[result.state]||result.title)+'. '+detail+' Open Settings.');
 if(['connected','unchecked','missing'].includes(result.state)&&$('noticeText').textContent===currentBobMessage)notice('');
 currentBobIssue=result.state+':'+(result.checked_at||'');currentBobMessage=result.message;
 const problem=!['connected','unchecked','missing'].includes(result.state);$('bobWarning').hidden=!problem||currentBobIssue===dismissedBobIssue;
 $('bobWarningTitle').textContent=result.title+' · '+result.key_name;$('bobWarningMessage').textContent=result.message;
 $('bobConnectionStatus').textContent=detail;
 }catch{$('bobStatus').dataset.state='network';$('bobStateLabel').textContent='Status unavailable';$('bobStatus').title='Cannot reach the app to check the last Bob result.';}
}
$('fixBobKey').onclick=()=>$('settingsOpen').click();
$('bobStatus').onclick=()=>$('settingsOpen').click();
$('dismissBobWarning').onclick=()=>{dismissedBobIssue=currentBobIssue;try{sessionStorage.setItem('dismissed-bob-issue',dismissedBobIssue);}catch{}$('bobWarning').hidden=true;if($('noticeText').textContent===currentBobMessage)notice('');};
setInterval(()=>{if(!document.hidden)refreshBobStatus();},4000);

function listPager(id,total,page,size,change){
 const root=$(id);root.replaceChildren();const pages=Math.max(1,Math.ceil(total/size));root.hidden=total===0;
 const previous=text('button','Previous');previous.disabled=page<=1;previous.onclick=()=>change(page-1);
 const next=text('button','Next');next.disabled=page>=pages;next.onclick=()=>change(page+1);
 const select=document.createElement('select');select.setAttribute('aria-label',id==='taskPages'?'Task page':'Draft page');
 for(let n=1;n<=pages;n++)select.append(new Option('Page '+n+' of '+pages,String(n)));select.value=String(page);select.onchange=()=>change(Number(select.value));
 root.append(text('span',total?((page-1)*size+1)+'–'+Math.min(total,page*size)+' of '+total:'No results','muted small'),previous,select,next);
}

async function refreshMailFilters(){state.selected=null;state.folder='all';$('mail').classList.remove('detail-open');$('reader').replaceChildren(text('p','Select a message to read it.','empty'));contactsLoaded=false;await sync();if($('contacts').classList.contains('active'))await loadContacts();}
async function saveExcludedDomains(){try{await api('/api/config',{excluded_domains:$('excludedDomains').value});$('domainSaveStatus').textContent='Exclusions saved on this Mac.';await refreshMailFilters();}catch(e){$('domainSaveStatus').textContent='Not saved: '+e.message;notice(e.message,'error');}};

let excludedSaveTimer;$('excludedDomains').oninput=()=>{clearTimeout(excludedSaveTimer);$('domainSaveStatus').textContent='Saving…';excludedSaveTimer=setTimeout(saveExcludedDomains,700);};$('excludedDomains').onchange=()=>{clearTimeout(excludedSaveTimer);saveExcludedDomains();};

$('findInvitations').onclick=()=>{state.folder='all';state.unread=false;state.search='meeting';$('search').value='meeting';$('all').classList.add('selected');$('unread').classList.remove('selected');view('mail');Promise.all([folders(),loadEmails()]).catch(e=>notice(e.message,'error'));};
document.addEventListener('keydown',event=>{if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='f'&&!document.querySelector('dialog[open]')){const active=document.querySelector('.view.active')?.id;const id={mail:'search',tasks:'boardSearch','task-review':'taskSearch',contacts:'contactSearch',drafts:'draftSearch'}[active];if(id){event.preventDefault();$(id).focus();$(id).select();}}});

function selectSettingsSection(name){
 document.querySelectorAll('[data-settings-panel]').forEach(p=>p.hidden=p.dataset.settingsPanel!==name);
 document.querySelectorAll('[data-settings-section]').forEach(b=>{if(b.dataset.settingsSection===name)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
 document.querySelector('.settings-content').scrollTop=0;
}
document.querySelectorAll('[data-settings-section]').forEach(b=>b.onclick=()=>selectSettingsSection(b.dataset.settingsSection));

// Wake timers may be suspended by macOS. Refresh immediately after a long gap,
// or when returning to the app, while keeping background discovery preferences.
let lastWakeTick=Date.now(),lastResumeSync=0;
function resumeWorkspace(){
 if(document.hidden||state.busy||Date.now()-lastResumeSync<30000)return;
 lastResumeSync=Date.now();sync(true,true);
}
setInterval(()=>{const now=Date.now();if(now-lastWakeTick>45000)resumeWorkspace();lastWakeTick=now;},15000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)resumeWorkspace();});
window.addEventListener('focus',resumeWorkspace);

async function refreshSyncedViews(){
 contactsLoaded=false;
 const jobs=[window.loadTaskWorkspace?.(),window.refreshSetup?.(),refreshBobStatus(),window.refreshQuickUsage?.()];
 const active=document.querySelector('.view.active')?.id;
 // Company labels and draft text may be mid-edit; never replace the active editor.
 if(active==='contacts'&&!$('contacts').contains(document.activeElement))jobs.push(loadContacts(true));
 if(active==='drafts'&&!$('savedDraftEditor').open)jobs.push(hydrateDrafts());
 if(active==='usage')jobs.push(window.loadUsage?.());
 if(active==='chat')jobs.push(window.refreshChatHistory?.());
 const results=await Promise.allSettled(jobs);
 const failed=results.find(r=>r.status==='rejected');
 if(failed)notice('Mail synced, but a view could not refresh: '+failed.reason.message,'error');
}

function renderEmailLinks(element,content){
 element.replaceChildren();const value=String(content||'');const pattern=/https?:\/\/[^\s<>"\u0000-\u001f]+/gi;let previous=0;
 for(const match of value.matchAll(pattern)){
  let link=match[0].replace(/[.,;:!?]+$/,'');
  while(link.endsWith(')')&&(link.match(/\)/g)||[]).length>(link.match(/\(/g)||[]).length)link=link.slice(0,-1);
  element.append(document.createTextNode(value.slice(previous,match.index)));
  try{const url=new URL(link);if(!['http:','https:'].includes(url.protocol))throw Error();const a=text('a',link);a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';element.append(a);}catch{element.append(document.createTextNode(link));}
  previous=match.index+link.length;
 }element.append(document.createTextNode(value.slice(previous)));
}
