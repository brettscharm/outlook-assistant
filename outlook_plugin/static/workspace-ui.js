'use strict';
let writingLoaded=false,writingLoading=false,discardedDraft=null;
window.writingDirty=false;
window.loadWriting=async(force=false)=>{
 if(writingLoading||(!force&&window.writingDirty))return;
 writingLoading=true;
 try{const cfg=await api('/api/config');if(force||!window.writingDirty){$('writingGuide').value=cfg.user_context.writing_style||'';window.writingDirty=false;}writingLoaded=true;}catch(e){$('writingStatus').textContent=e.message;}finally{writingLoading=false;}
};
$('writingGuide').oninput=()=>{window.writingDirty=true;$('writingStatus').textContent='Unsaved style changes.';};
$('learnWriting').onclick=()=>busy($('learnWriting'),async()=>{
 $('writingStatus').textContent='Bob is studying your examples…';$('writingGuide').readOnly=true;$('saveWriting').disabled=true;$('resetWriting').disabled=true;
 try{const result=await api('/api/writing-learn',{examples:$('writingExamples').value});$('writingGuide').value=result.guide;window.writingDirty=true;$('writingStatus').textContent='Guide ready. Review it, make any changes, then save.';}catch(e){$('writingStatus').textContent=e.message;throw e;}finally{$('writingGuide').readOnly=false;$('saveWriting').disabled=false;$('resetWriting').disabled=false;}
});
$('saveWriting').onclick=()=>busy($('saveWriting'),async()=>{await api('/api/writing-style',{guide:$('writingGuide').value});$('contextForm').elements.writing_style.value=$('writingGuide').value;window.writingDirty=false;$('writingStatus').textContent='Saved on this Mac. Future drafts will use this guide.';});
$('resetWriting').onclick=()=>busy($('resetWriting'),async()=>{await window.loadWriting(true);$('writingStatus').textContent='Loaded your saved guide.';});
window.renderDrafts=()=>{
 const root=$('draftList');root.replaceChildren();const ids=Object.keys(state.drafts).filter(id=>state.drafts[id]?.trim()).sort((a,b)=>(state.draftMeta[b]?.saved_at||'').localeCompare(state.draftMeta[a]?.saved_at||''));
 if(discardedDraft){const undo=text('button','Undo last discard');undo.onclick=()=>{const d=discardedDraft;state.drafts[d.id]=d.body;state.draftMeta[d.id]=d.meta;discardedDraft=null;persistDrafts();window.renderDrafts();};root.append(undo);}
 if(!ids.length)root.append(text('p','No saved replies yet. Open a message in Mail to write or generate a draft.','empty'));
 for(const id of ids){const meta=state.draftMeta[id]||{};const card=text('article','','workspace-card draft-card');card.append(text('h3',meta.subject||'Saved reply'),text('p',meta.sender||'','muted small'),text('p',state.drafts[id].slice(0,240)+(state.drafts[id].length>240?'…':''),'draft-preview'));const buttons=text('div','','actions');const open=text('button','Continue reply','primary');open.onclick=()=>{view('mail');selectEmail(id).catch(e=>notice(e.message+' Your saved draft is still available in Drafts.'));};const copy=text('button','Copy draft');copy.onclick=()=>navigator.clipboard.writeText(state.drafts[id]).then(()=>notice('Draft copied.')).catch(()=>notice('Clipboard unavailable. Open the reply and copy the text manually.'));const remove=text('button','Discard');remove.onclick=()=>{discardedDraft={id,body:state.drafts[id],meta};delete state.drafts[id];delete state.draftMeta[id];persistDrafts();window.renderDrafts();};buttons.append(open,copy,remove);card.append(buttons);root.append(card);}
};
window.loadWorkspaceSettings=async()=>{
 $('startAtLogin').disabled=true;$('connectionDetails').textContent='Checking local connections…';
 try{const startup=await api('/api/startup');$('startAtLogin').checked=startup.enabled;$('startAtLogin').disabled=!startup.supported;const s=await api('/api/status');$('connectionDetails').textContent=`Version ${s.version} · Bob Shell ${s.bob_installed?'installed':'not found'} · API key ${s.bob_configured?'saved (use Test Bob connection to verify)':'needed'} · ${s.message_count??0} cached emails, ${s.full_body_count??0} full bodies.`;}catch(e){$('connectionDetails').textContent=e.message;}
};
$('startAtLogin').onchange=async()=>{const enabled=$('startAtLogin').checked;$('startAtLogin').disabled=true;try{await api('/api/startup',{enabled});$('startupStatus').textContent=enabled?'Will start in the background at your next login.':'Automatic startup disabled for future logins.';}catch(e){$('startAtLogin').checked=!enabled;$('startupStatus').textContent=e.message;}finally{$('startAtLogin').disabled=false;}};
$('downloadBackup').onclick=()=>busy($('downloadBackup'),async()=>{const data=await api('/api/backup');data.browser_drafts={drafts:state.drafts,intents:state.intents,meta:state.draftMeta};const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=`outlook-assistant-backup-${new Date().toISOString().slice(0,10)}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('startupStatus').textContent='Backup download requested. Your Bob API key is not included.';});
