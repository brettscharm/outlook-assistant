'use strict';
let projectMailCurrent=null,projectMailDiscover=false,projectMailOffset=0,projectMailRequest=0,projectMailTimer;
window.openProjectEmails=p=>{
 clearTimeout(projectMailTimer);projectMailCurrent=p;projectMailDiscover=false;projectMailOffset=0;$('projectMailSearch').value='';$('projectMailTitle').textContent='Emails · '+p.name;
 if(!$('projectMailDialog').open)$('projectMailDialog').showModal();loadProjectEmails();
};
async function loadProjectEmails(){
 if(!projectMailCurrent)return;
 const request=++projectMailRequest,p=projectMailCurrent,discover=projectMailDiscover;
 $('projectMailAdd').textContent=discover?'Back to project emails':'Add emails';$('projectMailSearch').placeholder=discover?'Search all cached mail':'Search project emails';$('projectMailSearch').setAttribute('aria-label',discover?'Search all cached mail':'Search project emails');
 $('projectMailStatus').textContent='Loading…';$('projectMailList').replaceChildren();$('projectMailPrevious').disabled=true;$('projectMailNext').disabled=true;
 try{
  const data=await api('/api/project-emails?'+new URLSearchParams({project_id:p.id,search:$('projectMailSearch').value,offset:projectMailOffset,limit:25,discover}));
  if(request!==projectMailRequest)return;
  if(data.total&&projectMailOffset>=data.total){projectMailOffset=Math.floor((data.total-1)/25)*25;return loadProjectEmails();}
  $('projectMailStatus').textContent=discover?'Choose emails to associate with this project.':data.total+' email'+(data.total===1?'':'s')+' · From tasks and emails you added';
  const root=$('projectMailList');if(!data.items.length)root.append(text('p',discover?'No matching cached emails.':'No linked emails found. Add emails or link a project task to an email.','muted'));
  for(const item of data.items){
   const row=text('article','','project-mail-row');const title=text('button',item.subject||'(No subject)','project-mail-subject');title.disabled=!item.available;
   title.onclick=()=>{++projectMailRequest;$('projectMailDialog').close();view('mail');selectEmail(item.id).then(()=>{if(state.selected!==item.id)return;const back=text('button','Back to project emails','project-mail-back');back.onclick=()=>openProjectEmails(p);$('reader').prepend(back);}).catch(e=>notice(e.message,'error'));};
   row.append(title,text('p',[item.sender,item.received_time?date(item.received_time,true):''].filter(Boolean).join(' · '),'muted small'));
   const count=item.task_ids.length;row.append(text('p',[item.direct?'Added directly':'',count?count+' linked task'+(count===1?'':'s'):'',!item.available?'Unavailable or excluded from Mail':''].filter(Boolean).join(' · '),'muted small'));
   if(discover){const add=text('button',item.associated?'Added':'Add to project');add.disabled=item.associated;add.onclick=()=>busy(add,async()=>{await api('/api/project-emails',{project_id:p.id,email_id:item.id});if(request===projectMailRequest)await loadProjectEmails();});row.append(add);}
   else if(item.direct){const remove=text('button','Unlink');remove.onclick=()=>busy(remove,async()=>{await api('/api/project-emails',{project_id:p.id,email_id:item.id,remove:true});if(request===projectMailRequest)await loadProjectEmails();});row.append(remove);}
   root.append(row);
  }
  $('projectMailPrevious').disabled=projectMailOffset===0;$('projectMailNext').disabled=projectMailOffset+25>=data.total;$('projectMailPage').textContent=data.total?Math.floor(projectMailOffset/25)+1+' / '+Math.ceil(data.total/25):'';
  $('projectMailPrevious').parentElement.hidden=data.total<=25;
 }catch(e){if(request===projectMailRequest)$('projectMailStatus').textContent=e.message;}
}
$('projectMailClose').onclick=()=>{++projectMailRequest;clearTimeout(projectMailTimer);$('projectMailDialog').close();};
$('projectMailDialog').addEventListener('cancel',()=>{++projectMailRequest;clearTimeout(projectMailTimer);});
$('projectMailAdd').onclick=()=>{clearTimeout(projectMailTimer);projectMailDiscover=!projectMailDiscover;projectMailOffset=0;$('projectMailSearch').value='';loadProjectEmails();};
$('projectMailSearch').oninput=()=>{++projectMailRequest;clearTimeout(projectMailTimer);projectMailOffset=0;projectMailTimer=setTimeout(loadProjectEmails,250);};
$('projectMailPrevious').onclick=()=>{projectMailOffset=Math.max(0,projectMailOffset-25);loadProjectEmails();};
$('projectMailNext').onclick=()=>{projectMailOffset+=25;loadProjectEmails();};

