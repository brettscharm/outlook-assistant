const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('project meeting fields retain timezone precision, links and editable notes',()=>{
 const nodes=[];
 class Element{constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.events={};nodes.push(this);}append(...items){this.children.push(...items);}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}addEventListener(k,f){this.events[k]=f;}}
 const ids={};const $=id=>ids[id]||(ids[id]=new Element('div'));const text=(tag,value='')=>{const e=new Element(tag);e.textContent=value;return e;};
 const ctx={editingProject:null,window:{},$,text,crypto:require('node:crypto').webcrypto,document:{createElement:tag=>new Element(tag)},Date,URL,URLSearchParams,queueProjectSave(){},confirm:()=>true};
 const source=fs.readFileSync('outlook_plugin/static/organize-ui.js','utf8');vm.runInNewContext(source.slice(source.indexOf('function addProjectMeetingRow(')),ctx);
 const meeting={id:'meeting1',title:'Discovery',occurred_at:'2026-10-20T10:00:29-04:00',recording_url:'https://example.com/recording',meeting_url:'https://teams.microsoft.com/meet',calendar_id:'event1',transcript:'Alex: Send the proposal.',recording_file_id:'recording1'};
 const row=ctx.addProjectMeetingRow(meeting);let saved=row.meetingValue();assert.equal(saved.occurred_at,meeting.occurred_at);assert.equal(saved.calendar_id,'event1');assert.equal(saved.transcript,meeting.transcript);assert.equal(saved.recording_file_id,'recording1');assert.equal(saved.recording_url,meeting.recording_url);
 const field=label=>nodes.find(n=>n.attrs['aria-label']===label);field('Meeting notes').value='Send follow-up';assert.equal(row.meetingValue().notes,'Send follow-up');
 field('Meeting date & time').value='2026-10-21T15:30';assert.equal(row.meetingValue().occurred_at,new Date('2026-10-21T15:30').toISOString());
 const recording=nodes.find(n=>n.tag==='a'&&n.textContent==='Open recording');assert.equal(recording.hidden,false);field('Recording link').value='javascript:alert(1)';field('Recording link').events.input();assert.equal(recording.hidden,true);
});
