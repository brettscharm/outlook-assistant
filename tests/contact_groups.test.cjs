const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function setup(){
 const nodes={};const $=id=>nodes[id]??={value:'',textContent:'',hidden:false,addEventListener(){},querySelectorAll(){return [];}};
 const ctx={$,window:{},state:{pending:0},contactData:[{domain:'example.com',company:'Example',contacts:[]},{domain:'example.org',company:'EXAMPLE',contacts:[]},{domain:'other.com',company:'Other',contacts:[]}],setTimeout,clearTimeout,navigator:{clipboard:{writeText:async v=>ctx.copied=v}},notice:v=>ctx.notice=v,api:async(path,payload)=>({...payload,revision:payload.revision+1})};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('outlook_plugin/static/contact-groups.js','utf8'),ctx);return {ctx,$};
}
test('group addresses deduplicate and use Outlook separators',async()=>{
 const {ctx}=setup();assert.deepEqual(Array.from(vm.runInContext("groupEmails(' Pat@example.com;pat@example.com, sam@example.org\\n')",ctx)),['pat@example.com','sam@example.org']);
 await ctx.copyGroupEmails(['pat@example.com','sam@example.org']);assert.equal(ctx.copied,'pat@example.com; sam@example.org');
});
test('company groups span linked domains, not unrelated companies',()=>{
 const {ctx}=setup();assert.deepEqual(Array.from(vm.runInContext('groupDomains(contactData[0])',ctx)),['example.com','example.org']);
});
test('failed group save keeps draft dirty and allows retry before quit',async()=>{
 const {ctx,$}=setup();vm.runInContext("groupEditor={item:{id:'g',revision:0,domain:'example.com'},dirty:true}",ctx);$('contactGroupName').value='Team';$('contactGroupEmails').value='a@example.com';ctx.api=async()=>{throw Error('Offline');};
 await assert.rejects(ctx.window.flushContactGroups(),/Offline/);assert.equal(vm.runInContext('groupEditor.dirty',ctx),true);assert.match($('contactGroupStatus').textContent,/Not saved/);
 ctx.api=async(path,payload)=>({...payload,revision:1});await ctx.window.flushContactGroups();assert.equal(vm.runInContext('groupEditor.dirty',ctx),false);assert.equal(ctx.state.pending,0);
});
