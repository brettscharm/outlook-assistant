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
  const card=text('article','','workspace-card project-card');const title=text('button',p.name,'project-title');title.onclick=()=>openProject(p.id);card.append(title);if(p.description)card.append(text('p',p.description,'muted small'));
  const meter=document.createElement('progress');meter.max=Math.max(1,rows.length);meter.value=done;meter.setAttribute('aria-label',p.name+' task completion');card.append(meter,text('p',done+' of '+rows.length+' tasks completed'+(waiting?' · '+waiting+' waiting':''),'muted small'));
  const actions=text('div','','actions');const open=text('button','Open project');open.onclick=()=>openProject(p.id);const add=text('button','Add task');add.onclick=()=>{openProject(p.id);$('manualTask').click();};const edit=text('button','Edit project');edit.onclick=()=>openProjectEditor(p);actions.append(open,add,edit);card.append(actions);root.append(card);
 }
 const unassigned=tasks.filter(t=>!t.project_id);if(unassigned.length){const loose=text('button',unassigned.length+(unassigned.length===1?' task without a project':' tasks without a project'),'unassigned-tasks');loose.onclick=()=>openProject('unassigned');root.append(loose);}
};
window.loadProjects=async()=>{
 projectRows=await api('/api/projects');let selected=$('boardProject').value;if(!window.boardProjectRestored){try{selected=localStorage.getItem('outlook-board-project')||selected;}catch{}window.boardProjectRestored=true;}if(selected!=='unassigned'&&!projectRows.some(p=>p.id===selected))selected='';
 $('boardProject').replaceChildren();for(const [value,label] of [['','All tasks'],['unassigned','No project'],...projectRows.map(p=>[p.id,p.name])]){const o=text('option',label);o.value=value;$('boardProject').append(o);}$('boardProject').value=selected;
 const saved=await api('/api/tasks');renderProjectCards([...saved.my_tasks,...saved.others_tasks]);boardFingerprint='';renderTaskBoard();
};
function openProjectEditor(p){editingProject=p?.id||null;$('projectName').value=p?.name||'';$('projectDescription').value=p?.description||'';$('projectStatus').textContent='';$('projectEditor').showModal();}
$('newProject').onclick=()=>openProjectEditor();$('closeProject').onclick=()=>$('projectEditor').close();
$('projectForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{try{await api('/api/projects',{id:editingProject,name:$('projectName').value,description:$('projectDescription').value});$('projectEditor').close();await loadProjects();}catch(error){$('projectStatus').textContent=error.message;throw error;}});};
$('boardProject').onchange=()=>{try{localStorage.setItem('outlook-board-project',$('boardProject').value);}catch{}boardFingerprint='';renderTaskBoard();};
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

let archivePolling=null;
function showArchiveStatus(s){$('archiveMail').disabled=s.state==='working';$('archiveStatus').textContent=s.message+' '+s.messages+' emails · '+s.attachments+' attachments · '+s.missing_attachments+' attachments unavailable or skipped · '+s.previews+' preview-only emails. Saved at '+s.path;if(s.state!=='working'&&archivePolling){clearInterval(archivePolling);archivePolling=null;}}
$('archiveMail').onclick=async()=>{try{showArchiveStatus(await api('/api/archive',{}));if(!archivePolling)archivePolling=setInterval(()=>api('/api/archive').then(showArchiveStatus).catch(e=>{$('archiveStatus').textContent=e.message;}),2000);}catch(e){$('archiveStatus').textContent=e.message;}};

let calendarLoading=false;
window.loadCalendar=async()=>{if(calendarLoading)return;calendarLoading=true;$('refreshCalendar').disabled=true;$('calendarStatus').textContent='Reading Teams calendar…';try{const data=await api('/api/calendar');$('calendarStatus').textContent=data.warning+' Last read '+date(new Date(data.checked*1000).toISOString(),true)+(data.skipped?' · '+data.skipped+' records could not be read.':'');const root=$('calendarEvents');root.replaceChildren();if(!data.events.length)root.append(text('p','No cached meetings found in this date range.'));for(const event of data.events){const card=text('article','','action-card');card.append(text('h3',event.subject),text('p',date(event.start_time,true)+' – '+date(event.end_time,true)),text('p',[event.organizer,event.location].filter(Boolean).join(' · '),'muted small'));try{const url=new URL(event.join_url);if(url.protocol==='https:'&&!url.username&&!url.password&&!event.join_url.includes('[redacted]')){const join=text('a','Join meeting');join.href=url.href;join.target='_blank';join.rel='noopener noreferrer';card.append(join);}}catch{}root.append(card);}}catch(e){$('calendarStatus').textContent=e.message;$('calendarEvents').replaceChildren();}finally{calendarLoading=false;$('refreshCalendar').disabled=false;}};
$('refreshCalendar').onclick=window.loadCalendar;
setInterval(()=>{if($('calendar').classList.contains('active')&&!document.hidden)window.loadCalendar();},60000);

$('loadMeetingMail').onclick=()=>busy($('loadMeetingMail'),async()=>{const data=await api('/api/meeting-mail');$('meetingMailStatus').textContent=data.items.length+' meeting emails from all cached folders, including Deleted Items.'+(data.truncated?' Showing the 500 most recent matches.':'');const root=$('meetingMailResults');root.replaceChildren();for(const item of data.items){const card=text('article','','action-card');card.append(text('h3',item.subject),text('p',[item.folder,date(item.received_time,true)].filter(Boolean).join(' · '),'muted small'));for(const detail of item.details){if(detail.start_time)card.append(text('p','Invitation time: '+(detail.start_time.length===10?detail.start_time:date(detail.start_time,true))));if(detail.status||detail.method)card.append(text('p','Invitation record: '+[detail.method,detail.status].filter(Boolean).join(' · '),'muted small'));if(detail.rrule)card.append(text('p','Recurring invitation; individual occurrences are not expanded.','muted small'));}const open=text('button','Open source email');open.onclick=()=>{view('mail');selectEmail(item.email_id).catch(e=>notice(e.message,'error'));};card.append(open);root.append(card);}});
