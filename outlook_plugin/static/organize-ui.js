'use strict';
window.projectRows=[];
window.agentDirty=false;
let editingProject=null,agentRows=[],agentLoaded=false,agentDirty=false,agentSaving=false,agentTimer;
window.fillProjectSelect=(select,value)=>{select.replaceChildren(text('option','No project'));select.options[0].value='';for(const p of projectRows){const o=text('option',p.name);o.value=p.id;select.append(o);}select.value=value||'';};
window.loadProjects=async()=>{
 projectRows=await api('/api/projects');const selected=$('boardProject').value;
 $('boardProject').replaceChildren();for(const [value,label] of [['','All projects'],['unassigned','No project'],...projectRows.map(p=>[p.id,p.name])]){const o=text('option',label);o.value=value;$('boardProject').append(o);}$('boardProject').value=selected;
 const saved=await api('/api/tasks');const tasks=[...saved.my_tasks,...saved.others_tasks];const root=$('projectList');root.replaceChildren();
 if(!projectRows.length)root.append(text('p','Create a project to group related tasks.','muted'));
 for(const p of projectRows){const rows=tasks.filter(t=>t.project_id===p.id),done=rows.filter(t=>t.completed).length;const card=text('article','','workspace-card');card.append(text('h3',p.name),text('p',p.description),text('p',done+' of '+rows.length+' tasks completed','muted'));const actions=text('div','','actions');const open=text('button','View tasks');open.onclick=()=>{$('boardProject').value=p.id;view('tasks');};const edit=text('button','Edit project');edit.onclick=()=>openProjectEditor(p);actions.append(open,edit);card.append(actions);root.append(card);}
 boardFingerprint='';renderTaskBoard();
};
function openProjectEditor(p){editingProject=p?.id||null;$('projectName').value=p?.name||'';$('projectDescription').value=p?.description||'';$('projectStatus').textContent='';$('projectEditor').showModal();}
$('newProject').onclick=()=>openProjectEditor();$('closeProject').onclick=()=>$('projectEditor').close();
$('projectForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{try{await api('/api/projects',{id:editingProject,name:$('projectName').value,description:$('projectDescription').value});$('projectEditor').close();await loadProjects();}catch(error){$('projectStatus').textContent=error.message;throw error;}});};
$('boardProject').onchange=()=>{boardFingerprint='';renderTaskBoard();};
for(const [id,page] of [['openProfile','context'],['openWritingStyle','writing'],['openUsageDetails','usage']])$(id).onclick=()=>{$('settings').close();view(page);};
function showAgent(){const p=agentRows.find(p=>p.id===$('agentChoice').value);if(!p)return;$('agentInstructions').value=p.instructions;$('agentExamples').value=p.examples;$('agentSaveStatus').textContent='Saved on this Mac.';}
async function saveAgent(){if(agentSaving)return false;agentSaving=true;const key=$('agentChoice').value,values={id:key,instructions:$('agentInstructions').value,examples:$('agentExamples').value};try{agentRows=await api('/api/ai-profiles',values);agentDirty=values.instructions!==$('agentInstructions').value||values.examples!==$('agentExamples').value;$('agentSaveStatus').textContent=agentDirty?'Saving…':'Saved on this Mac.';return !agentDirty;}catch(e){$('agentSaveStatus').textContent='Not saved: '+e.message;return false;}finally{agentSaving=false;window.agentDirty=agentDirty;$('agentChoice').disabled=agentDirty;if(agentDirty)agentTimer=setTimeout(saveAgent,1500);}}
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
