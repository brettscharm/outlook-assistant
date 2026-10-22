'use strict';
let ownerContacts=[],ownerContactsLoading=false,ownerContactsLoadedAt=0;
let compactTaskCards=false;const taskCardOverrides=new Map();
try{compactTaskCards=localStorage.getItem('outlook-compact-tasks')==='true';}catch{}
let boardLanes=[],laneDraft=[],draggedTask=null;
let taskPage=1,taskViewChosen=false,revealSavedTask=null;
let taskReview=null,taskSaved=[],taskView='review',taskEditor=null,taskFingerprint='',taskLoading=false,scanFormReady=false,scanPanelSettled=false;
window.taskFormDirty=false;
window.taskScanRunning=false;
const localToday=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
function taskDeadline(t){
 if(t.deadline?.kind==='meeting'&&t.deadline.due_at){
  const time=new Date(t.deadline.due_at),delta=time-Date.now();
  if(!Number.isNaN(time.getTime())){const urgency=t.completed?'':delta<0?'overdue':delta<86400000?'today':delta<3*86400000?'soon':'';return {due:t.deadline.due_at,day:`${time.getFullYear()}-${String(time.getMonth()+1).padStart(2,'0')}-${String(time.getDate()).padStart(2,'0')}`,sortTime:time.getTime(),label:(urgency==='overdue'?'Overdue · ':'')+time.toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}),overdue:urgency==='overdue',urgency};}
 }

 const due=/^\d{4}-\d{2}-\d{2}$/.test(t.due_date||'')?t.due_date:'';
 const days=due?Math.round((Date.parse(due+'T00:00:00Z')-Date.parse(localToday()+'T00:00:00Z'))/86400000):null;
 const date=due?new Date(due+'T12:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'}):'No deadline stated';
 const urgency=t.completed||!due?'':days<0?'overdue':days===0?'today':days<=3?'soon':'';
 const prefix=urgency==='overdue'?'Overdue':urgency==='today'?'Due today':urgency==='soon'?(days===1?'Due tomorrow':'Due in '+days+' days'):'';
 return {due,day:due,sortTime:due?new Date(due+'T23:59:59').getTime():null,label:prefix?prefix+' · '+date:date,overdue:urgency==='overdue',urgency};
}
function compareTasks(a,b,mode){
 const ranks={none:0,low:1,medium:2,high:3};
 const dateCompare=(a,b,descending=false)=>{const x=taskDeadline(a).sortTime,y=taskDeadline(b).sortTime;if(x==null||y==null)return x!=null?-1:y!=null?1:0;return (x-y)*(descending?-1:1);};
 if(mode.startsWith('priority')){const x=ranks[a.priority]||0,y=ranks[b.priority]||0;if(!x||!y){if(x!==y)return x?-1:1;}else if(x!==y)return (x-y)*(mode==='priority-desc'?-1:1);}
 return dateCompare(a,b,mode==='due-desc')||String(a.id).localeCompare(String(b.id));
}

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
function editTask(item,origin){taskEditor={item,origin};$('taskEditorTitle').textContent=origin==='review'?'Review before adding':origin==='new'?'Add a task':'Task';$('editTaskText').value=item.text||'';$('editTaskDescription').value=item.description||'';$('editTaskCoOwners').value=(item.co_owners||[]).join('\n');$('editTaskCoOwners').setCustomValidity('');$('coOwnerSuggestions').hidden=true;$('editTaskCoOwners').setAttribute('aria-expanded','false');$('taskEmailPeopleStatus').textContent='';$('editTaskSource').value=item.source_type||(item.email_id?'email':'other');$('editTaskSourceUrl').value=item.source_url||'';$('editTaskType').value=item.type||'my';$('editTaskOwner').value=$('editTaskType').value==='my'?currentOwnerName():item.owner||item.assignee||'';$('editTaskDue').value=item.due_date||'';initializeTaskSchedule(item);$('editTaskPriority').value=item.priority||'none';window.fillProjectSelect?.($('editTaskProject'),item.project_id||'');refreshTaskProjectColor();$('editTaskEvidence').textContent=item.evidence||'';$('editTaskEvidence').hidden=!item.evidence;$('editTaskDateNote').textContent=[item.due_evidence?'Deadline in email: “'+item.due_evidence+'”':'',item.due_note||''].filter(Boolean).join(' · ');$('saveTaskEdit').textContent=item.action_type==='complete'?'Mark completed':'Add task';$('saveTaskEdit').hidden=origin==='saved';$('closeTaskEditor').textContent=origin==='saved'?'Done':'Close';$('retryTaskSave').hidden=true;$('taskSaveStatus').textContent=origin==='saved'?'All changes saved':'';$('ownerSuggestions').hidden=true;$('editTaskOwner').setCustomValidity('');$('taskEditor').showModal();progressRoot.hidden=origin!=='saved';window.flushTaskProgress=null;if(origin==='saved')openTaskProgress(item);window.mountTaskFiles($('taskEditor'),'task',origin==='saved'?item.id:null);loadOwnerContacts();taskLastSaved=JSON.stringify(taskEditValues());}
function dismissMenu(item){
 const details=document.createElement('details');details.className='dismiss-menu';
 details.append(text('summary','Dismiss with feedback'));details.append(text('p','Helps guide future suggestions. Restore removes this feedback.','muted small'));
 const choices=text('div','','dismiss-reasons');choices.setAttribute('role','group');choices.setAttribute('aria-label','Dismiss reason for '+item.text);
 let saving=false;
 for(const [key,label] of Object.entries(taskReview?.reasons||{}).filter(([key])=>key!=='quick')){
  const button=text('button',label);button.type='button';
  button.onclick=async()=>{
   if(saving)return;saving=true;choices.setAttribute('aria-busy','true');
   choices.querySelectorAll('button').forEach(b=>b.disabled=true);
   try{await api('/api/task-review',{id:item.id,action:'dismiss',reason:key});await loadTaskWorkspace();notice('Dismissed: '+label+'.');const undo=text('button','Undo');undo.dataset.noticeAction='true';undo.onclick=()=>busy(undo,async()=>{await api('/api/task-review',{id:item.id,action:'restore'});await loadTaskWorkspace();notice('Task restored.');});$('notice').append(undo);}
   catch(e){notice(e.message,'error');}
   finally{saving=false;choices.removeAttribute('aria-busy');choices.querySelectorAll('button').forEach(b=>b.disabled=false);}
  };
  choices.append(button);
 }
 const preferences=text('button','Task discovery preferences','dismiss-preferences');preferences.type='button';preferences.onclick=()=>{details.open=false;document.querySelector('.scan-panel').open=true;$('taskExcludedDomains').focus();};choices.append(preferences);details.append(choices);return details;
}
function taskAddedLabel(value){if(!value)return '';const added=new Date(value);return Number.isNaN(added.getTime())?'':'Added '+added.toLocaleString(undefined,{month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit'});}
function appendTaskAdded(card,t){const label=taskAddedLabel(t.created_at);if(!label)return;const stamp=text('time',label,'task-added muted small');stamp.dateTime=t.created_at;stamp.title=new Date(t.created_at).toLocaleString(undefined,{timeZoneName:'short'});card.append(stamp);}
function taskCard(t,origin){if(origin==='saved')return savedTaskCard(t);const card=text('article','','action-card'+(t.completed?' task-completed':''));const top=text('div','','action-card-top');const title=text('h3',t.text);if(origin==='review')window.addReviewCheckbox?.(top,t);top.append(title);if(t.project_id){const project=window.projectRows?.find(p=>p.id===t.project_id);if(project){const chip=text('button',project.name,'company-chip project-link');chip.onclick=()=>window.openProject?.(project.id);top.append(chip);}}if(t.company)top.append(text('span',t.company,'company-chip'));card.append(top);if(t.description){const description=text('p','','task-description');renderEmailLinks(description,t.description);card.append(description);}else if(t.evidence)card.append(text('p','From the email: “'+t.evidence+'”','task-description'));const meta=text('div','','task-meta');const owner=t.owner||t.assignee||'Owner unclear';const due=taskDeadline(t);meta.append(ownerChip(t),text('span',due.label,'due-chip '+due.urgency));if(t.priority&&t.priority!=='none')meta.append(text('span',t.priority[0].toUpperCase()+t.priority.slice(1)+' priority','priority-chip priority-'+t.priority));if(t.due_note)meta.append(text('span','Check deadline','due-chip caution'));meta.append(text('span',({email:'Email',slack:'Slack',teams:'Teams',meeting:'Meeting',other:'Other'})[t.source_type||(t.email_id?'email':'other')],'source-chip'));card.append(meta);if(t.source_url){try{const url=new URL(t.source_url);if(['https:','http:'].includes(url.protocol)){const link=text('a','Open source link','task-source-link');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';card.append(link);}}catch{}}if(t.email_id)card.append(taskSource(t));if(t.evidence){const details=document.createElement('details');details.className='evidence';details.append(text('summary','Why this is a task'),text('blockquote',t.evidence));if(t.owner_evidence&&t.owner_evidence!==t.evidence)details.append(text('p','Owner: “'+t.owner_evidence+'”','muted small'));if(t.due_evidence)details.append(text('p','Deadline: “'+t.due_evidence+'”','muted small'));card.append(details);}appendTaskAdded(card,t);const actions=text('div','','actions task-card-actions');if(origin==='review'){const add=text('button',t.action_type==='complete'?'Mark task completed':'Review & add','primary');add.onclick=()=>t.action_type==='complete'?busy(add,async()=>{await api('/api/task-review',{action:'accept',id:t.id});celebrateTaskDone();await loadTaskWorkspace();notice('Task marked completed. Reopen it from the Done lane if needed.');}):editTask(t,'review');const quick=text('button','×','task-quick-dismiss');quick.type='button';quick.title='Dismiss without feedback';quick.setAttribute('aria-label','Dismiss without feedback: '+t.text);quick.onclick=()=>busy(quick,async()=>{await api('/api/task-review',{id:t.id,action:'dismiss',reason:'quick'});await loadTaskWorkspace();notice('Dismissed. Restore it from Dismissed.');const undo=text('button','Undo');undo.dataset.noticeAction='true';undo.onclick=()=>busy(undo,async()=>{await api('/api/task-review',{id:t.id,action:'restore'});await loadTaskWorkspace();notice('Task restored.');});$('notice').append(undo);});top.append(quick);actions.append(add,dismissMenu(t));}else if(origin==='dismissed'){actions.append(text('span',taskReview.reasons[t.reason]||'Dismissed','muted small'));const restore=text('button','Restore');restore.onclick=()=>busy(restore,async()=>{await api('/api/task-review',{action:'restore',id:t.id});await loadTaskWorkspace();});actions.append(restore);}else{const complete=text('button',t.completed?'Reopen':'Mark done');complete.onclick=()=>busy(complete,async()=>{const wasDone=t.completed;await api('/api/tasks',{action:'toggle',id:t.id});if(!wasDone)celebrateTaskDone();await loadTaskWorkspace();});const edit=text('button','Open task');edit.onclick=()=>editTask(t,'saved');actions.append(complete,edit);}if(origin==='saved')card.append(taskProgressSummary(t));card.append(actions);if(origin==='saved')addTaskCollapse(card,top,t);return card;}
function renderTaskList(){if(!taskReview)return;const query=$('taskSearch').value.trim().toLowerCase(),filter=$('taskDueFilter').value;let items,origin;
if(taskView==='review'||taskView==='dismissed'){origin=taskView;items=taskReview.suggestions.filter(t=>t.status===taskView);}else{origin='saved';items=taskSaved.filter(t=>taskView==='done'?t.completed:!t.completed&&(taskView==='all'||(taskView==='my'?t.type==='my':t.type!=='my')));}
items=items.filter(t=>{const due=taskDeadline(t);return (!query||(t.text+' '+(t.description||'')+' '+(t.source_type||'')+' '+(t.owner||t.assignee||'')+' '+(t.company||'')+' '+(t.email_subject||'')).toLowerCase().includes(query))&&(filter==='all'||filter==='overdue'&&due.overdue||filter==='today'&&due.day===localToday()||filter==='upcoming'&&due.day>localToday()||filter==='none'&&!due.due);});
items.sort((a,b)=>compareTasks(a,b,$('reviewSort').value));window.updateReviewSelection?.(items,origin);
if(revealSavedTask){const index=items.findIndex(revealSavedTask);if(index>=0){taskPage=Math.floor(index/20)+1;revealSavedTask=null;}}
taskPage=Math.min(taskPage,Math.max(1,Math.ceil(items.length/20)));
const fingerprint=JSON.stringify([items,taskView,query,filter,taskPage,localToday()]);if(fingerprint===taskFingerprint)return;taskFingerprint=fingerprint;listPager('taskPages',items.length,taskPage,20,page=>{taskPage=page;taskFingerprint='';renderTaskList();$('taskPages').scrollIntoView({block:'nearest'});});
const root=$('taskList');root.replaceChildren();if(!items.length){const empty=text('div','','task-empty');empty.append(text('h3',taskView==='review'?'Nothing waiting for review.':'No tasks in this view.'),text('p',taskView==='review'?'New suggestions appear here automatically.':'Try another filter or add a task.','muted'));root.append(empty);}for(const item of items.slice((taskPage-1)*20,taskPage*20))root.append(taskCard(item,origin));}
window.loadTaskWorkspace=function(){if(taskLoading)return taskLoading;taskLoading=(async()=>{try{loadOwnerContacts();const [review,saved,lanes]=await Promise.all([api('/api/task-review'),api('/api/tasks'),api('/api/task-lanes')]);boardLanes=lanes;taskReview=review;$('reviewBadge').textContent=review.suggestions.filter(t=>t.status==='review').length;taskSaved=[...(saved.my_tasks||[]).map(t=>({...t,type:t.type||'my'})),...(saved.others_tasks||[]).map(t=>({...t,type:t.type||'others'}))];window.taskScanRunning=review.job.running;if(lastSuccessfulSync&&!state.busy){$('sync').title=syncTimeLabel()+(review.job.running?' · Checking tasks…':review.job.status==='error'?' · Task check failed':review.last_check?' · Tasks checked '+new Date(review.last_check).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}):'');}$('identityPrompt').hidden=review.identity_ready;$('findTasks').disabled=review.job.running||state.pending>0;$('stopScan').hidden=!review.job.running;$('scanProgress').max=Math.max(1,review.job.total);$('scanProgress').value=review.job.scanned;$('scanProgress').hidden=!review.job.running;
const auto=review.automatic_state;
$('scanScheduleLabel').textContent=auto==='paused'?'Automatic tasks paused':'Finding tasks automatically';
$('toggleTaskAuto').textContent=review.options.interval?'Pause':'Resume';
const status=auto==='paused'?'Resume to find new tasks.':auto==='identity'?'Add your name and work email to start.':auto==='bob'?'Test your Bob connection in Settings to start.':'Watching for new email'+(review.last_check?' · Last checked '+new Date(review.last_check).toLocaleTimeString(): ' · No check completed yet');
$('taskScanStatus').textContent=review.job.running?review.job.message:review.job.status==='error'?review.job.message:status;
if(!scanFormReady){const initial=restored?.scanDraft||review.options;$('scanSince').value=initial.since;$('scanMode').value=initial.mode;$('scanInterval').value=initial.interval;$('taskExcludedDomains').value=Array.isArray(initial.excluded_domains)?initial.excluded_domains.join('\n'):(initial.excluded_domains||'');window.taskFormDirty=!!restored?.scanDraft;scanFormReady=true;}if(!scanPanelSettled&&!review.job.running&&(review.suggestions.length||taskSaved.length)){document.querySelector('.scan-panel').open=false;scanPanelSettled=true;}
const stats=[['To review',review.suggestions.filter(t=>t.status==='review').length,'review'],['My active tasks',taskSaved.filter(t=>!t.completed&&t.type==='my').length,'my'],['Others / unclear',taskSaved.filter(t=>!t.completed&&t.type!=='my').length,'others'],['Overdue',taskSaved.filter(t=>taskDeadline(t).overdue).length,'overdue']];const statsKey=JSON.stringify(stats);if($('taskStats').dataset.fingerprint!==statsKey){$('taskStats').dataset.fingerprint=statsKey;$('taskStats').replaceChildren();for(const [label,count,target] of stats){const b=text('button','','task-stat');b.append(text('span',label),text('strong',count));b.onclick=()=>{$('taskDueFilter').value=target==='overdue'?'overdue':'all';setTaskView(target==='overdue'?'all':target);};$('taskStats').append(b);}}renderTaskList();renderTaskBoard();window.renderProjectCards?.(taskSaved);if(state.selected&&document.querySelector('.email-task-summary'))renderEmailSummary(state.selected,document.querySelector('.email-task-summary'));
}finally{taskLoading=false;}})();return taskLoading;};
function scanValues(){return {since:$('scanSince').value,mode:$('scanMode').value,interval:Number($('scanInterval').value),excluded_domains:$('taskExcludedDomains').value};}
let scanSaveTimer,scanSavePromise=null;
window.flushScanSettings=async()=>{
 clearTimeout(scanSaveTimer);if(scanSavePromise){if(!await scanSavePromise)return false;return window.flushScanSettings();}if(!window.taskFormDirty)return true;if(!$('scanForm').reportValidity())return false;
 scanSavePromise=(async()=>{try{while(window.taskFormDirty){const values=scanValues();await api('/api/task-scan-settings',values);window.taskFormDirty=JSON.stringify(values)!==JSON.stringify(scanValues());}$('scanSaveStatus').textContent='All changes saved';return true;}catch(e){$('scanSaveStatus').textContent='Not saved: '+e.message;return false;}})();try{return await scanSavePromise;}finally{scanSavePromise=null;}
};
$('scanForm').oninput=()=>{window.taskFormDirty=true;clearTimeout(scanSaveTimer);$('scanSaveStatus').textContent='Saving…';scanSaveTimer=setTimeout(()=>window.flushScanSettings(),700);};
window.getTaskScanDraft=()=>window.taskFormDirty?scanValues():null;
$('scanForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{await api('/api/task-scan-settings',scanValues());window.taskFormDirty=false;await loadTaskWorkspace();notice('Scan settings saved.');});};
$('findTasks').onclick=()=>busy($('findTasks'),async()=>{if(!$('scanForm').reportValidity())return;await api('/api/task-scan-settings',scanValues());window.taskFormDirty=false;await api('/api/task-scan',scanValues());setTaskView('review');await loadTaskWorkspace();});
$('toggleTaskAuto').onclick=()=>busy($('toggleTaskAuto'),async()=>{clearTimeout(scanSaveTimer);const interval=taskReview.options.interval?0:15;$('scanInterval').value=interval;await api('/api/task-scan-settings',scanValues());window.taskFormDirty=false;}).finally(()=>loadTaskWorkspace());
$('stopScan').onclick=()=>busy($('stopScan'),async()=>{await api('/api/task-scan-stop',{});await loadTaskWorkspace();});
$('setIdentity').onclick=()=>{view('context');$('contextForm').elements.full_name.focus();};
$('manualTask').onclick=()=>editTask({type:'my',owner:currentOwnerName(),project_id:projectRows.some(p=>p.id===$('boardProject').value)?$('boardProject').value:''},'new');
async function closeTaskPanel(){
 if(window.flushTaskProgress&&await window.flushTaskProgress()===false)return;
 if(taskEditor?.origin==='saved'&&await window.flushTaskEdits()===false)return;
 await loadTaskWorkspace();
 $('taskEditor').close();
}
$('closeTaskEditor').onclick=closeTaskPanel;
$('taskEditor').oncancel=e=>{e.preventDefault();closeTaskPanel();};
$('taskEditorForm').onsubmit=e=>{e.preventDefault();if(taskEditor?.origin==='saved'){closeTaskPanel();return;}busy(e.submitter,async()=>{
 const {item,origin}=taskEditor;
 const values={id:item.id,text:$('editTaskText').value,description:$('editTaskDescription').value,source_type:$('editTaskSource').value,source_url:$('editTaskSourceUrl').value,type:$('editTaskType').value,owner:$('editTaskOwner').value,co_owners:$('editTaskCoOwners').value.split(/\n/).map(v=>v.trim()).filter(Boolean),project_id:$('editTaskProject').value,priority:$('editTaskPriority').value,due_date:$('editTaskDue').value,...taskScheduleValues()};
 clearTimeout(taskEditTimer);
 if(window.flushTaskProgress&&await window.flushTaskProgress()===false)return;
 await api(origin==='review'?'/api/task-review':'/api/tasks',{...values,action:origin==='review'?'accept':origin==='new'?'add':'edit'});
 $('taskEditor').close();
 // Finish any earlier refresh before reading the newly committed task.
 if(taskLoading)await taskLoading;
 await loadTaskWorkspace();
 if(origin==='review'){
  notice('Added to Tasks.');
  return;
 }
 $('taskSearch').value='';$('boardSearch').value='';$('taskDueFilter').value='all';if($('boardProject').value&&$('boardProject').value!=='unassigned')$('boardProject').value=values.project_id||'unassigned';try{localStorage.setItem('outlook-board-project',$('boardProject').value);}catch{}
 const target=origin==='review'?taskSaved.find(t=>t.suggestion_id===item.id):origin==='saved'?taskSaved.find(t=>t.id===item.id):taskSaved.find(t=>t.text===values.text.trim()&&t.type===values.type);
 revealSavedTask=t=>target?t.id===target.id:origin==='review'?t.suggestion_id===item.id:t.text===values.text.trim();
 view('tasks');
 taskFingerprint='';renderTaskBoard();
 $('taskBoard').scrollIntoView({block:'start'});

});};
document.querySelectorAll('[data-task-view]').forEach(b=>b.onclick=()=>setTaskView(b.dataset.taskView));$('taskSearch').oninput=()=>{taskPage=1;renderTaskList();};$('taskDueFilter').onchange=()=>{taskPage=1;renderTaskList();};
window.mountEmailTasks=function(id,root){const panel=text('section','','email-task-summary');root.insertBefore(panel,root.querySelector('.body-state'));renderEmailSummary(id,panel);};
async function renderEmailSummary(id,panel){try{const review=await api('/api/task-review?'+new URLSearchParams({email_id:id}));if(state.selected!==id||!panel.isConnected)return;const items=review.suggestions.filter(t=>t.status!=='dismissed');const fingerprint=JSON.stringify([items,review.email_scanned,review.job.running]);if(panel.dataset.fingerprint===fingerprint)return;panel.dataset.fingerprint=fingerprint;panel.replaceChildren();const heading=text('div','','email-task-heading');heading.append(text('h3','Actions in this email'));const scan=text('button',review.job.running?'Scan in progress…':'Review this email');scan.disabled=review.job.running;scan.onclick=()=>busy(scan,async()=>{await api('/api/task-scan',{email_id:id,mode:'all'});await loadTaskWorkspace();});heading.append(scan);panel.append(heading);if(!items.length){panel.append(text('p',review.email_scanned?'No action items found.':'No tasks found yet.','muted small'));return;}const mine=items.filter(t=>t.type==='my');if(!mine.length)panel.append(text('p','No task clearly assigned to you.','muted small'));const groups=new Map();for(const item of items){const label=item.type==='my'?'YOUR TASKS':item.type==='unclear'?'OWNER UNCLEAR':(item.owner||'OTHER OWNER').toUpperCase()+"’S TASKS";if(!groups.has(label))groups.set(label,[]);groups.get(label).push(item);}for(const [label,tasks] of groups){panel.append(text('h4',label));for(const item of tasks){const row=text('div','','email-action');row.append(text('strong',item.text),text('span',taskDeadline(item).label,'muted small'));if(item.description)row.append(text('p',item.description,'task-description'));if(item.status==='review'){const add=text('button','Review & add');add.onclick=()=>editTask(item,'review');row.append(add);}else row.append(text('span',item.completed?'Completed':'Added to tasks','muted small'));panel.append(row);}}}catch(e){panel.textContent='Task summary unavailable: '+e.message;}}
loadTaskWorkspace().catch(e=>notice(e.message));setInterval(()=>{if(!document.hidden&&!$('taskEditor').open&&!document.querySelector('.dismiss-menu[open]'))loadTaskWorkspace().catch(()=>{});},5000);

let taskEditTimer,taskEditPromise=null,taskLastSaved='';
function taskEditValues(){return {action:'edit',id:taskEditor?.item.id,text:$('editTaskText').value,description:$('editTaskDescription').value,source_type:$('editTaskSource').value,source_url:$('editTaskSourceUrl').value,type:$('editTaskType').value,owner:$('editTaskOwner').value,co_owners:$('editTaskCoOwners').value.split(/\n/).map(v=>v.trim()).filter(Boolean),project_id:$('editTaskProject').value,priority:$('editTaskPriority').value,due_date:$('editTaskDue').value,...taskScheduleValues()};}
window.flushTaskEdits=async()=>{
 clearTimeout(taskEditTimer);
 if(taskEditor?.origin!=='saved'||!$('taskEditor').open)return true;
 if(taskEditPromise){const ok=await taskEditPromise;if(!ok)return false;return window.flushTaskEdits();}
 if(JSON.stringify(taskEditValues())===taskLastSaved)return true;
 if(!$('taskEditorForm').reportValidity()){$('taskSaveStatus').textContent='Check the highlighted field to save.';return false;}
 const editor=taskEditor;state.pending++;
 taskEditPromise=(async()=>{
  try{
   while(taskEditor===editor){
    const values=taskEditValues(),snapshot=JSON.stringify(values);if(snapshot===taskLastSaved)break;
    if(!$('taskEditorForm').checkValidity()){$('taskSaveStatus').textContent='Check the highlighted field to save.';return false;}
    $('taskSaveStatus').textContent='Saving…';$('retryTaskSave').hidden=true;
    await api('/api/tasks',values);taskLastSaved=snapshot;taskFingerprint='';boardFingerprint='';
   }
   $('taskSaveStatus').textContent='All changes saved';return true;
  }catch(e){$('taskSaveStatus').textContent='Not saved · '+e.message;$('retryTaskSave').hidden=false;return false;}
  finally{state.pending--;}
 })();
 try{return await taskEditPromise;}finally{taskEditPromise=null;}
};
function queueTaskEdit(){if(taskEditor?.origin!=='saved')return;clearTimeout(taskEditTimer);if(JSON.stringify(taskEditValues())===taskLastSaved)return;$('taskSaveStatus').textContent='Saving…';taskEditTimer=setTimeout(()=>window.flushTaskEdits(),650);}
$('taskEditorForm').addEventListener('input',queueTaskEdit);$('taskEditorForm').addEventListener('change',queueTaskEdit);
$('retryTaskSave').onclick=()=>window.flushTaskEdits();

const boardLimits={my:20,others:20,done:20};
let boardFingerprint='';
let showCompletedTasks=true;
try{showCompletedTasks=localStorage.getItem('outlook-show-completed')!=='false';}catch{}
window.openTaskPage=id=>{if(id==='tasks')renderTaskBoard();else{taskFingerprint='';renderTaskList();}};
function renderTaskBoard(){
 const query=$('boardSearch').value.trim().toLowerCase();
 const project=$('boardProject').value;
 const items=taskSaved.filter(t=>(!project||(project==='unassigned'?!t.project_id:t.project_id===project))).filter(t=>!query||[t.text,t.description,t.source_type,t.owner,t.assignee,t.company,t.email_subject].filter(Boolean).join(' ').toLowerCase().includes(query));
 window.renderBoardContext?.(items);
 items.sort((a,b)=>compareTasks(a,b,$('boardSort').value));
 const lanes=boardLanes.map(lane=>{boardLimits[lane.id]??=20;return [lane.id,lane.name,items.filter(t=>taskLane(t)===lane.id)];});
 if(revealSavedTask){for(const [key,,rows] of lanes){const index=rows.findIndex(revealSavedTask);if(index>=0){boardLimits[key]=Math.max(boardLimits[key],index+1);revealSavedTask=null;break;}}}
 const fingerprint=JSON.stringify([lanes,boardLimits,localToday(),showCompletedTasks]);if(draggedTask||fingerprint===boardFingerprint)return;boardFingerprint=fingerprint;
 const root=$('taskBoard');root.replaceChildren();
 for(const [key,label,rows] of lanes){const lane=text('section','','task-lane');lane.setAttribute('aria-label',label);lane.dataset.lane=key;lane.ondragover=e=>{if(draggedTask){e.preventDefault();e.dataTransfer.dropEffect='move';lane.classList.add('drop-target');}};lane.ondragleave=e=>{if(!lane.contains(e.relatedTarget))lane.classList.remove('drop-target');};lane.ondrop=e=>{e.preventDefault();lane.classList.remove('drop-target');const id=draggedTask;draggedTask=null;if(id)moveBoardTask(id,key);};const heading=text('div','','lane-heading');heading.append(text('h2',label),text('span',rows.length,'nav-count'));lane.append(heading);
 if(key==='done'){
 const toggle=text('button',showCompletedTasks?'Hide completed':'Show completed','lane-completed-toggle');
 toggle.id='toggleCompletedTasks';toggle.type='button';toggle.setAttribute('aria-pressed',String(showCompletedTasks));toggle.onclick=toggleCompletedTasks;heading.append(toggle);
 }
 if(key==='done'&&!showCompletedTasks){lane.append(text('p',rows.length?rows.length+' completed '+(rows.length===1?'task hidden.':'tasks hidden.'):'Completed tasks are hidden.','lane-empty'));root.append(lane);continue;}
 if(!rows.length)lane.append(text('p',query?'No matching tasks.':key==='done'?'No completed tasks.':'No tasks.','lane-empty'));
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
async function moveBoardTask(id,lane){const wasDone=taskSaved.find(t=>t.id===id)?.completed;try{await api('/api/tasks',{action:'move',id,lane_id:lane});if(lane==='done'&&!wasDone)celebrateTaskDone();if(taskLoading)await taskLoading;await loadTaskWorkspace();}catch(e){notice(e.message,'error');boardFingerprint='';renderTaskBoard();}}
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

function currentOwnerName(){return $('contextForm').elements.full_name.value.trim()||'Me';}
function currentOwnerEmails(){return $('contextForm').elements.email_addresses.value.toLowerCase().split(/[,;\s]+/).filter(v=>v.includes('@'));}
function ownerFullName(value){const parts=String(value||'').trim().replace(/^"|"$/g,'').split(',');return parts.length===2&&parts.every(p=>p.trim())?parts[1].trim()+' '+parts[0].trim():String(value||'').trim();}
function ownerLabel(task){
 const raw=task.type==='my'?currentOwnerName():task.owner||task.assignee||'Unassigned';
 const email=task.type==='my'?currentOwnerEmails()[0]||'':raw.match(/<([^>]+)>/)?.[1]||(/^[^\s@]+@[^\s@]+$/.test(raw)?raw:'');
 const name=ownerFullName(raw.replace(/\s*<[^>]+>/,''));
 const matches=ownerContacts.filter(p=>email?p.email.toLowerCase()===email.toLowerCase():p.name.toLowerCase()===name.toLowerCase());
 const person=matches.length===1?matches[0]:null;
 const address=person?.email||email,displayName=person?.name||name;
 return [displayName,address&&address!==displayName?address:'',person?.company||''].filter(Boolean).join(' · ');
}
function ownerChip(task){const chip=text('span',ownerLabel(task),'owner-chip');chip.dataset.ownerLabel=task.owner||task.assignee||'';chip.dataset.ownerType=task.type||'';return chip;}
async function loadOwnerContacts(){
 if(ownerContactsLoading||Date.now()-ownerContactsLoadedAt<60000)return;ownerContactsLoading=true;
 try{const result=await api('/api/contacts');ownerContactsLoadedAt=Date.now();ownerContacts=result.groups.flatMap(g=>g.contacts.map(p=>({...p,name:ownerFullName(p.name),company:g.company||''})));document.querySelectorAll('[data-owner-label]').forEach(node=>{node.textContent=ownerLabel({type:node.dataset.ownerType,owner:node.dataset.ownerLabel});});if($('taskEditor').open){renderOwnerSuggestions();renderCoOwnerSuggestions();}}
 catch{if($('editTaskOwner').value.startsWith('@')){$('ownerSuggestions').replaceChildren(text('p','Contacts unavailable. You can still type a name.','muted small'));$('ownerSuggestions').hidden=false;}}
 finally{ownerContactsLoading=false;if($('taskEditor').open)renderCoOwnerSuggestions();}
}
function renderOwnerSuggestions(){
 const root=$('ownerSuggestions'),value=$('editTaskOwner').value;
 $('editTaskOwner').setCustomValidity(value.startsWith('@')?'Choose a contact or remove @ to enter a name.':'');root.replaceChildren();root.hidden=!value.startsWith('@');if(root.hidden)return;
 const query=value.slice(1).trim().toLowerCase();
 const people=[{name:currentOwnerName(),email:currentOwnerEmails()[0]||'',self:true},...ownerContacts];
 const seen=new Set();const matches=people.filter(p=>{const id=p.email||p.name;if(seen.has(id))return false;seen.add(id);return (p.name+' '+p.email).toLowerCase().includes(query);}).slice(0,8);
 if(!matches.length){root.append(text('p',ownerContactsLoading?'Loading contacts…':'No matching contacts. Enter a name without @ to use it.','muted small'));return;}
 for(const person of matches){const b=text('button','','owner-option');b.type='button';b.append(text('strong',person.name+(person.self?' (you)':'')),text('small',[person.email,person.company].filter(Boolean).join(' · ')));
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

for(const id of ['boardSort','reviewSort']){
 try{const saved=localStorage.getItem('outlook-'+id);if([...$(id).options].some(o=>o.value===saved))$(id).value=saved;}catch{}
 $(id).onchange=()=>{try{localStorage.setItem('outlook-'+id,$(id).value);}catch{}taskPage=1;boardFingerprint='';renderTaskBoard();renderTaskList();};
}

$('editTaskType').addEventListener('change',()=>{
 if($('editTaskType').value==='my'){
  $('editTaskOwner').value=currentOwnerName();
  $('editTaskOwner').setCustomValidity('');$('ownerSuggestions').hidden=true;
  $('editTaskOwner').dispatchEvent(new Event('input',{bubbles:true}));
 }
});

function toggleCompletedTasks(){
 showCompletedTasks=!showCompletedTasks;
 try{localStorage.setItem('outlook-show-completed',String(showCompletedTasks));}catch{}
 boardFingerprint='';renderTaskBoard();
};

// Progress lives in its own dialog so background refreshes never replace a draft.
const progressRoot=text('section','','task-progress-panel');progressRoot.id='taskProgress';$('taskEditor').append(progressRoot);
let progressTaskId=null,progressRequest=null;
function progressDraftKey(id){return 'outlook-task-progress-'+id;}
function saveProgressDraft(id,values){try{localStorage.setItem(progressDraftKey(id),JSON.stringify(values));}catch{}}
function taskProgressSummary(task){
 const box=text('div','','task-progress-summary');
 if(task.waiting_on)box.append(text('p','Waiting on '+task.waiting_on,'small'));
 if(task.next_step)box.append(text('p','Next: '+task.next_step,'small'));
 const steps=task.subtasks||[];if(steps.length)box.append(text('span',steps.filter(s=>s.completed).length+' of '+steps.length+' subtasks complete','muted small'));
 const last=(task.updates||[]).at(-1);if(last)box.append(text('p',last.text,'latest-task-update'));
 return box;
}
function openTaskProgress(task){
 progressTaskId=task.id;progressRoot.replaceChildren();
 const heading=text('div','','task-progress-heading');heading.append(text('h3','Progress'));const completion=text('button',task.completed?'Reopen task':'Mark task done');completion.type='button';completion.onclick=()=>busy(completion,async()=>{if(window.flushTaskProgress&&await window.flushTaskProgress()===false)return;await api('/api/tasks',{action:'move',id:task.id,lane_id:task.completed?'todo':'done'});if(!task.completed)celebrateTaskDone();await loadTaskWorkspace();const updated=taskSaved.find(t=>t.id===task.id);if(updated&&$('taskEditor').open)openTaskProgress(updated);});heading.append(completion);progressRoot.append(heading);
 const status=text('p','','muted small');status.setAttribute('role','status');
 const waiting=document.createElement('input'),next=document.createElement('textarea');waiting.maxLength=300;next.maxLength=2000;waiting.value=task.waiting_on||'';next.value=task.next_step||'';
 for(const [name,field] of [['Waiting on',waiting],['Next step',next]]){const label=text('label',name);label.append(field);progressRoot.append(label);}
 const note=document.createElement('textarea');note.rows=3;note.maxLength=4000;note.placeholder='Received pricing. Waiting for approval…';
 const step=document.createElement('input');step.id='taskSubtaskInput';step.setAttribute('aria-label','New subtask');step.maxLength=500;step.placeholder='What needs to be done?';
 try{const draft=JSON.parse(localStorage.getItem(progressDraftKey(task.id))||'null');if(draft){note.value=draft.note||'';step.value=draft.step||'';if(draft.waiting!==undefined)waiting.value=draft.waiting;if(draft.next!==undefined)next.value=draft.next;}}catch{}
 const draft=()=>{const values={note:note.value,step:step.value};if(JSON.stringify({waiting_on:waiting.value,next_step:next.value})!==savedFields)Object.assign(values,{waiting:waiting.value,next:next.value});saveProgressDraft(task.id,values);};
 let chain=Promise.resolve(),fieldsTimer;let savedFields=JSON.stringify({waiting_on:task.waiting_on||'',next_step:task.next_step||''});
 const saveFields=()=>{clearTimeout(fieldsTimer);draft();const values={waiting_on:waiting.value,next_step:next.value};if(JSON.stringify(values)===savedFields)return chain;status.textContent='Saving…';chain=chain.catch(()=>{}).then(()=>api('/api/task-progress',{id:task.id,action:'set_waiting',...values})).then(()=>{savedFields=JSON.stringify(values);draft();status.textContent='Saved';return loadTaskWorkspace();}).catch(e=>{status.textContent='Not saved: '+e.message;return false;});progressRequest=chain;return chain;};
 window.flushTaskProgress=saveFields;
 waiting.oninput=next.oninput=()=>{draft();clearTimeout(fieldsTimer);fieldsTimer=setTimeout(saveFields,500);};waiting.onchange=saveFields;next.onchange=saveFields;note.oninput=draft;step.oninput=draft;
 const checklist=text('section');checklist.append(text('h3','Subtasks'));
 for(const item of task.subtasks||[]){const label=text('label','','checklist-row');const check=document.createElement('input');check.type='checkbox';check.checked=item.completed;label.append(check,text('span',item.text));check.onchange=async()=>{check.disabled=true;try{await api('/api/task-progress',{id:task.id,action:'set_subtask',subtask_id:item.id,completed:check.checked});await loadTaskWorkspace();}catch(e){check.checked=!check.checked;status.textContent=e.message;}finally{check.disabled=false;}};checklist.append(label);}
 const addStep=text('button','Add subtask');addStep.type='button';
 const addNote=text('button','Add update');addNote.type='button';
 const post=(button,field,action)=>{let requestId=null;button.onclick=()=>busy(button,async()=>{if(!field.value.trim())return;requestId??=crypto.randomUUID();if(await saveFields()===false)return;await chain;await api('/api/task-progress',{id:task.id,action,text:field.value,request_id:requestId});requestId=null;field.value='';draft();await loadTaskWorkspace();const updated=taskSaved.find(t=>t.id===task.id);if(updated&&$('taskEditor').open&&progressTaskId===task.id){openTaskProgress(updated);if(action==='add_subtask')focusSubtaskInput();}});};
 post(addStep,step,'add_subtask');post(addNote,note,'add_update');step.onkeydown=e=>{if(e.key==='Enter'&&!e.isComposing){e.preventDefault();addStep.click();}};
 const stepLabel=text('label','New subtask');stepLabel.append(step);checklist.append(stepLabel,addStep);progressRoot.insertBefore(checklist,heading.nextSibling);
 const noteLabel=text('label','Update');noteLabel.append(note);progressRoot.append(noteLabel,addNote,status);
 const history=text('section','','task-update-history');history.append(text('h3','Updates'));
 for(const update of [...(task.updates||[])].reverse()){const row=text('article');row.append(text('small',[update.author,date(update.created_at,true)].filter(Boolean).join(' · ')));const body=text('p');renderEmailLinks(body,update.text);row.append(body);history.append(row);}if(!(task.updates||[]).length)history.append(text('p','No updates yet.','muted'));progressRoot.append(history);
 const share=text('button','Export task');share.type='button';share.onclick=()=>busy(share,()=>exportTaskHandoff(task));progressRoot.append(share);
}
const handoffInput=document.createElement('input');handoffInput.type='file';handoffInput.accept='.json,application/json';handoffInput.hidden=true;document.body.append(handoffInput);
const importTaskButton=text('button','Import task');importTaskButton.type='button';$('boardOptionsContent').append(importTaskButton);importTaskButton.onclick=()=>handoffInput.click();
handoffInput.onchange=async()=>{const file=handoffInput.files[0];if(!file)return;try{if(file.size>250000)throw Error('Choose a task handoff file smaller than 250 KB.');const handoff=JSON.parse(await file.text());if(!confirm('Add this task to your board?\n\n'+String(handoff.task?.text||'Untitled').slice(0,500)))return;await api('/api/task-import',{handoff});await loadTaskWorkspace();}catch(e){notice(e.message,'error');}finally{handoffInput.value='';}};
async function exportTaskHandoff(task){const payload=await api('/api/task-handoff',{id:task.id});const body=JSON.stringify(payload,null,2);if(window.webkit?.messageHandlers?.saveBackup){window.webkit.messageHandlers.saveBackup.postMessage(body);return;}const url=URL.createObjectURL(new Blob([body],{type:'application/json'}));const a=text('a');a.href=url;a.download='Task-handoff.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

function taskScheduleValues(){return {color:$('taskColor').dataset.personalColor||'none',deadline:$('deadlineKind').value==='meeting'?{kind:'meeting',meeting_id:$('deadlineMeeting').value,offset_minutes:Number($('deadlineOffset').value)}:{kind:'date'}};}
let meetingChoiceRequest=0;
function initializeTaskSchedule(item){
 ++meetingChoiceRequest;
 $('taskColor').dataset.personalColor=item.color||'none';$('taskColor').value=item.color||'none';$('deadlineKind').value=item.deadline?.kind==='meeting'?'meeting':'date';$('deadlineOffset').value=String(item.deadline?.offset_minutes||0);
 $('deadlineMeeting').replaceChildren();if(item.deadline?.meeting_id){const option=text('option',item.deadline.subject);option.value=item.deadline.meeting_id;$('deadlineMeeting').append(option);}
 toggleDeadlineFields();if($('deadlineKind').value==='meeting')loadMeetingChoices(item.deadline?.meeting_id);
}
function toggleDeadlineFields(){const meeting=$('deadlineKind').value==='meeting';$('dateDeadlineField').hidden=meeting;$('meetingDeadlineFields').hidden=!meeting;$('deadlineMeeting').required=meeting;}
async function loadMeetingChoices(selected=$('deadlineMeeting').value){
 const request=++meetingChoiceRequest;$('meetingDeadlineStatus').textContent='Loading meetings…';
 try{const data=await api('/api/calendar');if(request!==meetingChoiceRequest)return;const previous=[...$('deadlineMeeting').options].find(o=>o.value===selected);$('deadlineMeeting').replaceChildren();const blank=text('option','Choose a meeting');blank.value='';$('deadlineMeeting').append(blank);for(const event of data.events){const option=text('option',new Date(event.start_time).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})+' · '+event.subject);option.value=event.meeting_id;$('deadlineMeeting').append(option);}if(previous&&![...$('deadlineMeeting').options].some(o=>o.value===selected))$('deadlineMeeting').append(previous);$('deadlineMeeting').value=selected||'';$('meetingDeadlineStatus').textContent='Times in '+Intl.DateTimeFormat().resolvedOptions().timeZone+'. Meeting changes are checked when you sync.';}catch(e){$('meetingDeadlineStatus').textContent=e.message;}
}
$('deadlineKind').onchange=()=>{toggleDeadlineFields();if($('deadlineKind').value==='meeting')loadMeetingChoices();};
function taskPriorityFlag(priority){
 if(!['high','medium','low'].includes(priority))return null;
 const label=priority[0].toUpperCase()+priority.slice(1),flag=text('span','','task-priority-flag priority-'+priority);
 flag.setAttribute('aria-label',label+' priority');flag.title=label+' priority';const icon=text('span','⚑');icon.setAttribute('aria-hidden','true');flag.append(icon,text('span',label));return flag;
}
function savedTaskCard(t){
 const card=text('article','','action-card task-card-v2'+(t.completed?' task-completed':''));card.dataset.color=window.projectRows?.find(p=>p.id===t.project_id)?.color||t.color||'none';applyProjectAccent(card,card.dataset.color);
 const top=text('div','','action-card-top');const title=text('h3',t.text);top.append(title);const priorityFlag=taskPriorityFlag(t.priority);if(priorityFlag)top.append(priorityFlag);card.append(top);addTaskCollapse(card,top,t);
 const meta=text('div','','task-meta');const due=taskDeadline(t);if(due.due)meta.append(text('span',due.label,'due-chip '+due.urgency));if(!due.due)meta.append(text('span','No due date','muted small'));card.append(meta);
 if(t.deadline?.kind==='meeting'){const meeting=text('p','Before '+t.deadline.subject,'task-meeting');if(t.deadline.availability==='unavailable')meeting.append(text('small','Meeting unavailable · Check Calendar'));card.append(meeting);}
 const context=text('div','','task-card-context');context.append(ownerChip(t));const project=window.projectRows?.find(p=>p.id===t.project_id);if(project){const chip=text('button',project.name,'project-link');chip.onclick=()=>window.openProject?.(project.id);context.append(chip);}for(const person of t.co_owners||[])context.append(text('span',person,'owner-chip co-owner-chip'));card.append(context);
 if(t.next_step||t.description){const detail=text('p','','task-description');renderEmailLinks(detail,(t.next_step?'Next: ':'')+(t.next_step||t.description));card.append(detail);}
 if(t.waiting_on)card.append(text('p','Waiting on '+t.waiting_on,'task-waiting'));
 const subs=t.subtasks||[];if(subs.length){const done=subs.filter(s=>s.completed).length;const progress=text('div','','task-subtask-count');progress.append(text('span',done+' / '+subs.length+' subtasks'));const bar=document.createElement('progress');bar.max=subs.length;bar.value=done;bar.setAttribute('aria-label','Subtask completion');progress.append(bar);card.append(progress);}
 appendTaskAdded(card,t);const actions=text('div','','actions task-card-actions');const open=text('button','Open task','task-open');open.onclick=()=>editTask(t,'saved');const complete=text('button',t.completed?'Reopen':'Mark done');complete.onclick=()=>busy(complete,async()=>{await api('/api/tasks',{action:'toggle',id:t.id});if(!t.completed)celebrateTaskDone();await loadTaskWorkspace();});const subtask=text('button','Add subtask');subtask.type='button';subtask.onclick=()=>{editTask(t,'saved');focusSubtaskInput();};actions.append(open,subtask,complete);card.append(actions);
 if(t.email_id){const email=document.createElement('details');email.className='task-email-source';email.append(text('summary','Source email'),taskSource(t));card.append(email);}else if(t.source_url){try{const url=new URL(t.source_url);if(['http:','https:'].includes(url.protocol)){const a=text('a','Open '+(t.source_type||'source')+' link','task-source-link');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';card.append(a);}}catch{}}
 return card;
}
let taskTimezone=Intl.DateTimeFormat().resolvedOptions().timeZone;
setInterval(()=>{const zone=Intl.DateTimeFormat().resolvedOptions().timeZone;if(zone!==taskTimezone){taskTimezone=zone;boardFingerprint='';taskFingerprint='';renderTaskBoard();if($('deadlineKind').value==='meeting'&&$('taskEditor').open)loadMeetingChoices();}else{boardFingerprint='';renderTaskBoard();}},60000);

$('taskEmailPeople').onclick=()=>busy($('taskEmailPeople'),async()=>{
 const people=[$('editTaskOwner').value,...$('editTaskCoOwners').value.split('\n')],recipients=[];
 for(const person of people){const address=person.match(/<([^>]+)>/)?.[1]||person.trim();if(/^[^\s@<>?,;]+@[^\s@<>?,;]+\.[^\s@<>?,;]+$/.test(address)&&!currentOwnerEmails().includes(address.toLowerCase())&&!recipients.includes(address))recipients.push(address);}
 if(!recipients.length){$('taskEmailPeopleStatus').textContent='Add a co-owner’s email address, or an owner with an email address.';return;}
 const subject=$('editTaskText').value,body=[subject,$('editTaskDescription').value,$('editTaskDue').value?'Due: '+$('editTaskDue').value:'',$('editTaskSourceUrl').value].filter(Boolean).join('\n\n');
 await api('/api/task-email-draft',{recipients,subject,body});$('taskEmailPeopleStatus').textContent='Draft requested in your default email app. Review it there before sending.';
});

function refreshTaskProjectColor(){const project=window.projectRows?.find(p=>p.id===$('editTaskProject').value);$('taskColor').querySelector('option[data-project-color]')?.remove();if(project&&/^#[0-9a-f]{6}$/i.test(project.color)){const option=text('option','Project color ('+project.color+')');option.value=project.color;option.dataset.projectColor='true';$('taskColor').append(option);}$('taskColor').disabled=!!project;$('taskColor').value=project?.color||$('taskColor').dataset.personalColor||'none';$('taskColorHelp').textContent=project?'Matches '+project.name+'. Change this color in the project.':'Choose a color for this task.';}
$('editTaskProject').addEventListener('change',refreshTaskProjectColor);$('taskColor').addEventListener('change',()=>{if(!$('taskColor').disabled)$('taskColor').dataset.personalColor=$('taskColor').value;});

// Keep the compact board menu predictable for pointer and keyboard users.
document.addEventListener('click',event=>{if(!$('boardOptions').contains(event.target))$('boardOptions').open=false;});
$('boardOptionsContent').addEventListener('click',event=>{if(event.target.closest('button'))$('boardOptions').open=false;});
$('boardOptionsContent').addEventListener('change',()=>{$('boardOptions').open=false;});
$('boardOptions').addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();$('boardOptions').open=false;$('boardOptions').querySelector('summary').focus();}});

function coOwnerMention(value,caret){
 const start=caret===0?0:value.lastIndexOf('\n',caret-1)+1;
 const next=value.indexOf('\n',caret),end=next<0?value.length:next;
 const line=value.slice(start,end).trimStart();
 return line.startsWith('@')?{start,end,query:line.slice(1).trim().toLowerCase()}:null;
}
function closeCoOwnerSuggestions(){ $('coOwnerSuggestions').hidden=true;$('editTaskCoOwners').setAttribute('aria-expanded','false'); }
function renderCoOwnerSuggestions(){
 const field=$('editTaskCoOwners'),root=$('coOwnerSuggestions');
 field.setCustomValidity(field.value.split('\n').some(line=>line.trimStart().startsWith('@'))?'Choose a contact or remove @ to enter a name.':'');
 const mention=coOwnerMention(field.value,field.selectionStart);root.replaceChildren();if(!mention){closeCoOwnerSuggestions();return;}
 root.hidden=false;field.setAttribute('aria-expanded','true');
 const existing=new Set(field.value.split('\n').filter(line=>!line.trimStart().startsWith('@')).map(line=>(line.match(/<([^>]+)>/)?.[1]||line).trim().toLowerCase()));
 const seen=new Set();const matches=ownerContacts.filter(person=>{const key=(person.email||person.name||'').toLowerCase();if(!key||seen.has(key)||existing.has(key))return false;seen.add(key);return ((person.name||'')+' '+(person.email||'')).toLowerCase().includes(mention.query);}).slice(0,8);
 if(!matches.length){root.append(text('p',ownerContactsLoading?'Loading contacts…':'No matches. Enter a name without @.','muted small'));return;}
 for(const person of matches){const button=text('button','','owner-option');button.type='button';button.append(text('strong',person.name||person.email),text('small',person.email||''));button.onclick=()=>{
 const value=person.email&&person.name&&person.name!==person.email?person.name+' <'+person.email+'>':person.email||person.name;
 const before=field.value.slice(0,mention.start),after=field.value.slice(mention.end);field.value=before+value+(after||'\n');const caret=before.length+value.length+1;
 field.focus();field.setSelectionRange(caret,caret);field.dispatchEvent(new Event('input',{bubbles:true}));closeCoOwnerSuggestions();};root.append(button);}
}
$('editTaskCoOwners').addEventListener('input',renderCoOwnerSuggestions);
$('editTaskCoOwners').addEventListener('click',renderCoOwnerSuggestions);
$('editTaskCoOwners').addEventListener('keydown',event=>{
 if(event.key==='Escape'&&!$('coOwnerSuggestions').hidden){event.preventDefault();event.stopPropagation();closeCoOwnerSuggestions();}
 else if(event.key==='ArrowDown'&&!$('coOwnerSuggestions').hidden){event.preventDefault();$('coOwnerSuggestions').querySelector('button')?.focus();}
 else if(event.key==='Enter'&&!$('coOwnerSuggestions').hidden&&$('coOwnerSuggestions').querySelector('button')){event.preventDefault();$('coOwnerSuggestions').querySelector('button').click();}
});
$('coOwnerSuggestions').addEventListener('keydown',event=>{const buttons=[...$('coOwnerSuggestions').querySelectorAll('button')];const index=buttons.indexOf(document.activeElement);if(['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();buttons[(index+(event.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();}if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closeCoOwnerSuggestions();$('editTaskCoOwners').focus();}});
document.addEventListener('click',event=>{if(event.target!==$('editTaskCoOwners')&&!$('coOwnerSuggestions').contains(event.target))closeCoOwnerSuggestions();});

function focusSubtaskInput(){const input=$('taskSubtaskInput');if(!input)return;input.scrollIntoView({block:'center'});input.focus({preventScroll:true});}
