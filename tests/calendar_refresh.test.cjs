const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function setup(){
 const nodes={refreshCalendar:{},calendarStatus:{},calendar:{classList:{contains:()=>true}}};let resolve,reject;
 const ctx={window:{},$:id=>nodes[id],calendarRequest:0,calendarAnchor:new Date(),calendarMode:'month',calendarEvents:[{id:'saved'}],calendarChecked:100,calendarRange:()=>({start:new Date(0),end:new Date(86400000)}),URLSearchParams,renderCalendar(){},fillCalendarProjects(){},date:()=> 'yesterday',setTimeout:()=>1,clearTimeout(){},document:{hidden:false},api:url=>url==='/api/projects'?Promise.resolve([]):new Promise((ok,fail)=>{resolve=ok;reject=fail;})};
 vm.createContext(ctx);const source=fs.readFileSync('outlook_plugin/static/calendar-ui.js','utf8');vm.runInContext(source.slice(source.indexOf('let calendarPoll='),source.indexOf("for(const button of document.querySelectorAll('[data-calendar-view]'))")),ctx);return {ctx,nodes,resolve:data=>resolve(data),reject:e=>reject(e)};
}
test('calendar stays visible while refresh loads and replaces events on completion',async()=>{
 const {ctx,resolve,nodes}=setup();const call=ctx.window.loadCalendar(true);assert.equal(ctx.calendarEvents[0].id,'saved');resolve({events:[{id:'updated'}],checked:200,refreshing:true});await call;assert.equal(ctx.calendarEvents[0].id,'updated');assert.match(nodes.calendarStatus.textContent,/Updating/);
});
test('failed calendar request retains meetings and last update',async()=>{
 const {ctx,reject,nodes}=setup();const call=ctx.window.loadCalendar();reject(Error('Offline'));await call;assert.equal(ctx.calendarEvents[0].id,'saved');assert.equal(ctx.calendarChecked,100);assert.match(nodes.calendarStatus.textContent,/Showing saved meetings/);
});
