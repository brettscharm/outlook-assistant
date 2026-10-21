'use strict';
let savedContactGroups=[],groupEditor=null,groupSaveTimer=null,groupSavePromise=Promise.resolve();
const groupEmails=value=>[...new Set(value.split(/[;,\n]+/).map(v=>v.trim().toLowerCase()).filter(Boolean))];
const groupDomains=company=>contactData.filter(g=>g.domain===company.domain||(company.company&&g.company.toLowerCase()===company.company.toLowerCase())).map(g=>g.domain);
window.loadContactGroups=async()=>{savedContactGroups=await api('/api/contact-groups');window.renderSavedGroups?.();};
async function copyGroupEmails(emails){
 if(!emails.length){notice('Add people to this group first.');return;}
 const value=emails.join('; ');
 try{await navigator.clipboard.writeText(value);notice(emails.length+' email addresses copied.');}
 catch{const box=document.createElement('textarea');box.value=value;box.setAttribute('aria-label','Email addresses to copy');const host=document.querySelector('#contactGroupDialog[open]')||document.querySelector('#calendarMeeting[open]')||$('contacts');host.append(box);box.focus();box.select();notice('Select and copy the addresses shown.');}
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
function openContactGroup(company,group,seed=null){
 if(group)company=contactData.find(g=>g.domain===group.domain)||{domain:group.domain,company:''};
 groupEditor={company,item:group?{...group,emails:[...group.emails]}:{id:crypto.randomUUID(),revision:0,domain:company.domain,name:seed?.name||'',emails:seed?.emails||[]},dirty:!!seed,extraPeople:seed?.people||[]};
 $('contactGroupTitle').textContent=(company.company||company.domain)+' · Group';$('contactGroupName').value=groupEditor.item.name;$('contactGroupEmails').value=groupEditor.item.emails.join('; ');
 const choices=$('contactGroupCompany');choices.replaceChildren();const domains=new Set([company.domain,...contactData.map(g=>g.domain),...groupEditor.item.emails.map(e=>e.split('@')[1])]);for(const domain of domains){const linked=contactData.find(g=>g.domain===domain);const option=text('option',linked?.company?linked.company+' · '+domain:domain||'Choose a company');option.value=domain;option.selected=domain===company.domain;choices.append(option);}$('contactGroupSearch').value='';$('contactGroupStatus').textContent='';$('contactGroupRemove').hidden=!group;$('contactGroupDialog').showModal();renderGroupPeople();$('contactGroupName').focus();
}
function renderGroupPeople(){
 const root=$('contactGroupPeople');root.replaceChildren();const query=$('contactGroupSearch').value.toLowerCase();const domains=groupDomains(groupEditor.company),selected=new Set(groupEmails($('contactGroupEmails').value));const seen=new Set();
 for(const person of [...groupEditor.extraPeople||[],...contactData.filter(g=>domains.includes(g.domain)).flatMap(g=>g.contacts)]){
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
  if(!groupEditor.item.domain){$('contactGroupStatus').textContent='Choose a company to save.';throw Error('Choose a company.');}
  const editor=groupEditor;const payload={...editor.item,name,emails:groupEmails($('contactGroupEmails').value)};editor.dirty=false;state.pending++;
  try{const saved=await api('/api/contact-groups',payload);editor.item=saved;savedContactGroups=savedContactGroups.filter(g=>g.id!==saved.id).concat(saved);$('contactGroupRemove').hidden=false;$('contactGroupStatus').textContent=editor.dirty?'Saving…':'Saved on this Mac';for(const card of $('contactGroups').querySelectorAll('.contact-group')){const domain=card.querySelector('.company-star')?.dataset.domain;const company=contactData.find(g=>g.domain===domain);if(company)window.refreshCompanyGroups(card,company);}window.renderSavedGroups?.();}
  catch(e){editor.dirty=true;$('contactGroupStatus').textContent='Not saved: '+e.message;throw e;}finally{state.pending--;}
 });return groupSavePromise;
}
$('contactGroupName').oninput=queueGroupSave;$('contactGroupEmails').oninput=()=>{queueGroupSave();renderGroupPeople();};$('contactGroupSearch').oninput=renderGroupPeople;
$('contactGroupClose').onclick=()=>busy($('contactGroupClose'),async()=>{await saveGroup();$('contactGroupDialog').close();});
$('contactGroupDialog').addEventListener('cancel',e=>{e.preventDefault();$('contactGroupClose').click();});
$('contactGroupCopy').onclick=()=>copyGroupEmails(groupEmails($('contactGroupEmails').value));
$('contactGroupRemove').onclick=()=>busy($('contactGroupRemove'),async()=>{await saveGroup();const item=groupEditor.item;await api('/api/contact-groups',{id:item.id,revision:item.revision,remove:true});savedContactGroups=savedContactGroups.filter(g=>g.id!==item.id);$('contactGroupDialog').close();renderContacts();window.renderSavedGroups?.();});

