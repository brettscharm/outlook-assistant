'use strict';
let chatSending=false;
function renderChat(data){
 const root=$('chatMessages');root.replaceChildren();
 if(!data.messages.length){const empty=text('div','','chat-empty');empty.append(text('h3','Start with a question.'),text('p','Try “What are the next steps for Acme?” or “Find the email about the renewal deadline.”','muted'));root.append(empty);}
 for(const m of data.messages){const item=text('article','',`chat-message chat-${m.role}`);item.append(text('strong',m.role==='user'?'You':'Bob'),text('div',m.text,'chat-answer'));
 if(m.role==='assistant'){item.append(text('p',`${m.searched} cached messages searched · ${m.used} excerpts provided to Bob`,'muted small'));const sources=text('div','','chat-sources');for(const source of m.sources||[]){const b=text('button',`${source.subject||'(No subject)'} · ${date(source.received_time)}`);b.title=source.sender;b.onclick=()=>{view('mail');selectEmail(source.id).catch(e=>notice(e.message));};sources.append(b);}item.append(sources);}root.append(item);}
}
$('chatQuestion').value=localStorage.getItem('outlook-chat-draft')||'';
$('chatQuestion').oninput=()=>localStorage.setItem('outlook-chat-draft',$('chatQuestion').value);
$('chatForm').onsubmit=async e=>{e.preventDefault();if(chatSending)return;const question=$('chatQuestion').value.trim();if(!question)return;chatSending=true;$('clearChat').disabled=true;$('chatQuestion').readOnly=true;$('chatStatus').textContent='Searching cached mail and asking Bob… This can take up to two minutes.';await busy($('sendChat'),async()=>{try{renderChat(await api('/api/chat',{question}));$('chatQuestion').value='';localStorage.removeItem('outlook-chat-draft');$('chatStatus').textContent='Answer saved on this Mac.';}catch(error){$('chatStatus').textContent=error.message;throw error;}});chatSending=false;$('clearChat').disabled=false;$('chatQuestion').readOnly=false;};
$('clearChat').onclick=()=>busy($('clearChat'),async()=>{renderChat(await api('/api/chat-clear',{}));$('chatStatus').textContent='Conversation cleared. Your emails and tasks are unchanged.';});
api('/api/chat').then(renderChat).catch(e=>{$('chatStatus').textContent=e.message;});
