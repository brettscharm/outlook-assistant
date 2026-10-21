const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
 const elements=[];function element(tag,value=''){const e={tag,textContent:value,value:'',innerText:'Original draft',innerHTML:'<p>Original draft</p>',dataset:{},children:[],isConnected:true,setAttribute(k,v){this[k]=v;},append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;},focus(){}};elements.push(e);return e;}
 let resolve;const calls=[];let box;
 const ctx={state:{drafts:{mail:'Original draft'},draftMeta:{},intents:{}},text:element,document:{createElement:tag=>element(tag)},persistDrafts(){},cleanEmailHTML:v=>v,richEditor:()=>{box=element('editor');return {box,wrapper:element('wrapper'),setHTML(v){box.innerHTML=v;box.innerText=v;}};},copyRichDraft:async()=>{},notice(){},busy:async(button,fn)=>fn(),api:(path,payload)=>{calls.push({path,payload});return new Promise(ok=>resolve=ok);}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('outlook_plugin/static/reply-composer.js','utf8'),ctx);ctx.mountReplyComposer('mail',{},element('root'));return {ctx,box,calls,resolve:v=>resolve(v),button:name=>elements.find(e=>e.tag==='button'&&e.textContent===name),elements};
}
test('polish sends typed draft, supports undo and keeps generation separate',async()=>{
 const {box,calls,resolve,button}=setup();const call=button('Polish draft').onclick();assert.equal(calls[0].path,'/api/polish-reply');assert.equal(calls[0].payload.draft,'Original draft');resolve({reply:'<p>Improved draft</p>'});await call;assert.equal(box.innerHTML,'<p>Improved draft</p>');button('Undo change').onclick();assert.equal(box.innerHTML,'<p>Original draft</p>');
});
test('edits made while polishing are not overwritten',async()=>{
 const {box,resolve,button}=setup();const call=button('Polish draft').onclick();box.innerHTML='<p>New user changes</p>';resolve({reply:'<p>Suggestion</p>'});await call;assert.equal(box.innerHTML,'<p>New user changes</p>');button('Use suggestion').onclick();assert.equal(box.innerHTML,'<p>Suggestion</p>');button('Undo change').onclick();assert.equal(box.innerHTML,'<p>New user changes</p>');
});
test('blank draft is not sent to Bob',async()=>{const {box,calls,button}=setup();box.innerText=' ';await button('Polish draft').onclick();assert.equal(calls.length,0);});
