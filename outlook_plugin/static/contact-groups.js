'use strict';
let savedContactGroups=[],groupEditor=null,groupSaveTimer=null,groupSavePromise=Promise.resolve();
const groupEmails=value=>[...new Set(value.split(/[;,\n]+/).map(v=>v.trim().toLowerCase()).filter(Boolean))];
const groupDomains=company=>contactData.filter(g=>g.domain===company.domain||(company.company&&g.company.toLowerCase()===company.company.toLowerCase())).map(g=>g.domain);
window.loadContactGroups=async()=>{savedContactGroups=await api('/api/contact-groups');};
async function copyGroupEmails(emails){
 if(!emails.length){notice('Add people to this group first.');return;}
 const value=emails.join('; ');
 try{await navigator.clipboard.writeText(value);notice(emails.length+' email addresses copied.');}
 catch{const box=document.createElement('textarea');box.value=value;box.setAttribute('aria-label','Email addresses to copy');const host=document.querySelector('#contactGroupDialog[open]')||$('contacts');host.append(box);box.focus();box.select();notice('Select and copy the addresses shown.');}
}
window.mountContactGroups=function(card,company){
 const section=text('section','','company-groups');section.append(text('h3','Groups'));
 const domains=groupDomains(company);
 for(const group of savedContactGroups.filter(g=>domains.includes(g.domain))){
  const row=text('div','','actions');const edit=text('button',group.name+' · '+group.emails.length);edit.onclick=()=>openContactGroup(company,group);
  const copy=text('button','Copy emails');copy.disabled=!group.emails.length;copy.setAttribute('aria-label','Copy emails for '+group.name);copy.onclick=()=>copyGroupEmails(group.emails);row.append(edit,copy);section.append(row);
 }
 const add=text('button','Add group');add.onclick=()=>openContactGroup(company);section.append(add);card.insertBefore(section,card.querySelector('.contact-person'));
};
window.refreshCompanyGroups=(card,company)=>{card.querySelector('.company-groups')?.remove();window.mountContactGroups(card,company);};
function openContactGroup(company,group){
 groupEditor={company,item:group?{...group,emails:[...group.emails]}:{id:crypto.randomUUID(),revision:0,domain:company.domain,name:'',emails:[]},dirty:false};
 $('contactGroupTitle').textContent=(company.company||company.domain)+' · Group';$('contactGroupName').value=group?.name||'';$('contactGroupEmails').value=(group?.emails||[]).join('; ');$('contactGroupSearch').value='';$('contactGroupStatus').textContent='';$('contactGroupRemove').hidden=!group;$('contactGroupDialog').showModal();renderGroupPeople();$('contactGroupName').focus();
}
function renderGroupPeople(){
 const root=$('contactGroupPeople');root.replaceChildren();const query=$('contactGroupSearch').value.toLowerCase();const domains=groupDomains(groupEditor.company),selected=new Set(groupEmails($('contactGroupEmails').value));const seen=new Set();
 for(const person of contactData.filter(g=>domains.includes(g.domain)).flatMap(g=>g.contacts)){
  if(seen.has(person.email)||!(person.name+' '+person.email).toLowerCase().includes(query))continue;seen.add(person.email);
  const label=text('label','','group-person');const box=document.createElement('input');box.type='checkbox';box.checked=selected.has(person.email.toLowerCase());box.onchange=()=>{const emails=new Set(groupEmails($('contactGroupEmails').value));if(box.checked)emails.add(person.email.toLowerCase());else emails.delete(person.email.toLowerCase());$('contactGroupEmails').value=[...emails].join('; ');queueGroupSave();};label.append(box,text('span',person.name+' · '+person.email));root.append(label);
 }
 if(!seen.size)root.append(text('p','No matching contacts. You can paste email addresses below.','muted small'));
}
function queueGroupSave(){groupEditor.dirty=true;clearTimeout(groupSaveTimer);$('contactGroupStatus').textContent='Saving…';groupSaveTimer=setTimeout(()=>saveGroup().catch(()=>{}),500);}
function saveGroup(){
 clearTimeout(groupSaveTimer);
 groupSavePromise=groupSavePromise.catch(()=>{}).then(async()=>{
  if(!groupEditor?.dirty)return;
  const name=$('contactGroupName').value.trim();if(!name){$('contactGroupStatus').textContent='Enter a group name to save.';throw Error('Enter a group name.');}
  const editor=groupEditor;const payload={...editor.item,name,emails:groupEmails($('contactGroupEmails').value)};editor.dirty=false;state.pending++;
  try{const saved=await api('/api/contact-groups',payload);editor.item=saved;savedContactGroups=savedContactGroups.filter(g=>g.id!==saved.id).concat(saved);$('contactGroupRemove').hidden=false;$('contactGroupStatus').textContent=editor.dirty?'Saving…':'Saved on this Mac';for(const card of $('contactGroups').querySelectorAll('.contact-group')){const domain=card.querySelector('.company-star')?.dataset.domain;const company=contactData.find(g=>g.domain===domain);if(company)window.refreshCompanyGroups(card,company);}}
  catch(e){editor.dirty=true;$('contactGroupStatus').textContent='Not saved: '+e.message;throw e;}finally{state.pending--;}
 });return groupSavePromise;
}
$('contactGroupName').oninput=queueGroupSave;$('contactGroupEmails').oninput=()=>{queueGroupSave();renderGroupPeople();};$('contactGroupSearch').oninput=renderGroupPeople;
$('contactGroupClose').onclick=()=>busy($('contactGroupClose'),async()=>{await saveGroup();$('contactGroupDialog').close();});
$('contactGroupDialog').addEventListener('cancel',e=>{e.preventDefault();$('contactGroupClose').click();});
$('contactGroupCopy').onclick=()=>copyGroupEmails(groupEmails($('contactGroupEmails').value));
$('contactGroupRemove').onclick=()=>busy($('contactGroupRemove'),async()=>{await saveGroup();const item=groupEditor.item;await api('/api/contact-groups',{id:item.id,revision:item.revision,remove:true});savedContactGroups=savedContactGroups.filter(g=>g.id!==item.id);$('contactGroupDialog').close();renderContacts();});

window.flushContactGroups=async()=>{await saveGroup();return true;};