// Project search is deliberately scoped to a saved project, not a global assistant.
const projectSearchDialog=document.createElement('dialog');projectSearchDialog.className='project-search-dialog';projectSearchDialog.setAttribute('aria-label','Ask project');
const projectSearchTitle=text('h2','Ask project');const projectSearchClose=text('button','Done');projectSearchClose.type='button';projectSearchClose.onclick=()=>projectSearchDialog.close();
const projectSearchMessages=text('div','','project-search-messages');const projectSearchStatus=text('p','','muted small');projectSearchStatus.setAttribute('role','status');
const projectSearchForm=document.createElement('form');const projectSearchQuestion=document.createElement('textarea');projectSearchQuestion.rows=3;projectSearchQuestion.maxLength=4000;projectSearchQuestion.placeholder='Ask about this project…';projectSearchQuestion.setAttribute('aria-label','Project question');projectSearchQuestion.required=true;
const projectSearchSend=text('button','Ask','primary');projectSearchSend.type='submit';const projectSearchHead=text('div','','actions');projectSearchHead.append(projectSearchTitle,projectSearchClose);projectSearchForm.append(projectSearchQuestion,projectSearchSend);projectSearchDialog.append(projectSearchHead,projectSearchMessages,projectSearchStatus,projectSearchForm);document.body.append(projectSearchDialog);
let searchProject=null,projectSearchGeneration=0,projectSearchBusy=false;
function renderProjectSearch(data,project){projectSearchMessages.replaceChildren();for(const message of data.messages||[]){const entry=text('article','','project-search-message');entry.append(text('strong',message.role==='user'?'You':'Answer'),text('p',message.text,'project-search-answer'));for(const source of message.sources||[]){const details=document.createElement('details');details.append(text('summary','['+source.id+'] '+source.title+' · '+source.kind),text('blockquote',source.quote));const open=text('button','Open source');open.type='button';open.onclick=()=>{projectSearchDialog.close();if(source.kind==='email'){view('mail');selectEmail(source.key).catch(e=>notice(e.message,'error'));}else if(source.kind==='task'){const task=taskSaved.find(t=>t.id===source.key);if(task)editTask(task,'saved');else notice('This task is no longer available.','error');}else{openProjectEditor(project);if(source.kind==='meeting'){const rows=[...$('projectMeetings').children];rows.find(r=>r.meetingValue().id===source.key)?.scrollIntoView({block:'center'});}}};details.append(open);entry.append(details);}if(message.role==='assistant'){entry.append(text('p',message.documents+' sources searched · '+message.excerpts+' of '+message.total_excerpts+' excerpts used'+(message.unavailable?' · '+message.unavailable+' emails unavailable':''),'muted small'));}projectSearchMessages.append(entry);}projectSearchMessages.scrollTop=projectSearchMessages.scrollHeight;}
window.openProjectSearch=async project=>{searchProject=project;const generation=++projectSearchGeneration;projectSearchTitle.textContent='Ask · '+project.name;projectSearchQuestion.value='';projectSearchMessages.replaceChildren();projectSearchStatus.textContent='Loading…';if(!projectSearchDialog.open)projectSearchDialog.showModal();try{const result=await api('/api/project-search?project_id='+encodeURIComponent(project.id));if(generation!==projectSearchGeneration)return;renderProjectSearch(result,project);projectSearchStatus.textContent='';projectSearchQuestion.focus();}catch(e){if(generation===projectSearchGeneration)projectSearchStatus.textContent=e.message;}};
projectSearchForm.onsubmit=async event=>{event.preventDefault();if(projectSearchBusy||!searchProject)return;const question=projectSearchQuestion.value.trim();if(!question)return;const project=searchProject,generation=projectSearchGeneration;projectSearchBusy=true;projectSearchSend.disabled=true;projectSearchQuestion.disabled=true;projectSearchStatus.textContent='Searching project…';try{const result=await api('/api/project-search',{project_id:project.id,question});if(generation===projectSearchGeneration){renderProjectSearch(result,project);projectSearchQuestion.value='';projectSearchStatus.textContent='';}}catch(e){if(generation===projectSearchGeneration)projectSearchStatus.textContent=e.message;}finally{projectSearchBusy=false;projectSearchSend.disabled=false;projectSearchQuestion.disabled=false;if(generation===projectSearchGeneration)projectSearchQuestion.focus();}};
projectSearchQuestion.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();projectSearchForm.requestSubmit();}});
