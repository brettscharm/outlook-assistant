const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.events={};this.attrs={};this.classList={add(){},remove(){}};}
 append(...nodes){this.children.push(...nodes);}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}replaceChildren(...nodes){this.children=nodes;}querySelector(){return null;}addEventListener(k,v){this.events[k]=v;}
}
async function fixture(kind){
 const created=[],calls=[],events={};const text=(tag,value='',cls='')=>{const node=new Element(tag);node.textContent=value;node.className=cls;created.push(node);return node;};
 const context={window:{},document:{createElement:tag=>text(tag),addEventListener:(k,v)=>events[k]=v},text,state:{pending:0},notice(){},busy(){},confirm(){return true;},api:async(url,data)=>{if(data)calls.push(data);return [];},FileReader:class{readAsDataURL(){this.result='data:text/plain;base64,dGVzdA==';this.onload();}}};
 vm.runInNewContext(fs.readFileSync('outlook_plugin/static/task-files.js','utf8'),context);context.window.mountTaskFiles(new Element('dialog'),kind,'owner-id');
 const drop=created.find(n=>n.className==='file-drop-zone'),input=created.find(n=>n.tag==='input');let prevented=false;
 drop.events.drop({dataTransfer:{types:['Files'],files:[{name:'first.pdf',size:4},{name:'bad.exe',size:3},{name:'big.pdf',size:26*1024*1024},{name:'second.docx',size:10}]},preventDefault(){prevented=true;},stopPropagation(){}});
 for(let i=0;i<10;i++)await Promise.resolve();
 assert(prevented);assert.deepEqual(calls.map(c=>c.name),['first.pdf','second.docx']);assert(calls.every(c=>c.kind===kind&&c.owner==='owner-id'));assert.equal(context.state.pending,0);assert.equal(input.disabled,false);
 input.files=[{name:'picker.xlsx',size:4}];await input.onchange();assert.equal(calls.at(-1).name,'picker.xlsx');
 let external=false;events.drop({dataTransfer:{types:['Files']},preventDefault(){external=true;}});assert(external);
 let taskDrag=false;events.drop({dataTransfer:{types:['text/plain']},preventDefault(){taskDrag=true;}});assert.equal(taskDrag,false);
}
(async()=>{await fixture('task');await fixture('project');console.log('Task/project drops, file picker, partial failures, and navigation protection passed.');})().catch(e=>{console.error(e);process.exit(1);});
