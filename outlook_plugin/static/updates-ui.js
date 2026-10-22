'use strict';
// Discover releases while work is active; the server independently prevents unsafe restarts.
let updateChecking=false,updateAvailable=false,updateInstalling=false,updateQueued=false;
const updateDay=()=>{const d=new Date();return [d.getFullYear(),d.getMonth()+1,d.getDate()].join('-');};
function updatePreference(key,value){try{if(value===undefined)return localStorage.getItem(key);localStorage.setItem(key,value);}catch{}return '';}
updateQueued=updatePreference('outlook-update-queued')==='true';
function showUpdateBanner(){
 if(!$('updateBanner').hidden)return;
 if(updatePreference('outlook-update-seen')===updateDay())return;
 updatePreference('outlook-update-seen',updateDay());
 $('updateBanner').hidden=false;
 $('updateBannerText').textContent=updateQueued?'Update queued. Active work will finish before the app restarts.':'Update available. Install when your work finishes; running jobs will not be stopped.';
 $('updateWhenReady').textContent=updateQueued?'Queued':'Update when ready';$('updateWhenReady').disabled=updateQueued;
}
$('dismissUpdate').onclick=()=>{$('updateBanner').hidden=true;};
$('updateWhenReady').onclick=()=>{updateQueued=true;updatePreference('outlook-update-queued','true');$('updateWhenReady').disabled=true;$('updateWhenReady').textContent='Queued';$('updateBannerText').textContent='Update queued. Active work will finish before the app restarts.';installReadyUpdate();};
async function installReadyUpdate(){
 if(!updateAvailable||updateInstalling||!updateIsIdle())return;
 updateInstalling=true;
 try{const result=await api('/api/update',{});if(result.updated){updateAvailable=false;updateQueued=false;updatePreference('outlook-update-queued','false');$('updateBannerText').textContent='Update installed. Reopening your workspace…';}else if(!/deferred/i.test(result.message||'')){$('updateBannerText').textContent=result.message||'Update could not be installed. We will retry.';}}
 catch{/* Offline or restarting; health checks reconnect without discarding edits. */}
 finally{updateInstalling=false;}
}
async function autoUpdate(){
 if(updateChecking||updateInstalling)return;updateChecking=true;
 try{const result=await api('/api/version');updateAvailable=!!result.update_available;if(updateAvailable){showUpdateBanner();await installReadyUpdate();}else{$('updateBanner').hidden=true;updateQueued=false;updatePreference('outlook-update-queued','false');}}
 catch{/* Leave the existing workspace usable while offline. */}finally{updateChecking=false;}
}
setTimeout(autoUpdate,45000);setInterval(autoUpdate,300000);setInterval(()=>{if(updateQueued)installReadyUpdate();},15000);
