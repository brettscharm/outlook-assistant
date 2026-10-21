'use strict';
let chatSending=false;
function renderChat(data){
 const root=$('chatMessages');root.replaceChildren();
 for(const m of data.messages){const item=text('article','',`chat-message chat-${m.role}`);item.append(text('strong',m.role==='user'?'You':'Bob'),text('div',m.text,'chat-answer'));
 if(m.role==='assistant'){if(m.sources?.length)item.append(text('p',m.source_kind==='possible'?'Possible matches':'Sources','muted small'));const sources=text('div','','chat-sources');for(const source of m.sources||[]){const b=text('button',`${source.subject||'(No subject)'} · ${date(source.received_time)}`);b.title=source.sender;b.onclick=()=>{closeAssistant();view('mail');selectEmail(source.id).catch(e=>notice(e.message));};sources.append(b);}item.append(sources);for(const action of m.actions||[]){const card=text('div','','assistant-action');card.append(text('strong',action.label));const details=text('details');details.append(text('summary','Review details'));for(const [key,value] of Object.entries(action.payload||{})){if(key.endsWith('_id'))continue;details.append(text('p',key.replaceAll('_',' ')+': '+(Array.isArray(value)?value.join(', '):value),'small'));}card.append(details);const apply=text('button',action.status==='applied'?'Applied':'Apply','primary');apply.disabled=action.status==='applied';apply.onclick=()=>busy(apply,async()=>{renderChat(await api('/api/assistant-apply',{action_id:action.id}));contactsLoaded=false;await window.loadTaskWorkspace?.();if($('contacts').classList.contains('active'))await loadContacts(true);});card.append(apply);item.append(card);}}root.append(item);}
 root.scrollTop=root.scrollHeight;
}
$('chatQuestion').value=(()=>{try{return localStorage.getItem('outlook-chat-draft')||'';}catch{return '';}})();
$('chatQuestion').oninput=()=>{try{localStorage.setItem('outlook-chat-draft',$('chatQuestion').value);}catch{}};
$('chatForm').onsubmit=async e=>{e.preventDefault();if(chatSending)return;const question=$('chatQuestion').value.trim();if(!question)return;chatSending=true;$('clearChat').disabled=true;$('chatQuestion').readOnly=true;$('chatStatus').textContent='Working…';await busy($('sendChat'),async()=>{try{renderChat(await api('/api/assistant',{question,context:{page:assistantPreviousView,email_id:assistantPreviousView==='mail'?state.selected:null}}));$('chatQuestion').value='';try{localStorage.removeItem('outlook-chat-draft');}catch{}$('chatStatus').textContent='';}catch(error){$('chatStatus').textContent=error.message;throw error;}});chatSending=false;$('clearChat').disabled=false;$('chatQuestion').readOnly=false;};
$('clearChat').onclick=()=>busy($('clearChat'),async()=>{renderChat(await api('/api/chat-clear',{}));$('chatStatus').textContent='Conversation cleared. Your emails and tasks are unchanged.';});
window.refreshChatHistory=async()=>{if(chatSending)return;const data=await api('/api/chat');if(!chatSending)renderChat(data);};
window.refreshChatHistory().catch(e=>{$('chatStatus').textContent=e.message;});

let assistantPreviousView='tasks',assistantDocked=false;
window.assistantViewChanged=id=>{if(id!=='chat'){assistantPreviousView=id;$('assistantContext').textContent='Viewing '+({'task-review':'tasks to review'}[id]||id);}else{$('chat').classList.remove('assistant-docked');assistantDocked=false;$('assistantExpand').textContent='Compact';$('assistantOpen').setAttribute('aria-expanded','true');}};
function openAssistant(){
 if($('chat').classList.contains('active')||assistantDocked){closeAssistant();return;}
 assistantDocked=true;$('assistantContext').textContent='Viewing '+assistantPreviousView;$('chat').classList.add('assistant-docked');$('assistantExpand').textContent='Expand';$('assistantOpen').setAttribute('aria-expanded','true');$('chatQuestion').focus();window.refreshChatHistory();
}
function closeAssistant(){const full=$('chat').classList.contains('active');assistantDocked=false;$('chat').classList.remove('assistant-docked');$('assistantOpen').setAttribute('aria-expanded','false');if(full)view(assistantPreviousView);$('assistantOpen').focus();}
$('assistantOpen').onclick=openAssistant;
$('assistantClose').onclick=closeAssistant;
$('assistantExpand').onclick=()=>{if(assistantDocked){view('chat');}else{view(assistantPreviousView);assistantDocked=true;$('chat').classList.add('assistant-docked');$('assistantExpand').textContent='Expand';} $('chatQuestion').focus();};
$('chat').addEventListener('keydown',event=>{if(event.key==='Escape'){closeAssistant();event.preventDefault();}});
