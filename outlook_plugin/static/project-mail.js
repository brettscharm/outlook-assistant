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
