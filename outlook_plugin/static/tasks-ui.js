'use strict';
let compactTaskCards=false;const taskCardOverrides=new Map();
try{compactTaskCards=localStorage.getItem('outlook-compact-tasks')==='true';}catch{}
let boardLanes=[],laneDraft=[],draggedTask=null;
let taskPage=1,taskViewChosen=false,revealSavedTask=null;
let taskReview=null,taskSaved=[],taskView='review',taskEditor=null,taskFingerprint='',taskLoading=false,scanFormReady=false,scanPanelSettled=false;
window.taskFormDirty=false;
window.taskScanRunning=false;
const localToday=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
function taskDeadline(t){const due=/^\d{4}-\d{2}-\d{2}$/.test(t.due_date||'')?t.due_date:'';return {due,label:due?new Date(due+'T12:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'}):'No deadline stated',overdue:!!due&&due<localToday()&&!t.completed};}
const openEmailPreviews=new Set();
function taskSource(t){
 const root=text('div','','task-email-source');
 const open=text('button',t.email_subject||'Open source email','source-email');open.type='button';open.onclick=()=>{view('mail');selectEmail(t.email_id).catch(e=>notice(e.message));};
 const details=document.createElement('details');details.className='task-email-preview';
 const key=t.id||t.email_id;const summary=text('summary','Preview email');const content=text('div','','task-email-content');details.append(summary,content);
 let loaded=false,loading=false;
 async function load(){
  if(loading||loaded)return;loading=true;content.setAttribute('aria-busy','true');content.replaceChildren(text('p','Loading email…','muted small'));
  try{const m=await api('/api/email?'+new URLSearchParams({id:t.email_id}));
   content.replaceChildren(text('strong',m.subject||'(No subject)'),text('p',m.sender||m.from?.address||'Sender unavailable','muted small'),text('p',date(m.received_time,true),'muted small'),text('p',m.body_complete?'Cached email':'Preview only · Full email is not available in the cache','muted small'),text('div',m.body||m.preview||'No readable content cached.','task-email-body'));const body=content.querySelector('.task-email-body');renderEmailLinks(body,body.textContent);loaded=true;
  }catch(e){content.replaceChildren(text('p','Email preview unavailable: '+e.message,'muted small'));const retry=text('button','Try again');retry.type='button';retry.onclick=load;content.append(retry);}
  finally{loading=false;content.removeAttribute('aria-busy');}
 }
 details.ontoggle=()=>{summary.textContent=details.open?'Hide email':'Preview email';if(details.open){openEmailPreviews.add(key);load();}else openEmailPreviews.delete(key);};
 details.open=openEmailPreviews.has(key);root.append(open,details);return root;
}
function setTaskView(name){
 taskViewChosen=true;taskPage=1;
 if(!['review','dismissed'].includes(name)){view('tasks');renderTaskBoard();return;}
 taskView=name;if(name==='dismissed')$('taskDueFilter').value='all';
 if(!$('task-review').classList.contains('active'))view('task-review');
 document.querySelectorAll('[data-task-view]').forEach(b=>b.classList.toggle('selected',b.dataset.taskView===name));taskFingerprint='';renderTaskList();
}
function editTask(item,origin){taskEditor={item,origin};$('taskEditorTitle').textContent=origin==='review'?'Review before adding':origin==='new'?'Add a task':'Edit task';$('editTaskText').value=item.text||'';$('editTaskDescription').value=item.description||'';$('editTaskSource').value=item.source_type||(item.email_id?'email':'other');$('editTaskSourceUrl').value=item.source_url||'';$('editTaskType').value=item.type||'my';$('editTaskOwner').value=item.owner||item.assignee||'';$('editTaskDue').value=taskDeadline(item).due;$('editTaskEvidence').textContent=item.evidence||'';$('editTaskEvidence').hidden=!item.evidence;$('editTaskDateNote').textContent=[item.due_evidence?'Deadline in email: “'+item.due_evidence+'”':'',item.due_note||''].filter(Boolean).join(' · ');$('saveTaskEdit').textContent=origin==='saved'?'Save changes':'Add task';$('ownerSuggestions').hidden=true;$('editTaskOwner').setCustomValidity('');$('taskEditor').showModal();loadOwnerContacts();}
function dismissMenu(item){
 const details=document.createElement('details');details.className='dismiss-menu';
 details.append(text('summary','Dismiss…'));
 const choices=text('div','','dismiss-reasons');choices.setAttribute('role','group');choices.setAttribute('aria-label','Dismiss reason for '+item.text);
 let saving=false;
 for(const [key,label] of Object.entries(taskReview?.reasons||{})){
  const button=text('button',label);button.type='button';
  button.onclick=async()=>{
   if(saving)return;saving=true;choices.setAttribute('aria-busy','true');
   choices.querySelectorAll('button').forEach(b=>b.disabled=true);
   try{await api('/api/task-review',{id:item.id,action:'dismiss',reason:key});await loadTaskWorkspace();notice('Dismissed: '+label+'. You can restore it in Dismissed.');}
   catch(e){notice(e.message,'error');}
   finally{saving=false;choices.removeAttribute('aria-busy');choices.querySelectorAll('button').forEach(b=>b.disabled=false);}
  };
  choices.append(button);
 }
 details.append(choices);return details;
}
function taskCard(t,origin){const card=text('article','','action-card');const top=text('div','','action-card-top');const title=text('h3',t.text);top.append(title);if(t.company)top.append(text('span',t.company,'company-chip'));card.append(top);if(t.description){const description=text('p','','task-description');renderEmailLinks(description,t.description);card.append(description);}else if(t.evidence)card.append(text('p','From the email: “'+t.evidence+'”','task-description'));const meta=text('div','','task-meta');const owner=t.owner||t.assignee||'Owner unclear';const due=taskDeadline(t);meta.append(text('span',t.type==='my'?'Your task':owner,'owner-chip '+(t.type==='unclear'?'unclear':'')),text('span',(due.overdue?'Overdue · ':'')+due.label,due.overdue?'due-chip overdue':'due-chip'));if(t.due_note)meta.append(text('span','Check deadline','due-chip caution'));meta.append(text('span',({email:'Email',slack:'Slack',teams:'Teams',meeting:'Meeting',other:'Other'})[t.source_type||(t.email_id?'email':'other')],'source-chip'));card.append(meta);if(t.source_url){try{const url=new URL(t.source_url);if(['https:','http:'].includes(url.protocol)){const link=text('a','Open source link','task-source-link');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';card.append(link);}}catch{}}if(t.email_id)card.append(taskSource(t));if(t.evidence){const details=document.createElement('details');details.className='evidence';details.append(text('summary','Why this is a task'),text('blockquote',t.evidence));if(t.owner_evidence&&t.owner_evidence!==t.evidence)details.append(text('p','Owner: “'+t.owner_evidence+'”','muted small'));if(t.due_evidence)details.append(text('p','Deadline: “'+t.due_evidence+'”','muted small'));card.append(details);}const actions=text('div','','actions task-card-actions');if(origin==='review'){const add=text('button','Review & add','primary');add.onclick=()=>editTask(t,'review');actions.append(add,dismissMenu(t));}else if(origin==='dismissed'){actions.append(text('span',taskReview.reasons[t.reason]||'Dismissed','muted small'));const restore=text('button','Restore');restore.onclick=()=>busy(restore,async()=>{await api('/api/task-review',{action:'restore',id:t.id});await loadTaskWorkspace();});actions.append(restore);}else{const complete=text('button',t.completed?'Reopen':'Mark done');complete.onclick=()=>busy(complete,async()=>{const wasDone=t.completed;await api('/api/tasks',{action:'toggle',id:t.id});if(!wasDone)celebrateTaskDone();await loadTaskWorkspace();});const edit=text('button','Edit');edit.onclick=()=>editTask(t,'saved');actions.append(complete,edit);}card.append(actions);if(origin==='saved')addTaskCollapse(card,top,t);return card;}
function renderTaskList(){if(!taskReview)return;const query=$('taskSearch').value.trim().toLowerCase(),filter=$('taskDueFilter').value;let items,origin;
if(taskView==='review'||taskView==='dismissed'){origin=taskView;items=taskReview.suggestions.filter(t=>t.status===taskView);}else{origin='saved';items=taskSaved.filter(t=>taskView==='done'?t.completed:!t.completed&&(taskView==='all'||(taskView==='my'?t.type==='my':t.type!=='my')));}
items=items.filter(t=>{const due=taskDeadline(t);return (!query||(t.text+' '+(t.description||'')+' '+(t.source_type||'')+' '+(t.owner||t.assignee||'')+' '+(t.company||'')+' '+(t.email_subject||'')).toLowerCase().includes(query))&&(filter==='all'||filter==='overdue'&&due.overdue||filter==='today'&&due.due===localToday()||filter==='upcoming'&&due.due>localToday()||filter==='none'&&!due.due);});
items.sort((a,b)=>(taskDeadline(a).due||'9999').localeCompare(taskDeadline(b).due||'9999'));
if(revealSavedTask){const index=items.findIndex(revealSavedTask);if(index>=0){taskPage=Math.floor(index/20)+1;revealSavedTask=null;}}
taskPage=Math.min(taskPage,Math.max(1,Math.ceil(items.length/20)));
const fingerprint=JSON.stringify([items,taskView,query,filter,taskPage]);if(fingerprint===taskFingerprint)return;taskFingerprint=fingerprint;listPager('taskPages',items.length,taskPage,20,page=>{taskPage=page;taskFingerprint='';renderTaskList();$('taskPages').scrollIntoView({block:'nearest'});});
const root=$('taskList');root.replaceChildren();if(!items.length){const empty=text('div','','task-empty');empty.append(text('h3',taskView==='review'?'Nothing waiting for review.':'No tasks in this view.'),text('p',taskView==='review'?'New suggestions appear here automatically when task discovery is on.':'Try another filter or add a task.','muted'));root.append(empty);}for(const item of items.slice((taskPage-1)*20,taskPage*20))root.append(taskCard(item,origin));}
window.loadTaskWorkspace=function(){if(taskLoading)return taskLoading;taskLoading=(async()=>{try{const [review,saved,lanes]=await Promise.all([api('/api/task-review'),api('/api/tasks'),api('/api/task-lanes')]);boardLanes=lanes;taskReview=review;$('reviewBadge').textContent=review.suggestions.filter(t=>t.status==='review').length;taskSaved=[...(saved.my_tasks||[]).map(t=>({...t,type:t.type||'my'})),...(saved.others_tasks||[]).map(t=>({...t,type:t.type||'others'}))];window.taskScanRunning=review.job.running;if(lastSuccessfulSync&&!state.busy){$('syncTime').textContent=syncTimeLabel()+(review.job.running?' · Checking tasks…':review.job.status==='error'?' · Task check failed':review.last_check?' · Tasks checked '+new Date(review.last_check).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}):'');}$('identityPrompt').hidden=review.identity_ready;$('findTasks').disabled=review.job.running||state.pending>0;$('stopScan').hidden=!review.job.running;$('scanProgress').max=Math.max(1,review.job.total);$('scanProgress').value=review.job.scanned;$('scanProgress').hidden=!review.job.running;
const auto=review.automatic_state;
$('scanScheduleLabel').textContent=auto==='paused'?'Task discovery paused':'Automatic task discovery';
$('toggleTaskAuto').textContent=review.options.interval?'Pause automatic discovery':'Resume automatic discovery';
const status=auto==='paused'?'Resume to find new tasks.':auto==='identity'?'Add your name and work email to start.':auto==='bob'?'Test your Bob connection in Settings to start.':'Watching for new email'+(review.last_check?' · Last checked '+new Date(review.last_check).toLocaleTimeString(): ' · No check completed yet');
$('taskScanStatus').textContent=review.job.running?review.job.message:review.job.status==='error'?review.job.message:status;
if(!scanFormReady){const initial=restored?.scanDraft||review.options;$('scanSince').value=initial.since;$('scanMode').value=initial.mode;$('scanInterval').value=initial.interval;window.taskFormDirty=!!restored?.scanDraft;scanFormReady=true;}if(!scanPanelSettled&&!review.job.running&&(review.suggestions.length||taskSaved.length)){document.querySelector('.scan-panel').open=false;scanPanelSettled=true;}
const stats=[['To review',review.suggestions.filter(t=>t.status==='review').length,'review'],['My active tasks',taskSaved.filter(t=>!t.completed&&t.type==='my').length,'my'],['Others / unclear',taskSaved.filter(t=>!t.completed&&t.type!=='my').length,'others'],['Overdue',taskSaved.filter(t=>taskDeadline(t).overdue).length,'overdue']];const statsKey=JSON.stringify(stats);if($('taskStats').dataset.fingerprint!==statsKey){$('taskStats').dataset.fingerprint=statsKey;$('taskStats').replaceChildren();for(const [label,count,target] of stats){const b=text('button','','task-stat');b.append(text('span',label),text('strong',count));b.onclick=()=>{$('taskDueFilter').value=target==='overdue'?'overdue':'all';setTaskView(target==='overdue'?'all':target);};$('taskStats').append(b);}}renderTaskList();renderTaskBoard();if(state.selected&&document.querySelector('.email-task-summary'))renderEmailSummary(state.selected,document.querySelector('.email-task-summary'));
}finally{taskLoading=false;}})();return taskLoading;};
function scanValues(){return {since:$('scanSince').value,mode:$('scanMode').value,interval:Number($('scanInterval').value)};}
let scanSaveTimer;$('scanForm').oninput=()=>{window.taskFormDirty=true;clearTimeout(scanSaveTimer);scanSaveTimer=setTimeout(async()=>{if(!$('scanForm').checkValidity())return;try{await api('/api/task-scan-settings',scanValues());window.taskFormDirty=false;$('scanSaveStatus').textContent='Saved.';await loadTaskWorkspace();}catch(e){$('scanSaveStatus').textContent='Not saved: '+e.message;}},700);};
window.getTaskScanDraft=()=>window.taskFormDirty?scanValues():null;
$('scanForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{await api('/api/task-scan-settings',scanValues());window.taskFormDirty=false;await loadTaskWorkspace();notice('Scan settings saved.');});};
$('findTasks').onclick=()=>busy($('findTasks'),async()=>{if(!$('scanForm').reportValidity())return;await api('/api/task-scan-settings',scanValues());window.taskFormDirty=false;await api('/api/task-scan',scanValues());setTaskView('review');await loadTaskWorkspace();});
$('toggleTaskAuto').onclick=()=>busy($('toggleTaskAuto'),async()=>{clearTimeout(scanSaveTimer);const interval=taskReview.options.interval?0:15;$('scanInterval').value=interval;await api('/api/task-scan-settings',scanValues());window.taskFormDirty=false;}).finally(()=>loadTaskWorkspace());
$('stopScan').onclick=()=>busy($('stopScan'),async()=>{await api('/api/task-scan-stop',{});await loadTaskWorkspace();});
$('setIdentity').onclick=()=>{view('context');$('contextForm').elements.full_name.focus();};
$('manualTask').onclick=()=>editTask({type:'my',owner:currentOwnerName()},'new');
$('closeTaskEditor').onclick=()=>$('taskEditor').close();
$('taskEditorForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{
 const {item,origin}=taskEditor;
 const values={id:item.id,text:$('editTaskText').value,description:$('editTaskDescription').value,source_type:$('editTaskSource').value,source_url:$('editTaskSourceUrl').value,type:$('editTaskType').value,owner:$('editTaskOwner').value,due_date:$('editTaskDue').value};
 clearTimeout(taskEditTimer);
 await api(origin==='review'?'/api/task-review':'/api/tasks',{...values,action:origin==='review'?'accept':origin==='new'?'add':'edit'});
 $('taskEditor').close();
 // Finish any earlier refresh before reading the newly committed task.
 if(taskLoading)await taskLoading;
 await loadTaskWorkspace();
 $('taskSearch').value='';$('boardSearch').value='';$('taskDueFilter').value='all';
 const target=origin==='review'?taskSaved.find(t=>t.suggestion_id===item.id):origin==='saved'?taskSaved.find(t=>t.id===item.id):taskSaved.find(t=>t.text===values.text.trim()&&t.type===values.type);
 revealSavedTask=t=>target?t.id===target.id:origin==='review'?t.suggestion_id===item.id:t.text===values.text.trim();
 view('tasks');setTaskView(target?.completed?'done':values.type==='my'?'my':'others');
 taskFingerprint='';renderTaskBoard();
 $('taskBoard').scrollIntoView({block:'start'});
 notice('Task saved in '+(boardLanes.find(l=>l.id===taskLane(target||{}))?.name||'My Tasks')+'.');
});};
document.querySelectorAll('[data-task-view]').forEach(b=>b.onclick=()=>setTaskView(b.dataset.taskView));$('taskSearch').oninput=()=>{taskPage=1;renderTaskList();};$('taskDueFilter').onchange=()=>{taskPage=1;renderTaskList();};
window.mountEmailTasks=function(id,root){const panel=text('section','','email-task-summary');root.insertBefore(panel,root.querySelector('.reader-meta'));renderEmailSummary(id,panel);};
async function renderEmailSummary(id,panel){try{const review=await api('/api/task-review?'+new URLSearchParams({email_id:id}));if(state.selected!==id||!panel.isConnected)return;const items=review.suggestions.filter(t=>t.status!=='dismissed');const fingerprint=JSON.stringify([items,review.email_scanned,review.job.running]);if(panel.dataset.fingerprint===fingerprint)return;panel.dataset.fingerprint=fingerprint;panel.replaceChildren();const heading=text('div','','email-task-heading');heading.append(text('h3','Actions in this email'));const scan=text('button',review.job.running?'Scan in progress…':'Review this email');scan.disabled=review.job.running;scan.onclick=()=>busy(scan,async()=>{await api('/api/task-scan',{email_id:id,mode:'all'});await loadTaskWorkspace();});heading.append(scan);panel.append(heading);if(!items.length){panel.append(text('p',review.email_scanned?'No action items found.':'No tasks found yet.','muted small'));return;}const mine=items.filter(t=>t.type==='my');if(!mine.length)panel.append(text('p','No task clearly assigned to you.','muted small'));const groups=new Map();for(const item of items){const label=item.type==='my'?'YOUR TASKS':item.type==='unclear'?'OWNER UNCLEAR':(item.owner||'OTHER OWNER').toUpperCase()+"’S TASKS";if(!groups.has(label))groups.set(label,[]);groups.get(label).push(item);}for(const [label,tasks] of groups){panel.append(text('h4',label));for(const item of tasks){const row=text('div','','email-action');row.append(text('strong',item.text),text('span',taskDeadline(item).label,'muted small'));if(item.description)row.append(text('p',item.description,'task-description'));if(item.status==='review'){const add=text('button','Review & add');add.onclick=()=>editTask(item,'review');row.append(add);}else row.append(text('span',item.completed?'Completed':'Added to tasks','muted small'));panel.append(row);}}}catch(e){panel.textContent='Task summary unavailable: '+e.message;}}
loadTaskWorkspace().catch(e=>notice(e.message));setInterval(()=>{if(!document.hidden&&!$('taskEditor').open&&!document.querySelector('.dismiss-menu[open]'))loadTaskWorkspace().catch(()=>{});},5000);

let taskEditTimer;
$('taskEditorForm').addEventListener('input',()=>{if(taskEditor?.origin!=='saved')return;clearTimeout(taskEditTimer);const id=taskEditor.item.id;taskEditTimer=setTimeout(async()=>{if(!taskEditor||taskEditor.item.id!==id||!$('taskEditorForm').checkValidity())return;try{await api('/api/tasks',{action:'edit',id,text:$('editTaskText').value,description:$('editTaskDescription').value,source_type:$('editTaskSource').value,source_url:$('editTaskSourceUrl').value,type:$('editTaskType').value,owner:$('editTaskOwner').value,due_date:$('editTaskDue').value});$('taskEditorTitle').textContent='Edit task · Saved';taskFingerprint='';}catch(e){$('taskEditorTitle').textContent='Edit task · Not saved';notice(e.message);}},650);});

const boardLimits={my:20,others:20,done:20};
let boardFingerprint='';
window.openTaskPage=id=>{if(id==='tasks')renderTaskBoard();else{taskFingerprint='';renderTaskList();}};
function renderTaskBoard(){
 const query=$('boardSearch').value.trim().toLowerCase();
 const items=taskSaved.filter(t=>!query||[t.text,t.description,t.source_type,t.owner,t.assignee,t.company,t.email_subject].filter(Boolean).join(' ').toLowerCase().includes(query));
 items.sort((a,b)=>(taskDeadline(a).due||'9999').localeCompare(taskDeadline(b).due||'9999'));
 const lanes=boardLanes.map(lane=>{boardLimits[lane.id]??=20;return [lane.id,lane.name,items.filter(t=>taskLane(t)===lane.id)];});
 if(revealSavedTask){for(const [key,,rows] of lanes){const index=rows.findIndex(revealSavedTask);if(index>=0){boardLimits[key]=Math.max(boardLimits[key],index+1);revealSavedTask=null;break;}}}
 const fingerprint=JSON.stringify([lanes,boardLimits]);if(draggedTask||fingerprint===boardFingerprint)return;boardFingerprint=fingerprint;
 const root=$('taskBoard');root.replaceChildren();
 for(const [key,label,rows] of lanes){const lane=text('section','','task-lane');lane.setAttribute('aria-label',label);lane.dataset.lane=key;lane.ondragover=e=>{if(draggedTask){e.preventDefault();e.dataTransfer.dropEffect='move';lane.classList.add('drop-target');}};lane.ondragleave=e=>{if(!lane.contains(e.relatedTarget))lane.classList.remove('drop-target');};lane.ondrop=e=>{e.preventDefault();lane.classList.remove('drop-target');const id=draggedTask;draggedTask=null;if(id)moveBoardTask(id,key);};const heading=text('div','','lane-heading');heading.append(text('h2',label),text('span',rows.length,'nav-count'));lane.append(heading);
 if(!rows.length)lane.append(text('p',query?'No matching tasks.':key==='done'?'Completed tasks appear here.':'Drag tasks here or choose this lane on a card.','lane-empty'));
 for(const task of rows.slice(0,boardLimits[key])){
 const card=taskCard(task,'saved');card.draggable=true;card.dataset.taskId=task.id;
 card.ondragstart=e=>{if(e.target.closest('a,button,input,select,textarea,details')){e.preventDefault();return;}draggedTask=task.id;e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',task.id);};
 card.ondragend=()=>{draggedTask=null;document.querySelectorAll('.drop-target').forEach(el=>el.classList.remove('drop-target'));};
 const label=text('label','Move to','lane-move');const select=document.createElement('select');select.setAttribute('aria-label','Move '+task.text+' to lane');
 for(const option of boardLanes){const el=text('option',option.name);el.value=option.id;el.selected=option.id===key;select.append(el);}
 select.onchange=()=>{select.disabled=true;moveBoardTask(task.id,select.value).finally(()=>select.disabled=false);};label.append(select);card.append(label);lane.append(card);
 }
 if(rows.length>boardLimits[key]){const more=text('button','Show more ('+(rows.length-boardLimits[key])+' remaining)');more.onclick=()=>{boardLimits[key]+=20;renderTaskBoard();};lane.append(more);}root.append(lane);
 }
}
$('boardSearch').oninput=()=>{boardFingerprint='';renderTaskBoard();};

function taskLane(t){return t.completed?'done':t.lane_id&&t.lane_id!=='done'?t.lane_id:'todo';}
async function moveBoardTask(id,lane){const wasDone=taskSaved.find(t=>t.id===id)?.completed;try{await api('/api/tasks',{action:'move',id,lane_id:lane});if(lane==='done'&&!wasDone)celebrateTaskDone();if(taskLoading)await taskLoading;await loadTaskWorkspace();notice('Moved to '+(boardLanes.find(l=>l.id===lane)?.name||'lane')+'.');}catch(e){notice(e.message,'error');boardFingerprint='';renderTaskBoard();}}
function renderLaneEditor(){
 const root=$('laneRows');root.replaceChildren();
 laneDraft.forEach((lane,index)=>{const row=text('div','','lane-config-row');const name=document.createElement('input');name.value=lane.name;name.maxLength=60;name.required=true;name.setAttribute('aria-label','Lane '+(index+1)+' name');name.oninput=()=>lane.name=name.value;row.append(name);
 if(lane.id==='todo'||lane.id==='done')row.append(text('small',lane.id==='todo'?'Starting lane':'Completed lane','muted'));
 for(const [title,step] of [['Move up',-1],['Move down',1]]){const b=text('button',step<0?'↑':'↓');b.type='button';b.setAttribute('aria-label',title+' '+lane.name);b.disabled=index+step<0||index+step>=laneDraft.length;b.onclick=()=>{[laneDraft[index],laneDraft[index+step]]=[laneDraft[index+step],laneDraft[index]];renderLaneEditor();};row.append(b);}
 if(!['todo','done'].includes(lane.id)){const remove=text('button','Remove');remove.type='button';remove.onclick=()=>{if(taskSaved.some(t=>taskLane(t)===lane.id)){$('laneSaveStatus').textContent='Move tasks out of this lane before removing it.';return;}laneDraft.splice(index,1);renderLaneEditor();};row.append(remove);}root.append(row);
 });$('addLane').disabled=laneDraft.length>=12;
}
$('configureLanes').onclick=()=>{laneDraft=boardLanes.map(l=>({...l}));$('laneSaveStatus').textContent='';renderLaneEditor();$('laneEditor').showModal();};
$('closeLanes').onclick=()=>$('laneEditor').close();
$('addLane').onclick=()=>{if(laneDraft.length<12){laneDraft.push({id:'lane-'+crypto.randomUUID(),name:'New lane'});renderLaneEditor();}};
$('laneForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{try{boardLanes=await api('/api/task-lanes',{lanes:laneDraft});$('laneEditor').close();boardFingerprint='';renderTaskBoard();notice('Lanes saved on this Mac.');}catch(error){$('laneSaveStatus').textContent=error.message;}});};

let ownerContacts=[],ownerContactsLoading=false;
function currentOwnerName(){return $('contextForm').elements.full_name.value.trim()||'Me';}
function currentOwnerEmails(){return $('contextForm').elements.email_addresses.value.toLowerCase().split(/[,;\s]+/).filter(v=>v.includes('@'));}
async function loadOwnerContacts(){
 if(ownerContactsLoading)return;ownerContactsLoading=true;
 try{const result=await api('/api/contacts');ownerContacts=result.groups.flatMap(g=>g.contacts);if($('taskEditor').open)renderOwnerSuggestions();}
 catch{if($('editTaskOwner').value.startsWith('@')){$('ownerSuggestions').replaceChildren(text('p','Contacts unavailable. You can still type a name.','muted small'));$('ownerSuggestions').hidden=false;}}
 finally{ownerContactsLoading=false;}
}
function renderOwnerSuggestions(){
 const root=$('ownerSuggestions'),value=$('editTaskOwner').value;
 $('editTaskOwner').setCustomValidity(value.startsWith('@')?'Choose a contact or remove @ to enter a name.':'');root.replaceChildren();root.hidden=!value.startsWith('@');if(root.hidden)return;
 const query=value.slice(1).trim().toLowerCase();
 const people=[{name:currentOwnerName(),email:currentOwnerEmails()[0]||'',self:true},...ownerContacts];
 const seen=new Set();const matches=people.filter(p=>{const id=p.email||p.name;if(seen.has(id))return false;seen.add(id);return (p.name+' '+p.email).toLowerCase().includes(query);}).slice(0,8);
 if(!matches.length){root.append(text('p',ownerContactsLoading?'Loading contacts…':'No matching contacts. Enter a name without @ to use it.','muted small'));return;}
 for(const person of matches){const b=text('button','','owner-option');b.type='button';b.append(text('strong',person.name+(person.self?' (you)':'')),text('small',person.email));
 b.onclick=()=>{$('editTaskOwner').value=person.self?currentOwnerName():person.name===person.email?person.email:person.name+' <'+person.email+'>';$('editTaskType').value=person.self||currentOwnerEmails().includes(person.email.toLowerCase())?'my':'others';root.hidden=true;$('editTaskOwner').dispatchEvent(new Event('input',{bubbles:true}));$('editTaskOwner').focus();};root.append(b);}
}
$('editTaskOwner').addEventListener('input',renderOwnerSuggestions);
$('editTaskOwner').addEventListener('change',()=>{const value=$('editTaskOwner').value.trim();if(!value||value.startsWith('@'))return;const mine=value.toLowerCase()===currentOwnerName().toLowerCase()||value.toLowerCase()==='me'||currentOwnerEmails().includes((value.match(/<([^>]+)>/)?.[1]||value).toLowerCase());$('editTaskType').value=mine?'my':value==='Owner unclear'?'unclear':'others';$('editTaskType').dispatchEvent(new Event('input',{bubbles:true}));});
$('editTaskOwner').addEventListener('keydown',e=>{if(e.key==='Escape'){$('ownerSuggestions').hidden=true;e.preventDefault();e.stopPropagation();}if(e.key==='ArrowDown'&&!$('ownerSuggestions').hidden){e.preventDefault();$('ownerSuggestions').querySelector('button')?.focus();}});
$('ownerSuggestions').addEventListener('keydown',e=>{const buttons=[...$('ownerSuggestions').querySelectorAll('button')];const index=buttons.indexOf(document.activeElement);if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();buttons[(index+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();}if(e.key==='Escape'){$('ownerSuggestions').hidden=true;$('editTaskOwner').focus();e.preventDefault();e.stopPropagation();}});

function addTaskCollapse(card,top,task){
 let collapsed=taskCardOverrides.has(task.id)?taskCardOverrides.get(task.id):compactTaskCards;
 const button=text('button','','task-collapse');button.type='button';
 function apply(){card.classList.toggle('task-collapsed',collapsed);button.textContent=collapsed?'▸':'▾';button.setAttribute('aria-expanded',String(!collapsed));button.setAttribute('aria-label',(collapsed?'Expand task: ':'Collapse task: ')+task.text);button.title=collapsed?'Expand task':'Collapse task';}
 button.onclick=()=>{collapsed=!collapsed;taskCardOverrides.set(task.id,collapsed);apply();};top.prepend(button);apply();
}
function updateTaskDensityButton(){$('toggleTaskCards').textContent=compactTaskCards?'Expand all':'Collapse all';}
$('toggleTaskCards').onclick=()=>{compactTaskCards=!compactTaskCards;taskCardOverrides.clear();try{localStorage.setItem('outlook-compact-tasks',String(compactTaskCards));}catch{}updateTaskDensityButton();boardFingerprint='';renderTaskBoard();};
updateTaskDensityButton();

let confettiCleanup;
function celebrateTaskDone(){
 clearTimeout(confettiCleanup);document.querySelector('.task-confetti')?.remove();
 if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 const layer=text('div','','task-confetti');layer.setAttribute('aria-hidden','true');document.body.append(layer);
 for(let i=0;i<48;i++){
  const piece=text('i','','confetti-piece');layer.append(piece);
  const angle=Math.random()*Math.PI*2,distance=100+Math.random()*Math.min(innerWidth*.42,460);
  const x=Math.cos(angle)*distance,y=Math.sin(angle)*distance*.65;
  piece.animate([{transform:'translate(0,0) rotate(0deg)',opacity:1},{transform:`translate(${x}px,${y}px) rotate(${180+i*17}deg)`,opacity:1,offset:.65},{transform:`translate(${x*1.15}px,${y+100}px) rotate(${360+i*23}deg)`,opacity:0}],{duration:950+Math.random()*200,easing:'cubic-bezier(.15,.65,.4,1)',fill:'forwards'});
 }
 confettiCleanup=setTimeout(()=>layer.remove(),1200);
}
