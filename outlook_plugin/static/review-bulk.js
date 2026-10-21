'use strict';
const reviewSelection=new Set();let reviewMatching=[],reviewBulkBusy=false;
function reviewEligible(item){return item.status==='review'&&item.action_type!=='complete';}
window.addReviewCheckbox=(root,item)=>{if(!reviewEligible(item))return;const box=document.createElement('input');box.type='checkbox';box.className='review-select-box';box.dataset.reviewId=item.id;box.checked=reviewSelection.has(item.id);box.setAttribute('aria-label','Select task: '+item.text);box.onchange=()=>{if(box.checked)reviewSelection.add(item.id);else reviewSelection.delete(item.id);renderReviewSelection();};root.append(box);};
function renderReviewSelection(){
 window.reviewSelectionDirty=reviewSelection.size>0;
 const count=reviewSelection.size,selected=reviewMatching.filter(item=>reviewSelection.has(item.id)).length;
 $('reviewSelectAll').checked=!!reviewMatching.length&&selected===reviewMatching.length;$('reviewSelectAll').indeterminate=selected>0&&selected<reviewMatching.length;$('reviewSelectAll').disabled=!reviewMatching.length||reviewBulkBusy;
 $('reviewSelectedCount').textContent=count?count+' selected'+(count>selected?' · '+(count-selected)+' outside these results':''):'';$('reviewBulkOpen').disabled=!count||reviewBulkBusy;$('reviewClearSelection').hidden=!count;
 document.querySelectorAll('[data-review-id]').forEach(box=>{box.checked=reviewSelection.has(box.dataset.reviewId);box.disabled=reviewBulkBusy;});
}
window.updateReviewSelection=(items,origin)=>{
 const valid=new Set((taskReview?.suggestions||[]).filter(reviewEligible).map(t=>t.id));for(const id of reviewSelection)if(!valid.has(id))reviewSelection.delete(id);
 reviewMatching=origin==='review'?items.filter(reviewEligible):[];$('reviewBulkBar').hidden=origin!=='review'||(!reviewMatching.length&&!reviewSelection.size);renderReviewSelection();
};
$('reviewSelectAll').onchange=()=>{for(const item of reviewMatching){if($('reviewSelectAll').checked)reviewSelection.add(item.id);else reviewSelection.delete(item.id);}renderReviewSelection();};
$('reviewClearSelection').onclick=()=>{reviewSelection.clear();renderReviewSelection();};
const reviewBulkFields=['Project','Owner','Priority','Due','CoOwners'];
for(const key of reviewBulkFields)$('reviewBulkUse'+key).onchange=()=>{$('reviewBulk'+key+'Fields').hidden=!$('reviewBulkUse'+key).checked;};
$('reviewBulkOwnerType').onchange=()=>{$('reviewBulkOwner').hidden=$('reviewBulkOwnerType').value==='my';};
$('reviewBulkOpen').onclick=async()=>{try{
 projectRows=await api('/api/projects');$('reviewBulkForm').reset();for(const key of reviewBulkFields)$('reviewBulk'+key+'Fields').hidden=true;$('reviewBulkOwner').hidden=true;
 const select=$('reviewBulkProject');select.replaceChildren();for(const [value,label] of [['','No project'],...projectRows.map(p=>[p.id,p.name])]){const option=text('option',label);option.value=value;select.append(option);}
 $('reviewBulkCount').textContent=reviewSelection.size+' selected tasks';$('reviewBulkStatus').textContent='';$('reviewBulkSubmit').textContent='Add tasks';$('reviewBulkDialog').showModal();
 }catch(error){notice(error.message,'error');}};
function closeReviewBulk(){if(!reviewBulkBusy)$('reviewBulkDialog').close();}
$('reviewBulkClose').onclick=closeReviewBulk;$('reviewBulkDialog').addEventListener('cancel',event=>{event.preventDefault();closeReviewBulk();});
function reviewBulkPayload(item,changes){
 return {action:'accept',id:item.id,priority:item.priority||'none',project_id:item.project_id||'',source_type:item.source_type||'email',source_url:item.source_url||'',co_owners:item.co_owners||[],...changes};
}
$('reviewBulkForm').onsubmit=async event=>{
 event.preventDefault();if(reviewBulkBusy)return;const changes={};
 if($('reviewBulkUseProject').checked)changes.project_id=$('reviewBulkProject').value;
 if($('reviewBulkUsePriority').checked)changes.priority=$('reviewBulkPriority').value;
 if($('reviewBulkUseDue').checked){changes.due_date=$('reviewBulkDue').value;changes.deadline={kind:'date'};}
 if($('reviewBulkUseCoOwners').checked)changes.co_owners=$('reviewBulkCoOwners').value.split('\n').map(x=>x.trim()).filter(Boolean);
 if($('reviewBulkUseOwner').checked){changes.type=$('reviewBulkOwnerType').value;changes.owner=changes.type==='my'?currentOwnerName():$('reviewBulkOwner').value.trim();if(!changes.owner){$('reviewBulkStatus').textContent='Enter an owner name.';$('reviewBulkOwner').focus();return;}}
 const items=(taskReview?.suggestions||[]).filter(item=>reviewSelection.has(item.id)&&reviewEligible(item));if(!items.length){$('reviewBulkStatus').textContent='These tasks have already been reviewed.';return;}
 reviewBulkBusy=true;state.pending++;$('reviewBulkForm').querySelectorAll('input,select,textarea,button').forEach(el=>el.disabled=true);let added=0,failed=0,lastError='';
 try{for(const item of items){$('reviewBulkStatus').textContent='Adding '+(added+failed+1)+' of '+items.length+'…';try{await api('/api/task-review',reviewBulkPayload(item,changes));reviewSelection.delete(item.id);added++;}catch(error){failed++;lastError=error.message;}}
 $('reviewBulkStatus').textContent=added+' added'+(failed?' · '+failed+' could not be added. '+lastError+' Retry to add the remaining tasks.':'.');
 await loadTaskWorkspace();if(!failed){$('reviewBulkDialog').close();notice(added+' tasks added.');}
 }catch(error){$('reviewBulkStatus').textContent=added+' added. '+error.message;}
 finally{reviewBulkBusy=false;state.pending--;$('reviewBulkForm').querySelectorAll('input,select,textarea,button').forEach(el=>el.disabled=false);$('reviewBulkCount').textContent=reviewSelection.size+' selected tasks';$('reviewBulkSubmit').textContent=failed?'Retry remaining':'Add tasks';renderReviewSelection();}
};
