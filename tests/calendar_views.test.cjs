const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('outlook_plugin/static/calendar-ui.js','utf8');const context=vm.createContext({});vm.runInContext(source.slice(0,source.indexOf("let calendarMode=")),context);
const old=process.env.TZ;process.env.TZ='America/New_York';
let range=context.calendarRange(new Date(2026,2,8),'day');assert.equal((range.end-range.start)/3600000,23);
range=context.calendarRange(new Date(2026,10,1),'day');assert.equal((range.end-range.start)/3600000,25);
range=context.calendarRange(new Date(2026,9,21),'month');assert.equal(range.days,35);assert.equal(range.start.getDay(),1);
const day=new Date(2026,9,22),event=(id,start,end)=>({id,start_time:'2026-10-22T'+start+':00-04:00',end_time:'2026-10-22T'+end+':00-04:00'});
const layout=context.calendarTimedLayout([event('a','09:00','10:00'),event('b','09:30','10:30'),event('c','11:00','12:00')],day);
assert.equal(layout[0].columns,2);assert.equal(layout[1].column,1);assert.equal(layout[2].columns,1);
assert.equal(context.calendarOverlaps({start_time:'2026-10-21T23:00:00-04:00',end_time:'2026-10-22T00:00:00-04:00'},day),false);
if(old===undefined)delete process.env.TZ;else process.env.TZ=old;
console.log('Calendar ranges, DST boundaries, midnight edges, and overlapping events passed.');

assert.equal(context.calendarRange(new Date(2026,7,21),'month').days,42);

// Overflow uses already-loaded events and opens the meeting list without a cache request.
const nodes={calendarMeetingTitle:{},calendarMeetingDetails:{children:[],replaceChildren(){this.children=[];},append(...items){this.children.push(...items);}},calendarMeeting:{open:false,showModal(){this.open=true;},close(){this.open=false;}}};
const dayContext=vm.createContext({$:id=>nodes[id],text:(tag,label)=>({tag,label,children:[],append(...items){this.children.push(...items);}}),calendarOverlaps:()=>true,calendarEvents:[{subject:'One',start_time:'2026-10-22T08:00:00Z'},{subject:'Two',start_time:'2026-10-22T09:00:00Z'}],calendarEventButton:event=>({event}),chooseCalendarDay(){throw Error('Should not change the view until requested');}});
vm.runInContext(source.slice(source.indexOf('function showCalendarDay('),source.indexOf('function saveCalendarMode')),dayContext);
dayContext.showCalendarDay(new Date(2026,9,22));assert.equal(nodes.calendarMeeting.open,true);assert.equal(nodes.calendarMeetingDetails.children[0].children.length,2);
