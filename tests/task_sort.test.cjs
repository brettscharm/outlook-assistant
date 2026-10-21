const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('outlook_plugin/static/tasks-ui.js','utf8');
const start=source.indexOf('function taskDeadline('),end=source.indexOf('\nfunction ',source.indexOf('function compareTasks(')+1);
const context=vm.createContext({localToday:()=> '2026-03-08'});
vm.runInContext(source.slice(start,end),context);
for(const [date,urgency] of [['2026-03-07','overdue'],['2026-03-08','today'],['2026-03-09','soon'],['2026-03-11','soon'],['2026-03-12',''],['','']]){
 assert.equal(context.taskDeadline({due_date:date}).urgency,urgency);
 assert.equal(context.taskDeadline({due_date:date,completed:true}).urgency,'');
}
const items=[{id:'a',due_date:'2026-03-08',priority:'low'},{id:'b',due_date:'2026-03-12',priority:'high'},{id:'c',priority:'none'}];
for(const [mode,order] of [['due-asc','abc'],['due-desc','bac'],['priority-desc','bac'],['priority-asc','abc']])assert.equal([...items].sort((a,b)=>context.compareTasks(a,b,mode)).map(t=>t.id).join(''),order);
console.log('Deadline and sorting checks passed.');
const originalTimezone=process.env.TZ;
const meeting={id:'meeting',deadline:{kind:'meeting',due_at:'2026-11-02T15:30:00+00:00'}};
process.env.TZ='America/New_York';assert.match(context.taskDeadline(meeting).label,/10:30/);
process.env.TZ='America/Los_Angeles';assert.match(context.taskDeadline(meeting).label,/7:30/);
assert.equal(context.taskDeadline(meeting).sortTime,Date.parse('2026-11-02T15:30:00Z'));
if(originalTimezone===undefined)delete process.env.TZ;else process.env.TZ=originalTimezone;
console.log('Meeting deadlines follow the system timezone without changing their instant.');
