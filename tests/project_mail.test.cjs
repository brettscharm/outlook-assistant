const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
 class Element{constructor(){this.children=[];this.parentElement={};}append(...items){this.children.push(...items);}replaceChildren(...items){this.children=items;}setAttribute(k,v){this[k]=v;}addEventListener(){}showModal(){this.open=true;}close(){this.open=false;}}
 const ids={},calls=[],$=id=>ids[id]||(ids[id]=new Element());
 const ctx={document:{createElement:()=>new Element(),body:new Element()},window:{},$,URLSearchParams,clearTimeout,setTimeout,text:(tag,value)=>Object.assign(new Element(),{tag,textContent:value}),api:url=>new Promise(resolve=>calls.push({url,resolve})),date:x=>x};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('outlook_plugin/static/project-mail.js','utf8'),ctx);return {ctx,ids,calls};
}
const settle=async()=>{for(let i=0;i<5;i++)await Promise.resolve();};
test('late responses cannot replace another project email view',async()=>{
 const {ctx,ids,calls}=setup();ctx.window.openProjectEmails({id:'old',name:'Old'});ctx.window.openProjectEmails({id:'new',name:'New'});
 calls[1].resolve({items:[],total:0});await settle();calls[0].resolve({items:[],total:99});await settle();
 assert.equal(ids.projectMailTitle.textContent,'Emails · New');assert.match(ids.projectMailStatus.textContent,/^0 emails/);
});
test('project email pages use server offsets and reset when adding mail',async()=>{
 const {ctx,ids,calls}=setup();ctx.window.openProjectEmails({id:'project',name:'Project'});calls[0].resolve({items:[],total:55});await settle();
 assert.equal(ids.projectMailNext.disabled,false);assert.equal(ids.projectMailPrevious.disabled,true);assert.equal(ids.projectMailPage.textContent,'1 / 3');
 ids.projectMailNext.onclick();assert.match(calls[1].url,/offset=25/);calls[1].resolve({items:[],total:55});await settle();assert.equal(ids.projectMailPage.textContent,'2 / 3');
 ids.projectMailAdd.onclick();assert.match(calls[2].url,/offset=0/);assert.match(calls[2].url,/discover=true/);calls[2].resolve({items:[],total:0});await settle();assert.equal(ids.projectMailPrevious.parentElement.hidden,true);
});