window.flushContactGroups=async()=>{await saveGroup();return true;};

$('contactGroupCompany').onchange=()=>{const domain=$('contactGroupCompany').value;groupEditor.item.domain=domain;groupEditor.company=contactData.find(g=>g.domain===domain)||{domain,company:''};renderGroupPeople();queueGroupSave();};
window.createGroupFromMeeting=async event=>{
 await loadContacts();
 const people=(event.attendees||[]).filter(p=>p.type!=='resource'&&p.email);
 const emails=[...new Set(people.map(p=>p.email))];if(!emails.length)return;
 const domain=emails[0].split('@')[1];const company=contactData.find(g=>g.domain===domain)||{domain,company:''};
 openContactGroup(company,null,{name:event.subject.slice(0,100),emails,people});
};

let savedGroupsPage=1;
function filteredSavedGroups(groups,companies,query){
 query=query.trim().toLowerCase();
 return groups.map(group=>({group,company:companies.find(c=>c.domain===group.domain)?.company||group.domain})).filter(({group,company})=>(group.name+' '+company+' '+group.domain+' '+group.emails.join(' ')).toLowerCase().includes(query)).sort((a,b)=>a.company.localeCompare(b.company)||a.group.name.localeCompare(b.group.name)||a.group.id.localeCompare(b.group.id));
}
window.renderSavedGroups=()=>{
 const root=$('savedGroupList');if(!root)return;root.replaceChildren();
 const rows=filteredSavedGroups(savedContactGroups,contactData,$('savedGroupSearch').value),pages=Math.max(1,Math.ceil(rows.length/20));savedGroupsPage=Math.min(Math.max(1,savedGroupsPage),pages);
 $('savedGroupCount').textContent=rows.length+(rows.length===1?' group':' groups');
 for(const {group,company} of rows.slice((savedGroupsPage-1)*20,savedGroupsPage*20)){
  const card=text('article','','saved-group-card');const details=text('div');details.append(text('h3',group.name),text('p',company+' · '+group.emails.length+(group.emails.length===1?' person':' people'),'muted small'));
  const actions=text('div','','actions');const edit=text('button','Edit');edit.setAttribute('aria-label','Edit '+group.name);edit.onclick=()=>openContactGroup({domain:group.domain,company},group);
  const copy=text('button','Copy emails');copy.disabled=!group.emails.length;copy.setAttribute('aria-label','Copy emails for '+group.name);copy.onclick=()=>copyGroupEmails(group.emails);actions.append(edit,copy);card.append(details,actions);root.append(card);
 }
 if(!rows.length)root.append(text('p',savedContactGroups.length?'No matching groups.':'No groups yet. Add one here or create one from a calendar event.','muted'));
 const nav=$('savedGroupPages');nav.replaceChildren();nav.hidden=pages<=1;
 if(pages>1){const previous=text('button','Previous'),next=text('button','Next');previous.disabled=savedGroupsPage===1;next.disabled=savedGroupsPage===pages;previous.onclick=()=>{savedGroupsPage--;window.renderSavedGroups();};next.onclick=()=>{savedGroupsPage++;window.renderSavedGroups();};nav.append(previous,text('span',savedGroupsPage+' of '+pages),next);}
};
function setContactsView(groups){
 $('contactsCompaniesPanel').hidden=groups;$('contactsGroupsPanel').hidden=!groups;
 for(const [id,selected] of [['contactsCompaniesView',!groups],['contactsGroupsView',groups]]){$(id).setAttribute('aria-pressed',String(selected));$(id).classList.toggle('selected',selected);}
 if(groups){window.renderSavedGroups();window.loadContactGroups().catch(e=>notice(e.message,'error'));}
}
$('contactsCompaniesView').onclick=()=>setContactsView(false);$('contactsGroupsView').onclick=()=>setContactsView(true);
$('savedGroupSearch').oninput=()=>{savedGroupsPage=1;window.renderSavedGroups();};
$('newSavedGroup').onclick=()=>openContactGroup({domain:'',company:''});
$('refreshSavedGroups').onclick=()=>busy($('refreshSavedGroups'),()=>window.loadContactGroups());
