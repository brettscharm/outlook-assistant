'use strict';
function mountReplyComposer(id,message,root){
 const section=text('details','','draft reply-disclosure');section.append(text('summary','Reply'));
 const recipient=text('div','To: '+(message.sender||message.from?.address||'Original sender'),'reply-recipient');section.append(recipient);
 const expand=text('button','Expand editor');expand.type='button';expand.setAttribute('aria-pressed','false');expand.onclick=()=>{const expanded=section.classList.toggle('reply-expanded');expand.textContent=expanded?'Restore editor':'Expand editor';expand.setAttribute('aria-pressed',String(expanded));};
 const controls=text('div','','actions reply-controls');const tone=document.createElement('select');tone.setAttribute('aria-label','Reply tone');
 for(const [value,label] of [['friendly','Friendly'],['professional','Professional'],['direct','Direct'],['firm','Firm'],['casual','Casual']]){const option=text('option',label);option.value=value;tone.append(option);}
 const intent=document.createElement('input');intent.placeholder='Optional instructions';intent.setAttribute('aria-label','Reply instructions');intent.maxLength=3000;intent.value=state.intents[id]||'';intent.oninput=()=>{state.intents[id]=intent.value;persistDrafts();};controls.append(tone,intent,expand);
 const remember=()=>{state.drafts[id]=box.innerText;state.draftMeta[id]={html:cleanEmailHTML(box.innerHTML),subject:message.subject||'(No subject)',sender:message.sender||'',saved_at:new Date().toISOString()};persistDrafts();};
 const editor=richEditor(state.drafts[id]||'',state.draftMeta[id]?.html||'',remember),box=editor.box;box.dataset.placeholder='Write your reply here, then choose Polish draft.';
 const actions=text('div','','actions reply-actions');const polish=text('button','Polish draft','primary'),generate=text('button','Draft for me'),copy=text('button','Copy reply'),undo=text('button','Undo change');undo.hidden=true;let previousHTML='';
 const suggestions=text('div','','reply-suggestions');
 function apply(reply){previousHTML=box.innerHTML;editor.setHTML(reply);remember();undo.hidden=false;suggestions.replaceChildren();}
 undo.onclick=()=>{editor.setHTML(previousHTML);remember();undo.hidden=true;};
 async function request(button,path){
  if(path==='/api/polish-reply'&&!box.innerText.trim()){box.focus();notice('Write your reply in the box first.');return;}
  const original=box.innerHTML;const payload={email_id:id,tone:tone.value,intent:intent.value};if(path==='/api/polish-reply')Object.assign(payload,{draft:box.innerText,html:cleanEmailHTML(original)});
  polish.disabled=true;generate.disabled=true;
  try{await busy(button,async()=>{const result=await api(path,payload);
   if(!section.isConnected)return;
   if(box.innerHTML===original){apply(result.reply);return;}
   const preview=text('div','','reply-suggestion-preview');preview.innerHTML=cleanEmailHTML(result.reply);const use=text('button','Use suggestion');use.onclick=()=>apply(result.reply);const dismiss=text('button','Keep my draft');dismiss.onclick=()=>suggestions.replaceChildren();suggestions.replaceChildren(text('p','Your draft changed while Bob was working. Review the suggestion below.','muted small'),preview,use,dismiss);
  });}finally{polish.disabled=false;generate.disabled=false;}
 }
 polish.onclick=()=>request(polish,'/api/polish-reply');generate.onclick=()=>request(generate,'/api/smart-reply');
 copy.onclick=()=>copyRichDraft(box.innerText,box.innerHTML).then(()=>notice('Reply copied.')).catch(()=>notice('Select the draft text and copy it manually.'));
 actions.append(polish,generate,copy,undo);const status=text('p','Changes save automatically.','muted small');status.id='replySaveStatus';section.append(controls,editor.wrapper,actions,suggestions,status);root.append(section);
}
