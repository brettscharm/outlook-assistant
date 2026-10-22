'use strict';
let slackOffset=0,slackSerial=0,slackImportBusy=false;
window.slackImportDirty=false;
try{const saved=JSON.parse(localStorage.getItem('outlook-slack-import-draft')||'{}');for(const id of ['slackWorkspace','slackChannel','slackPaste','slackLink'])if(typeof saved[id]==='string')$(id).value=saved[id];window.slackImportDirty=!!$('slackPaste').value;}catch{}
function saveSlackImportDraft(){try{localStorage.setItem('outlook-slack-import-draft',JSON.stringify(Object.fromEntries(['slackWorkspace','slackChannel','slackPaste','slackLink'].map(id=>[id,$(id).value]))));}catch{$('slackImportStatus').textContent='Draft recovery storage is unavailable. Import before closing the app.';}}

window.loadSlack=async function(sourceId){
 if(typeof sourceId==='string'){$('slackSearch').value=sourceId;slackOffset=0;}
 const serial=++slackSerial;
 try{const result=await api('/api/slack?'+new URLSearchParams({search:$('slackSearch').value,conversation:$('slackConversation').value,offset:slackOffset}));if(serial!==slackSerial)return;
 const selected=$('slackConversation').value;$('slackConversation').replaceChildren(new Option('All conversations',''));for(const row of result.conversations)$('slackConversation').append(new Option(row.name,row.id));$('slackConversation').value=selected;
 $('slackMessages').replaceChildren();for(const row of result.items){const card=text('article','','action-card slack-message');card.append(text('h3',row.sender),text('p',row.workspace+' · '+row.channel+' · '+(row.occurred_at?date(row.occurred_at,true):'Date not provided'),'muted small'));const body=text('p','','slack-message-body');renderEmailLinks(body,row.text);card.append(body);const actions=text('div','','actions');const create=text('button','Create task');create.onclick=()=>editTask({text:'',description:row.sender+' · '+row.channel+'\n'+row.text,source_type:'slack',source_url:row.url,type:'my'},'new');actions.append(create);if(row.url){const link=text('a','Open in Slack');link.href=row.url;link.target='_blank';link.rel='noopener noreferrer';actions.append(link);}card.append(actions);$('slackMessages').append(card);}
 $('slackStatus').textContent=result.total?result.total+' imported messages':'No imported messages found.';$('slackPage').textContent=result.total?(slackOffset+1)+'–'+Math.min(slackOffset+30,result.total):'';$('slackPrevious').disabled=slackOffset===0;$('slackNext').disabled=slackOffset+30>=result.total;
 }catch(e){$('slackStatus').textContent=e.message;}
};
let slackSearchTimer;$('slackSearch').oninput=()=>{clearTimeout(slackSearchTimer);slackOffset=0;slackSearchTimer=setTimeout(()=>window.loadSlack(),250);};$('slackConversation').onchange=()=>{slackOffset=0;window.loadSlack();};$('slackPrevious').onclick=()=>{slackOffset=Math.max(0,slackOffset-30);window.loadSlack();};$('slackNext').onclick=()=>{slackOffset+=30;window.loadSlack();};
$('slackImportOpen').onclick=()=>{$('slackImportDialog').showModal();};
function closeSlackImport(){if(slackImportBusy)return;$('slackImportDialog').close();}
$('slackImportClose').onclick=closeSlackImport;$('slackImportDialog').addEventListener('cancel',e=>{e.preventDefault();closeSlackImport();});
for(const id of ['slackWorkspace','slackChannel','slackPaste','slackLink','slackFiles'])$(id).addEventListener('input',()=>{window.slackImportDirty=!!$('slackPaste').value||!!$('slackFiles').files.length;saveSlackImportDraft();});
$('slackImportSave').onclick=()=>busy($('slackImportSave'),async()=>{
 const files=[...$('slackFiles').files],paste=$('slackPaste').value;
 if(files.length&&paste.trim())throw Error('Paste text or select files, not both.');
 if(files.length>30)throw Error('Select up to 30 files at a time.');
 const batches=[];for(const file of files){if(file.size>1000000)throw Error(file.name+' exceeds 1 MB. Select a smaller daily message file.');let value;try{value=JSON.parse(await file.text());}catch{throw Error(file.name+' is not valid JSON.');}if(!Array.isArray(value))throw Error(file.name+' must contain a Slack message or users array.');batches.push(value);}
 slackImportBusy=true;$('slackImportClose').disabled=true;let added=0,updated=0,skipped=0,users=0;
 try{for(const messages of batches.length?batches:[null]){const result=await api('/api/slack-import',{workspace:$('slackWorkspace').value,channel:$('slackChannel').value,url:$('slackLink').value,text:messages?'':paste,messages});added+=result.added;updated+=result.updated;skipped+=result.skipped;users+=result.users;}
 $('slackPaste').value='';$('slackFiles').value='';window.slackImportDirty=false;saveSlackImportDraft();$('slackImportStatus').textContent=`${added} added · ${updated} updated · ${skipped} unchanged or empty${users?' · '+users+' people imported':''}`;slackOffset=0;await window.loadSlack();
 }catch(e){$('slackImportStatus').textContent='Import stopped. Earlier files remain saved; retrying will not duplicate them. '+e.message;throw e;}finally{slackImportBusy=false;$('slackImportClose').disabled=false;}
});
