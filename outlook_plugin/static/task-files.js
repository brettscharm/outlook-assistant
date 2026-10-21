'use strict';
window.mountTaskFiles=function(parent,kind,owner){
 parent.querySelector('.attached-files')?.remove();
 const section=text('section','','attached-files');section.append(text('h3','Files'));parent.append(section);
 if(!owner){section.append(text('p','Save this '+kind+' first to attach files.','muted small'));return;}
 const list=text('div','','file-list'),status=text('p','','muted small');status.setAttribute('role','status');
 const label=text('label','Attach files','file-picker');const input=document.createElement('input');input.type='file';input.multiple=true;input.accept='.doc,.docx,.xls,.xlsx,.ppt,.pptx,.pdf,.txt,.csv,.rtf,.png,.jpg,.jpeg';input.setAttribute('aria-label','Attach files to '+kind);label.append(input);
 section.append(label,text('p','Saved on this Mac · Up to 25 MB per file','muted small'),list,status);
 if(window.webkit?.messageHandlers?.saveBackup&&!window.nativeFilePickerReady){label.hidden=true;const update=text('a','Update the Mac app to attach files','feedback-link');update.href='https://github.com/brettscharm/outlook-assistant/releases/tag/v2.17.0';update.target='_blank';update.rel='noopener noreferrer';section.prepend(update);}
 async function render(){
  const rows=await api('/api/task-files?'+new URLSearchParams({kind,owner}));list.replaceChildren();
  if(!rows.length)list.append(text('p','No files attached.','muted small'));
  for(const file of rows){
   const row=text('div','','attached-file');const info=text('div','','file-info');info.append(text('strong',file.name),text('small',(file.size/1024/1024>=1?(file.size/1024/1024).toFixed(1)+' MB':Math.max(1,Math.round(file.size/1024))+' KB')));
   const open=text('button','Open');open.type='button';open.setAttribute('aria-label','Open '+file.name);open.onclick=()=>busy(open,async()=>{await api('/api/task-files',{kind,owner,id:file.id,action:'open'});status.textContent='Opened in your default Mac app. Edits there update this saved copy.';});
   const remove=text('button','Remove');remove.type='button';remove.setAttribute('aria-label','Remove '+file.name);remove.onclick=()=>{if(!confirm('Remove '+file.name+' from this '+kind+'? This deletes the attached copy. Your original file is unchanged.'))return;busy(remove,async()=>{await api('/api/task-files',{kind,owner,id:file.id,action:'remove'});await render();});};
   row.append(info,open,remove);list.append(row);
  }
 }
 input.onchange=async()=>{input.disabled=true;state.pending++;try{for(const file of input.files){if(file.size>25*1024*1024)throw Error(file.name+' is larger than 25 MB.');status.textContent='Saving '+file.name+'…';const content=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Could not read '+file.name));reader.readAsDataURL(file);});await api('/api/task-files',{kind,owner,action:'add',name:file.name,content});await render();}status.textContent='Files saved on this Mac.';}catch(e){status.textContent=e.message;notice(e.message,'error');}finally{input.disabled=false;input.value='';state.pending--;}};
 render().catch(e=>{status.textContent=e.message;});
};
