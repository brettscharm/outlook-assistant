const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {test}=require('node:test');
function setup(kind){
 const nodes={};const $=id=>nodes[id]??={value:'',children:[],open:true,hidden:true,reportValidity:()=>true,checkValidity:()=>true,addEventListener(){}};
 const calls=[],pending=[];const ctx={$,window:{},state:{pending:0},taskEditor:{origin:'saved',item:{id:'task'}},editingProject:'project',taskScheduleValues:()=>({}),taskFingerprint:'',boardFingerprint:'',setTimeout,clearTimeout,api:(path,data)=>{calls.push(data);return new Promise((resolve,reject)=>pending.push({resolve,reject}));}};
 vm.createContext(ctx);const source=fs.readFileSync('outlook_plugin/static/'+(kind==='task'?'tasks-ui.js':'organize-ui.js'),'utf8');
 const start=source.indexOf(kind==='task'?'let taskEditTimer':'let projectSaveTimer');const end=source.indexOf(kind==='task'?'const boardLimits':'function queueProjectSave',start);
 vm.runInContext(source.slice(start,end),ctx);return {ctx,$,calls,pending,flush:ctx.window[kind==='task'?'flushTaskEdits':'flushProjectEdits'],field:kind==='task'?'editTaskText':'projectName',status:kind==='task'?'taskSaveStatus':'projectStatus',retry:kind==='task'?'retryTaskSave':'retryProjectSave'};
}
for(const kind of ['task','project']){
 test(kind+' serializes rapid edits and drains latest change',async()=>{
  const {ctx,$,calls,pending,flush,field}=setup(kind);$(field).value='First';const first=flush();const second=flush();$(field).value='Latest';pending.shift().resolve();await new Promise(setImmediate);assert.equal(calls.length,2);assert.equal(calls[1][kind==='task'?'text':'name'],'Latest');pending.shift().resolve();assert.equal(await first,true);assert.equal(await second,true);assert.equal(ctx.state.pending,0);assert.equal(await flush(),true);assert.equal(calls.length,2);
 });
 test(kind+' reports failed save and allows retry',async()=>{
  const {ctx,$,pending,flush,field,status,retry}=setup(kind);$(field).value='Keep me';const failed=flush();pending.shift().reject(Error('Offline'));assert.equal(await failed,false);assert.match($(status).textContent,/Not saved/);assert.equal($(retry).hidden,false);assert.equal(ctx.state.pending,0);const saved=flush();pending.shift().resolve();assert.equal(await saved,true);assert.equal($(status).textContent,'All changes saved');
 });
 test(kind+' rejects invalid fields before writing',async()=>{const {$,calls,flush}=setup(kind);$(kind==='task'?'taskEditorForm':'projectForm').reportValidity=()=>false;assert.equal(await flush(),false);assert.equal(calls.length,0);});
}
function workspace(){
 const nodes={};const $=id=>nodes[id]??={open:false,value:''};const calls=[];
 const ctx={$,window:{contextDirty:false},document:{activeElement:{blur(){}}},taskEditor:null,editingProject:null,draftSaving:false,contextSaving:false,state:{pending:0},contactDrafts:{},draftDirty:{},draftConflicts:{},draftTimer:null,contextTimer:null,clearTimeout,setTimeout,flushDrafts:async()=>calls.push('drafts'),flushContext:async()=>calls.push('context')};
 for(const key of ['flushTaskEdits','flushTaskProgress','flushProjectEdits','flushAgentEdits','flushSettingsEdits','flushMailExclusions'])ctx.window[key]=async()=>{calls.push(key);return true;};
 vm.createContext(ctx);const source=fs.readFileSync('outlook_plugin/static/workspace-ui.js','utf8');vm.runInContext(source.slice(source.indexOf('window.flushWorkspace='),source.indexOf('let settingsPending=')),ctx);return {ctx,$,calls};
}
test('quit flushes every saved editor before allowing exit',async()=>{const {ctx,calls}=workspace();assert.equal(await ctx.window.flushWorkspace(),true);assert.equal(calls.length,8);});
test('quit refuses a failed project save',async()=>{const {ctx}=workspace();ctx.window.flushProjectEdits=async()=>false;await assert.rejects(ctx.window.flushWorkspace(),/could not be saved/);});
test('quit preserves a task draft that was not added',async()=>{const {ctx,$}=workspace();$('taskEditor').open=true;$('editTaskText').value='Unsaved draft';ctx.taskEditor={origin:'new'};await assert.rejects(ctx.window.flushWorkspace(),/Add your new task/);});
test('quit refuses unresolved draft conflicts',async()=>{const {ctx}=workspace();ctx.draftConflicts={test:{text:'Other version'}};await assert.rejects(ctx.window.flushWorkspace(),/need saving/);});
test('settings serialize updates without losing edits typed during a save',async()=>{
 const nodes={};const $=id=>nodes[id]??={value:'',textContent:''};const calls=[],pending=[];
 const ctx={$,window:{},setTimeout,clearTimeout,refreshBobStatus(){},refreshSetup(){},api:(path,values)=>{calls.push(values);return new Promise(resolve=>pending.push(resolve));}};vm.createContext(ctx);
 const source=fs.readFileSync('outlook_plugin/static/workspace-ui.js','utf8');vm.runInContext(source.slice(source.indexOf('let settingsPending='),source.indexOf("for(const [id,key] of [['key'")),ctx);
 $('keyName').value='First';ctx.queueSettingsField('keyName','bob_key_name');const result=ctx.window.flushSettingsEdits();$('keyName').value='Latest';ctx.queueSettingsField('keyName','bob_key_name');pending.shift()();await new Promise(setImmediate);assert.equal(calls[1].bob_key_name,'Latest');pending.shift()();assert.equal(await result,true);assert.equal(ctx.window.settingsSaving,false);await ctx.window.flushSettingsEdits();
});
test('one-page lists hide unnecessary pagination, multiple pages retain controls',()=>{
 const nodes={};const $=id=>nodes[id]??={children:[],replaceChildren(){this.children=[];},append(...items){this.children.push(...items);}};
 const ctx={$,text:()=>({}),document:{createElement:()=>({append(){},setAttribute(){}})},Option:function(label,value){this.label=label;this.value=value;}};vm.createContext(ctx);
 const source=fs.readFileSync('outlook_plugin/static/app.js','utf8');vm.runInContext(source.slice(source.indexOf('function listPager('),source.indexOf('async function refreshMailFilters')),ctx);
 ctx.listPager('taskPages',1,1,20,()=>{});assert.equal($('taskPages').hidden,true);assert.equal($('taskPages').children.length,0);ctx.listPager('taskPages',21,1,20,()=>{});assert.equal($('taskPages').hidden,false);assert.equal($('taskPages').children.length,4);
});
