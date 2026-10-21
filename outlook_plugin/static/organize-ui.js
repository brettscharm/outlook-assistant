'use strict';
window.projectRows=[];
window.agentDirty=false;
let editingProject=null,agentRows=[],agentLoaded=false,agentDirty=false,agentSaving=false,agentTimer;
window.fillProjectSelect=(select,value)=>{select.replaceChildren(text('option','No project'));select.options[0].value='';for(const p of projectRows){const o=text('option',p.name);o.value=p.id;select.append(o);}select.value=value||'';};
window.openProject=id=>{$('boardProject').value=id||'';try{localStorage.setItem('outlook-board-project',id||'');}catch{}$('boardSearch').value='';boardFingerprint='';view('tasks');renderTaskBoard();};
window.renderBoardContext=rows=>{
 const p=projectRows.find(p=>p.id===$('boardProject').value);const root=$('boardContext');root.replaceChildren();
 const top=text('div','','project-board-heading');const copy=text('div');
 const title=p?p.name:$('boardProject').value==='unassigned'?'Tasks without a project':'All tasks';
 copy.append(text('h2',title));if(p?.description)copy.append(text('p',p.description,'muted small'));
 const done=rows.filter(t=>t.completed).length,waiting=rows.filter(t=>!t.completed&&t.waiting_on).length;
 copy.append(text('p',rows.length+(rows.length===1?' task · ':' tasks · ')+done+' completed'+(waiting?' · '+waiting+' waiting':''),'muted small'));top.append(copy);
 if(p){const back=text('button','All projects');back.onclick=()=>view('projects');const all=text('button','All tasks');all.onclick=()=>openProject('');top.append(back,all);}
 root.append(top);if($('tasks').classList.contains('active'))$('pageTitle').textContent='Tasks';
};
window.renderProjectCards=tasks=>{
 const root=$('projectList');root.replaceChildren();
 if(!projectRows.length)root.append(text('p','Projects group related tasks. You can also keep tasks without a project.','muted'));
 for(const p of projectRows){
  const rows=tasks.filter(t=>t.project_id===p.id),done=rows.filter(t=>t.completed).length,waiting=rows.filter(t=>!t.completed&&t.waiting_on).length;
  const card=text('article','','workspace-card project-card');card.dataset.color=p.color;const title=text('button',p.name,'project-title');title.onclick=()=>openProject(p.id);card.append(title);if(p.description)card.append(text('p',p.description,'muted small'));
  const meter=document.createElement('progress');meter.max=Math.max(1,rows.length);meter.value=done;meter.setAttribute('aria-label',p.name+' task completion');card.append(meter,text('p',done+' of '+rows.length+' tasks completed'+(waiting?' · '+waiting+' waiting':''),'muted small'));
  const actions=text('div','','actions');const open=text('button','Open project');open.onclick=()=>openProject(p.id);const add=text('button','Add task');add.onclick=()=>{openProject(p.id);$('manualTask').click();};const edit=text('button','Edit project');edit.onclick=()=>openProjectEditor(p);actions.append(open,add,edit);card.append(actions);const links=text('div','','actions project-record-links');for(const link of p.links||[]){try{const u=new URL(link.url);if(u.protocol!=='https:'||u.username||u.password)continue;const a=text('a',link.label||({isc:'ISC opportunity',gainsight:'Gainsight renewal',deployment:'Deployment',other:'Related record'})[link.kind]||'Related record','feedback-link');a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';links.append(a);}catch{}}card.append(links);root.append(card);
 }
 const unassigned=tasks.filter(t=>!t.project_id);if(unassigned.length){const loose=text('button',unassigned.length+(unassigned.length===1?' task without a project':' tasks without a project'),'unassigned-tasks');loose.onclick=()=>openProject('unassigned');root.append(loose);}
};
window.loadProjects=async()=>{
 projectRows=await api('/api/projects');let selected=$('boardProject').value;if(!window.boardProjectRestored){try{selected=localStorage.getItem('outlook-board-project')||selected;}catch{}window.boardProjectRestored=true;}if(selected!=='unassigned'&&!projectRows.some(p=>p.id===selected))selected='';
 $('boardProject').replaceChildren();for(const [value,label] of [['','All tasks'],['unassigned','No project'],...projectRows.map(p=>[p.id,p.name])]){const o=text('option',label);o.value=value;$('boardProject').append(o);}$('boardProject').value=selected;
 const saved=await api('/api/tasks');renderProjectCards([...saved.my_tasks,...saved.others_tasks]);boardFingerprint='';renderTaskBoard();
};
function openProjectEditor(p){$('projectLinks').replaceChildren();for(const link of p?.links||[])addProjectLinkRow(link);editingProject=p?.id||null;$('projectName').value=p?.name||'';$('projectDescription').value=p?.description||'';$('projectColor').value=p?.color||['blue','purple','green','orange','pink'][projectRows.length%5];$('projectStatus').textContent=p?'All changes saved':'';$('saveProject').hidden=!!p;$('closeProject').textContent=p?'Done':'Close';$('retryProjectSave').hidden=true;projectLastSaved=JSON.stringify(projectValues());$('projectEditor').showModal();window.mountTaskFiles($('projectEditor'),'project',editingProject);}
$('newProject').onclick=()=>openProjectEditor();
let projectSaveTimer,projectSavePromise=null,projectLastSaved='';
function projectValues(){return {id:editingProject,name:$('projectName').value,description:$('projectDescription').value,color:$('projectColor').value,links:[...$('projectLinks').children].map(row=>({kind:row.querySelector('select').value,label:row.querySelector('[data-link-label]').value,url:row.querySelector('[data-link-url]').value.trim()}))};}
window.flushProjectEdits=async()=>{
 clearTimeout(projectSaveTimer);
 if(!editingProject||!$('projectEditor').open)return true;
 if(projectSavePromise){if(!await projectSavePromise)return false;return window.flushProjectEdits();}
 if(JSON.stringify(projectValues())===projectLastSaved)return true;
 if(!$('projectForm').reportValidity()){$('projectStatus').textContent='Enter a project name to save.';return false;}
 state.pending++;
 projectSavePromise=(async()=>{try{while(true){const values=projectValues(),snapshot=JSON.stringify(values);if(snapshot===projectLastSaved)break;if(!$('projectForm').checkValidity())return false;$('projectStatus').textContent='Saving…';await api('/api/projects',values);projectLastSaved=snapshot;}$('projectStatus').textContent='All changes saved';$('retryProjectSave').hidden=true;return true;}catch(e){$('projectStatus').textContent='Not saved · '+e.message;$('retryProjectSave').hidden=false;return false;}finally{state.pending--;}})();
 try{return await projectSavePromise;}finally{projectSavePromise=null;}
};
function queueProjectSave(){if(!editingProject)return;clearTimeout(projectSaveTimer);$('projectStatus').textContent='Saving…';projectSaveTimer=setTimeout(()=>window.flushProjectEdits(),650);}
$('projectForm').addEventListener('input',queueProjectSave);$('projectForm').addEventListener('change',queueProjectSave);
$('retryProjectSave').onclick=()=>window.flushProjectEdits();
async function closeProjectEditor(){if(!await window.flushProjectEdits())return;$('projectEditor').close();await loadProjects();}
$('closeProject').onclick=closeProjectEditor;$('projectEditor').addEventListener('cancel',e=>{e.preventDefault();closeProjectEditor();});
$('backToSettings').onclick=async()=>{await $('settingsOpen').onclick();selectSettingsSection('personal');};
$('projectForm').onsubmit=e=>{e.preventDefault();if(editingProject){closeProjectEditor();return;}busy(e.submitter,async()=>{try{await api('/api/projects',projectValues());$('projectEditor').close();await loadProjects();}catch(error){$('projectStatus').textContent=error.message;throw error;}});};
$('boardProject').onchange=()=>{try{localStorage.setItem('outlook-board-project',$('boardProject').value);}catch{}boardFingerprint='';renderTaskBoard();};
for(const [id,page] of [['openProfile','context'],['openWritingStyle','writing'],['openUsageDetails','usage']])$(id).onclick=()=>{$('settings').close();view(page);};
window.flushAgentEdits=async()=>{clearTimeout(agentTimer);while(agentSaving)await new Promise(resolve=>setTimeout(resolve,50));return !agentDirty||await saveAgent();};
function showAgent(){const p=agentRows.find(p=>p.id===$('agentChoice').value);if(!p)return;$('agentInstructions').value=p.instructions;$('agentExamples').value=p.examples;$('agentSaveStatus').textContent='Saved on this Mac.';}
async function saveAgent(){if(agentSaving)return false;agentSaving=true;const key=$('agentChoice').value,values={id:key,instructions:$('agentInstructions').value,examples:$('agentExamples').value};try{agentRows=await api('/api/ai-profiles',values);$('saveAgent').hidden=true;agentDirty=values.instructions!==$('agentInstructions').value||values.examples!==$('agentExamples').value;$('agentSaveStatus').textContent=agentDirty?'Saving…':'Saved on this Mac.';return !agentDirty;}catch(e){$('agentSaveStatus').textContent='Not saved: '+e.message;$('saveAgent').hidden=false;return false;}finally{agentSaving=false;window.agentDirty=agentDirty;$('agentChoice').disabled=agentDirty;if(agentDirty)agentTimer=setTimeout(saveAgent,1500);}}
async function refreshAgents(){const data=await api('/api/ai-profiles');if(!agentLoaded){agentRows=data.profiles;for(const p of agentRows){const o=text('option',p.name);o.value=p.id;$('agentChoice').append(o);}agentLoaded=true;showAgent();}const active=data.activity.find(a=>a.state==='working');$('agentActivityQuick').textContent=active?active.assistant+' · Working':'AI activity';const root=$('agentActivity');root.replaceChildren();if(!data.activity.length)root.append(text('p','No AI requests in this session.','muted'));for(const a of data.activity){root.append(text('p',a.assistant+' · '+a.state+' · '+new Date(a.started).toLocaleTimeString()));}}
$('agentChoice').onchange=()=>{clearTimeout(agentTimer);if(agentDirty){$('agentSaveStatus').textContent='Save your changes before switching assistants.';return;}showAgent();};
$('agentForm').oninput=()=>{agentDirty=true;window.agentDirty=true;$('agentChoice').disabled=true;clearTimeout(agentTimer);$('agentSaveStatus').textContent='Saving…';agentTimer=setTimeout(async()=>{await saveAgent();$('agentChoice').disabled=agentDirty;},700);};
$('agentForm').onsubmit=e=>{e.preventDefault();clearTimeout(agentTimer);busy(e.submitter,async()=>{await saveAgent();$('agentChoice').disabled=agentDirty;});};
$('resetAgent').onclick=()=>busy($('resetAgent'),async()=>{clearTimeout(agentTimer);if(agentSaving)return;agentRows=await api('/api/ai-profiles',{id:$('agentChoice').value,reset:true});agentDirty=false;window.agentDirty=false;$('agentChoice').disabled=false;showAgent();});
$('testAgent').onclick=()=>busy($('testAgent'),async()=>{if(!await saveAgent())return;$('agentTestResult').textContent='Working…';try{$('agentTestResult').textContent=(await api('/api/ai-profile-test',{id:$('agentChoice').value,sample:$('agentSample').value})).answer;}catch(e){$('agentTestResult').textContent=e.message;throw e;}});
$('agentActivityQuick').onclick=async()=>{await $('settingsOpen').onclick();selectSettingsSection('agents');await refreshAgents();};
loadProjects().catch(e=>notice(e.message));refreshAgents().catch(()=>{});setInterval(()=>{if(!document.hidden)refreshAgents().catch(()=>{});},3000);

async function refreshBobInstall(){const data=await api('/api/bob-install');$('bobInstallStatus').textContent=data.message;$('installBob').disabled=data.state==='working';}
$('installBob').onclick=()=>busy($('installBob'),async()=>{await api('/api/bob-install',{});await refreshBobInstall();});
async function checkBobRelease(){try{const r=await api('/api/bob-release');$('bobReleaseStatus').textContent=r.version?(r.update_available?'Bob update available: '+r.version+' (installed '+r.installed+').':r.installed===r.version?'Bob '+r.version+' is up to date.':'Latest supported IBM release: '+r.version):r.error;}catch{}}
setTimeout(checkBobRelease,5000);setInterval(checkBobRelease,86400000);setInterval(()=>{if($('settings').open)refreshBobInstall().catch(()=>{});},3000);

let archivePolling=null;
function showArchiveStatus(s){$('archiveMail').disabled=s.state==='working';$('archiveStatus').textContent=s.message+' '+s.messages+' emails · '+s.attachments+' attachments · '+s.missing_attachments+' attachments unavailable or skipped · '+s.previews+' preview-only emails. Saved at '+s.path;if(s.state!=='working'&&archivePolling){clearInterval(archivePolling);archivePolling=null;}}
$('archiveMail').onclick=async()=>{try{showArchiveStatus(await api('/api/archive',{}));if(!archivePolling)archivePolling=setInterval(()=>api('/api/archive').then(showArchiveStatus).catch(e=>{$('archiveStatus').textContent=e.message;}),2000);}catch(e){$('archiveStatus').textContent=e.message;}};

$('loadMeetingMail').onclick=()=>busy($('loadMeetingMail'),async()=>{const data=await api('/api/meeting-mail');$('meetingMailStatus').textContent=data.items.length+' meeting emails from all cached folders, including Deleted Items.'+(data.truncated?' Showing the 500 most recent matches.':'');const root=$('meetingMailResults');root.replaceChildren();for(const item of data.items){const card=text('article','','action-card');card.append(text('h3',item.subject),text('p',[item.folder,date(item.received_time,true)].filter(Boolean).join(' · '),'muted small'));for(const detail of item.details){if(detail.start_time)card.append(text('p','Invitation time: '+(detail.start_time.length===10?detail.start_time:date(detail.start_time,true))));if(detail.status||detail.method)card.append(text('p','Invitation record: '+[detail.method,detail.status].filter(Boolean).join(' · '),'muted small'));if(detail.rrule)card.append(text('p','Recurring invitation; individual occurrences are not expanded.','muted small'));}const open=text('button','Open source email');open.onclick=()=>{view('mail');selectEmail(item.email_id).catch(e=>notice(e.message,'error'));};card.append(open);root.append(card);}});

let checkingExternalProjects=false;setInterval(async()=>{if(checkingExternalProjects||document.hidden||$('projectEditor').open||$('taskEditor').open||['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;checkingExternalProjects=true;try{const rows=await api('/api/projects');if(JSON.stringify(rows)!==JSON.stringify(projectRows))await loadProjects();}catch{}finally{checkingExternalProjects=false;}},5000);

function addProjectLinkRow(link={}){
 const row=text('div','','project-link-row');const kind=document.createElement('select');kind.setAttribute('aria-label','Record type');for(const [value,label] of [['isc','ISC opportunity'],['gainsight','Gainsight renewal'],['deployment','Deployment'],['other','Other record']]){const o=text('option',label);o.value=value;kind.append(o);}kind.value=link.kind||'isc';
 const label=document.createElement('input');label.dataset.linkLabel='';label.setAttribute('aria-label','Record name or ID');label.placeholder='Name or opportunity ID';label.maxLength=200;label.value=link.label||'';
 const url=document.createElement('input');url.dataset.linkUrl='';url.type='url';url.required=true;url.pattern='https://.*';url.setAttribute('aria-label','Record URL');url.placeholder='https://…';url.maxLength=4000;url.value=link.url||'';
 const remove=text('button','Remove');remove.type='button';remove.setAttribute('aria-label','Remove record link');remove.onclick=()=>{row.remove();queueProjectSave();};row.append(kind,label,url,remove);$('projectLinks').append(row);
}
$('addProjectLink').onclick=()=>{if($('projectLinks').children.length>=20)return;addProjectLinkRow();$('projectLinks').lastElementChild.querySelector('input').focus();};
