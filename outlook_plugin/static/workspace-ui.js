'use strict';
let draftPage=1,editingSavedDraft=null;
let writingLoaded=false,writingLoading=false,discardedDraft=null;
window.writingDirty=false;
window.loadWriting=async(force=false)=>{
 if(writingLoading||(!force&&window.writingDirty))return;
 writingLoading=true;
 try{const cfg=await api('/api/config');if(force||!window.writingDirty){$('writingGuide').value=cfg.user_context.writing_style||'';if(!$('writingExamples').value)$('writingExamples').value=cfg.writing_samples||'';window.writingDirty=false;}writingLoaded=true;}catch(e){$('writingStatus').textContent=e.message;}finally{writingLoading=false;}
};
$('writingGuide').oninput=()=>{window.writingDirty=true;$('contextForm').elements.writing_style.value=$('writingGuide').value;queueContextSave('writing_style',$('writingGuide').value);$('writingStatus').textContent='Autosaving style changes…';};
$('learnWriting').onclick=()=>busy($('learnWriting'),async()=>{
 $('writingStatus').textContent='Bob is studying your examples…';$('writingGuide').readOnly=true;$('saveWriting').disabled=true;$('resetWriting').disabled=true;
 try{const result=await api('/api/writing-learn',{examples:$('writingExamples').value});$('writingGuide').value=result.guide;window.writingDirty=true;$('contextForm').elements.writing_style.value=result.guide;queueContextSave('writing_style',result.guide);$('writingStatus').textContent='Guide ready and autosaving. Edit it to refine your style.';}catch(e){$('writingStatus').textContent=e.message;throw e;}finally{$('writingGuide').readOnly=false;$('saveWriting').disabled=false;$('resetWriting').disabled=false;}
});
$('saveWriting').onclick=()=>busy($('saveWriting'),flushContext);
$('resetWriting').onclick=()=>busy($('resetWriting'),async()=>{await flushContext();if(window.contextDirty)return;await window.loadWriting(true);$('writingStatus').textContent='Loaded your saved guide.';});
window.renderDrafts=()=>{
 const root=$('draftList');root.replaceChildren();const ids=[...new Set([...Object.keys(state.drafts),...Object.keys(draftConflicts)])].filter(id=>(state.drafts[id]?.trim()||draftConflicts[id])&&((state.draftMeta[id]?.subject||'')+' '+(state.draftMeta[id]?.sender||'')+' '+(state.drafts[id]||'')).toLowerCase().includes($('draftSearch').value.trim().toLowerCase())).sort((a,b)=>(state.draftMeta[b]?.saved_at||'').localeCompare(state.draftMeta[a]?.saved_at||''));
 draftPage=Math.min(draftPage,Math.max(1,Math.ceil(ids.length/20)));listPager('draftPages',ids.length,draftPage,20,page=>{draftPage=page;window.renderDrafts();$('draftPages').scrollIntoView({block:'nearest'});});
 if(discardedDraft){const undo=text('button','Undo last discard');undo.onclick=()=>{const d=discardedDraft;state.drafts[d.id]=d.body;state.draftMeta[d.id]=d.meta;state.intents[d.id]=d.intent;discardedDraft=null;persistDrafts();window.renderDrafts();};root.append(undo);}
 if(!ids.length)root.append(text('p',$('draftSearch').value?'No matching drafts. Try another search.':'No saved replies yet. Open a message in Mail to write or generate a draft.','empty'));
 for(const id of ids.slice((draftPage-1)*20,draftPage*20)){const meta=state.draftMeta[id]||{};const card=text('article','','workspace-card draft-card');card.append(text('h3',meta.subject||'Saved reply'),text('p',meta.sender||'','muted small'),text('p',(state.drafts[id]||'').slice(0,240)+((state.drafts[id]||'').length>240?'…':''),'draft-preview'));const buttons=text('div','','actions');const open=text('button','Edit draft','primary');open.onclick=()=>openSavedDraft(id);const copy=text('button','Copy draft');copy.onclick=()=>copyRichDraft(state.drafts[id],meta.html).then(()=>notice('Draft copied.')).catch(()=>notice('Clipboard unavailable. Open the reply and copy the text manually.'));const remove=text('button','Discard');remove.onclick=()=>{discardedDraft={id,body:state.drafts[id],meta,intent:state.intents[id]||''};delete state.drafts[id];delete state.intents[id];delete state.draftMeta[id];persistDrafts();window.renderDrafts();};if(draftConflicts[id]){const saved=draftConflicts[id];const warning=text('div','','draft-conflict');warning.append(text('strong','Another saved version exists'),text('p',saved.missing?'No saved version exists on this Mac. Save this version to keep your recovered draft.':saved.deleted?'This draft was discarded in another window.':saved.text.slice(0,500)));const keep=text('button','Save this version instead');keep.onclick=()=>{draftRevisions[id]=saved.revision;delete draftConflicts[id];persistDrafts();flushDrafts();window.renderDrafts();};const useSaved=text('button','Use saved version');useSaved.onclick=()=>{useDiskDraft(id,saved);delete draftDirty[id];delete draftConflicts[id];storeBrowserDrafts();window.renderDrafts();};warning.append(keep,useSaved);card.append(warning);}buttons.append(open,copy,remove);card.append(buttons);root.append(card);}
};
window.loadWorkspaceSettings=async()=>{
 refreshSetup();loadStorageStatus();$('startAtLogin').disabled=true;$('connectionDetails').textContent='Checking local connections…';
 try{const startup=await api('/api/startup');$('startAtLogin').checked=startup.enabled;$('startAtLogin').disabled=!startup.supported;const s=await api('/api/status');$('connectionDetails').textContent=`Version ${s.version} · Bob Shell ${s.bob_installed?'installed':'not found'} · API key ${s.bob_configured?'saved (use Test Bob connection to verify)':'needed'} · ${s.message_count??0} cached emails, ${s.full_body_count??0} full bodies.`;}catch(e){$('connectionDetails').textContent=e.message;}
};
$('startAtLogin').onchange=async()=>{const enabled=$('startAtLogin').checked;$('startAtLogin').disabled=true;try{await api('/api/startup',{enabled});$('startupStatus').textContent=enabled?'Will start in the background at your next login.':'Automatic startup disabled for future logins.';}catch(e){$('startAtLogin').checked=!enabled;$('startupStatus').textContent=e.message;}finally{$('startAtLogin').disabled=false;}};
$('downloadBackup').onclick=()=>busy($('downloadBackup'),async()=>{await window.flushWorkspace();const data=await api('/api/backup');data.browser_drafts={drafts:state.drafts,intents:state.intents,meta:state.draftMeta};if(window.webkit?.messageHandlers?.saveBackup){window.webkit.messageHandlers.saveBackup.postMessage(JSON.stringify(data,null,2));return;}const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=`outlook-assistant-backup-${new Date().toISOString().slice(0,10)}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('startupStatus').textContent='Backup download requested. Your Bob API key is not included.';});

window.refreshSetup=async function refreshSetup(){try{const result=await api('/api/setup');const root=$('setupChecks');root.replaceChildren();for(const c of result.checks){const item=text('div','','setup-check');item.append(text('strong',(c.ready?'✓ ':'○ ')+c.label),text('p',c.detail,'muted small'));if(!c.ready&&['bob','node'].includes(c.id)){const link=text('a','Install IBM Bob Shell','feedback-link');link.href='https://bob.ibm.com/docs/shell/getting-started/install-and-setup';link.target='_blank';link.rel='noopener noreferrer';item.append(link);}if(!c.ready&&c.id==='identity'){const fix=text('button','Set up my identity');fix.onclick=()=>{$('settings').close();view('context');$('contextForm').elements.full_name.focus();};item.append(fix);}root.append(item);}$('setupNotice').hidden=result.ready;const missing=result.checks.filter(c=>!c.ready);const bobMissing=missing.some(c=>c.id==='bob');const identityOnly=missing.length===1&&missing[0].id==='identity';$('openSetup').dataset.target=identityOnly?'identity':'settings';$('openSetup').textContent=bobMissing?'Set up Bob Shell':identityOnly?'Add my identity':'Finish setup';$('setupSummary').textContent=bobMissing?'Bob setup needs attention. Mail and saved data remain available.':identityOnly?'Add your name and email so Bob can recognize your tasks.':missing.length+' setup steps need attention on this Mac.';}catch(e){$('setupSummary').textContent='Setup check unavailable: '+e.message;$('setupNotice').hidden=false;}}
$('openSetup').onclick=async()=>{if($('openSetup').dataset.target==='identity'){view('context');$('contextForm').elements.full_name.focus();}else {await $('settingsOpen').onclick();selectSettingsSection('setup');}};
$('recheckSetup').onclick=()=>busy($('recheckSetup'),refreshSetup);
refreshSetup();

async function loadStorageStatus(){try{const s=await api('/api/storage');$('storageLocation').textContent=`Saved data: ${s.directory} · Recovery copies: ${s.backup_directory}`;$('recoveryStatus').textContent=s.recoveries.length?s.recoveries.map(r=>r.file+': '+r.message).join(' '):'Saved data survives app shutdowns, updates, and Mac restarts. Three previous saves and up to seven daily copies are kept for recovery.';}catch(e){$('recoveryStatus').textContent=e.message;}}
let contextPending={},contextTimer=null,contextSaving=false;
window.contextDirty=false;
function queueContextSave(key,value){contextPending[key]=value;window.contextDirty=true;try{localStorage.setItem('outlook-context-pending',JSON.stringify(contextPending));}catch{notice('Local recovery storage is unavailable. Keep the app open until changes are saved.','error');}$('contextSaveStatus').textContent='Saving on this Mac…';clearTimeout(contextTimer);contextTimer=setTimeout(flushContext,600);}
async function flushContext(){if(contextSaving||!Object.keys(contextPending).length)return;contextSaving=true;state.pending++;const fields={...contextPending};try{await api('/api/context-autosave',{fields});for(const [k,v] of Object.entries(fields))if(contextPending[k]===v)delete contextPending[k];window.contextDirty=!!Object.keys(contextPending).length;window.writingDirty=window.contextDirty;try{localStorage.setItem('outlook-context-pending',JSON.stringify(contextPending));}catch{notice('Local recovery storage is unavailable. Keep the app open until changes are saved.','error');}$('contextSaveStatus').textContent='Saved on this Mac.';$('writingStatus').textContent='All changes saved';$('saveWriting').hidden=true;refreshSetup();}catch(e){$('contextSaveStatus').textContent='Not saved to disk: '+e.message;$('writingStatus').textContent='Not saved: '+e.message;$('saveWriting').hidden=false;}finally{contextSaving=false;state.pending--;if(Object.keys(contextPending).length)contextTimer=setTimeout(flushContext,5000);}}
$('contextForm').addEventListener('input',e=>{if(e.target.name)queueContextSave(e.target.name,e.target.value);});
$('writingExamples').oninput=()=>queueContextSave('writing_samples',$('writingExamples').value);
try{contextPending=JSON.parse(localStorage.getItem('outlook-context-pending')||'{}');if(Object.keys(contextPending).length){window.contextDirty=true;flushContext();}}catch{}
window.nativeBackupDone=ok=>{$('startupStatus').textContent=ok?'Backup saved. Your Bob API key is not included.':'Backup was not saved.';};
window.flushWorkspace=async()=>{
 document.activeElement?.blur();
 const until=Date.now()+10000;
 while((draftSaving||contextSaving||window.settingsSaving)&&Date.now()<until)await new Promise(resolve=>setTimeout(resolve,50));
 if(draftSaving||contextSaving||window.settingsSaving)throw Error('Saving is still in progress. Please try again.');
 if($('taskEditor').open&&taskEditor?.origin!=='saved'&&$('editTaskText').value.trim())throw Error('Add your new task or close its editor before quitting.');
 if($('projectEditor').open&&!editingProject&&$('projectName').value.trim())throw Error('Create your new project or close its editor before quitting.');
 for(const flush of [window.flushTaskEdits,window.flushTaskProgress,window.flushProjectEdits,window.flushAgentEdits,window.flushSettingsEdits,window.flushMailExclusions,window.flushScanSettings])if(flush&&await flush()===false)throw Error('Some changes could not be saved. Keep the app open and retry.');
 do{clearTimeout(draftTimer);clearTimeout(contextTimer);await flushDrafts();await flushContext();}while((Object.keys(draftDirty).some(id=>!draftConflicts[id])||window.contextDirty)&&Date.now()<until);
 if(Object.keys(draftDirty).length||Object.keys(draftConflicts).length||window.contextDirty||Object.keys(contactDrafts).length||state.pending)throw Error('Some changes still need saving. Review the save status before quitting.');
 return true;
};
let settingsPending={},settingsTimer,settingsPromise=null;
function queueSettingsField(id,key){const value=$(id).value;if(id==='key'&&!value.trim())return;settingsPending[key]=value;$('settingsStatus').textContent='Saving…';clearTimeout(settingsTimer);settingsTimer=setTimeout(()=>window.flushSettingsEdits(),600);}
window.flushSettingsEdits=async()=>{
 clearTimeout(settingsTimer);if(settingsPromise){if(!await settingsPromise)return false;return window.flushSettingsEdits();}
 if(!Object.keys(settingsPending).length)return true;
 window.settingsSaving=true;
 settingsPromise=(async()=>{try{while(Object.keys(settingsPending).length){const values={...settingsPending};await api('/api/config',values);for(const [key,value] of Object.entries(values))if(settingsPending[key]===value)delete settingsPending[key];if(values.bob_api_key&&$('key').value===values.bob_api_key)$('key').value='';}$('settingsStatus').textContent='All changes saved';refreshBobStatus();refreshSetup();return true;}catch(e){$('settingsStatus').textContent='Not saved: '+e.message;return false;}finally{window.settingsSaving=false;}})();
 try{return await settingsPromise;}finally{settingsPromise=null;}
};
for(const [id,key] of [['key','bob_api_key'],['keyName','bob_key_name'],['team','bob_team_id'],['profile','outlook_profile']])$(id).addEventListener(id==='key'||id==='profile'?'change':'input',()=>queueSettingsField(id,key));

let usageLoading=false;
function storageSize(value){const units=['B','KB','MB','GB','TB'];let index=0;while(value>=1024&&index<units.length-1){value/=1024;index++;}return value.toLocaleString(undefined,{maximumFractionDigits:1})+' '+units[index];}
window.loadUsage=async()=>{
 if(usageLoading)return;usageLoading=true;
 try{const data=await api('/api/usage');renderQuickUsage(data);const root=$('usageSummary');root.replaceChildren();
 const grid=text('div','','usage-grid');
 for(const [label,bucket] of [['Today (UTC)',data.today],['This month (UTC)',data.month],['Since tracking started',data.total]]){const card=text('article','','workspace-card');card.append(text('h3',label),text('strong',bucket.requests+' Bob requests'),text('p',bucket.succeeded+' succeeded · '+bucket.failed+' failed','muted small'),text('p',bucket.reported_units.toLocaleString(undefined,{maximumFractionDigits:6})+' Bobcoins reported'),text('p',bucket.unreported+' requests without reported usage','muted small'));for(const [field,title] of [['input_tokens','Input tokens'],['output_tokens','Output tokens'],['cache_read_tokens','Cached tokens read'],['cache_write_tokens','Cached tokens written']]){const reports=bucket[field+'_reports']||0;card.append(text('p',title+': '+(reports?bucket[field].toLocaleString()+' ('+reports+'/'+bucket.requests+' requests reported)':'Unavailable'),'muted small'));}grid.append(card);}root.append(grid,text('p','Bobcoins measure Bob consumption, not a dollar charge or your remaining account balance. Your IBM plan determines billing. Missing cost or token data is unknown, not free. Totals cover only this app on this Mac. Cached tokens may overlap input tokens; do not add them together.','muted small'));
 $('usageStatus').textContent=(data.started_at?'Tracking since '+date(data.started_at,true)+'.':'Tracking begins with your next Bob request; earlier activity cannot be reconstructed.')+(data.tracking_error?' A recent request could not be recorded. Totals may be incomplete.':'');
 const disk=$('usageStorage');disk.replaceChildren(text('h3',storageSize(data.storage.total_bytes)+' saved by this app'),text('p',storageSize(data.storage.free_bytes)+' available on this disk','muted'));
 for(const item of data.storage.items){const row=text('div','','usage-storage-row');row.append(text('span',item.name),text('strong',storageSize(item.bytes)));disk.append(row);}
 }catch(e){$('usageStatus').textContent='Could not read usage: '+e.message;}finally{usageLoading=false;}
};
$('refreshUsage').onclick=()=>window.loadUsage();
setInterval(()=>{if(document.querySelector('.view.active')?.id==='usage'&&!document.hidden)window.loadUsage();},30000);

$('draftSearch').oninput=()=>{draftPage=1;window.renderDrafts();};
function openSavedDraft(id){
 editingSavedDraft=id;$('savedDraftTitle').textContent=state.draftMeta[id]?.subject||'Edit saved draft';
 const editor=richEditor(state.drafts[id]||'',state.draftMeta[id]?.html||'',()=>{state.drafts[id]=editor.box.innerText;state.draftMeta[id]={...state.draftMeta[id],html:cleanEmailHTML(editor.box.innerHTML),saved_at:new Date().toISOString()};persistDrafts();});
 $('savedDraftContent').replaceChildren(editor.wrapper);$('savedDraftStatus').textContent=draftDirty[id]?'Saving on this Mac…':'Saved on this Mac.';$('savedDraftEditor').showModal();
}
$('closeSavedDraft').onclick=async()=>{await flushDrafts();$('savedDraftEditor').close();window.renderDrafts();};
$('savedDraftEditor').addEventListener('close',()=>window.renderDrafts());
$('copySavedDraft').onclick=()=>busy($('copySavedDraft'),async()=>{await copyRichDraft(state.drafts[editingSavedDraft]||'',state.draftMeta[editingSavedDraft]?.html);notice('Draft copied. Paste it into Outlook and review before sending.');});

let quickUsageLoading=false;
function renderQuickUsage(data){
 const today=data.today,partial=today.unreported>0||data.tracking_error;
 const total=today.reported_units.toLocaleString(undefined,{maximumFractionDigits:0});
 const summary=today.requests===0?'No usage today':today.unreported===today.requests?'Usage unreported':total+' Bobcoins'+(partial?' · Partial':'');
 $('usageQuick').textContent='Today (UTC) · '+summary;
 $('usageQuick').title='Today (UTC) · '+today.requests+' requests · '+today.unreported+' without reported usage. '+(data.tracking_error?'Some usage could not be recorded. ':'')+'This app on this Mac only. Click for tokens and usage details.';
 $('usageQuick').setAttribute('aria-label',summary+'. '+$('usageQuick').title);
}
window.refreshQuickUsage=async()=>{if(quickUsageLoading)return;quickUsageLoading=true;try{renderQuickUsage(await api('/api/usage'));}catch{$('usageQuick').textContent='Usage unavailable';$('usageQuick').title='Could not load usage. Click to retry in Usage.';}finally{quickUsageLoading=false;}};
$('usageQuick').onclick=()=>view('usage');
window.refreshQuickUsage();
setInterval(()=>{if(!document.hidden&&document.querySelector('.view.active')?.id!=='usage')window.refreshQuickUsage();},30000);
