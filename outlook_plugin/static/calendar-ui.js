'use strict';
function calendarDay(value){const d=new Date(value);d.setHours(0,0,0,0);return d;}
function calendarAddDays(value,count){const d=calendarDay(value);d.setDate(d.getDate()+count);return d;}
function calendarDateKey(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function calendarRange(anchor,mode){
 const day=calendarDay(anchor);if(mode==='day')return {start:day,end:calendarAddDays(day,1),days:1};
 let days=7;if(mode==='month'){day.setDate(1);days=Math.ceil(((day.getDay()+6)%7+new Date(day.getFullYear(),day.getMonth()+1,0).getDate())/7)*7;}
 day.setDate(day.getDate()-(day.getDay()+6)%7);
 return {start:day,end:calendarAddDays(day,days),days};
}
function calendarOverlaps(event,day){return new Date(event.start_time)<calendarAddDays(day,1)&&new Date(event.end_time)>day;}
function calendarTimedLayout(events,day){
 const next=calendarAddDays(day,1),minute=d=>d.getHours()*60+d.getMinutes()+d.getSeconds()/60;
 const rows=events.filter(e=>!e.all_day&&calendarOverlaps(e,day)).map(event=>{const start=new Date(event.start_time),end=new Date(event.end_time);const top=start<day?0:minute(start),bottom=end>=next?1440:minute(end);return {event,top,bottom:Math.max(top+20,bottom)};}).sort((a,b)=>a.top-b.top||b.bottom-a.bottom);
 let cluster=[],end=-1;
 const finish=()=>{const columns=[];for(const row of cluster){let column=columns.findIndex(bottom=>bottom<=row.top);if(column<0)column=columns.length;columns[column]=row.bottom;row.column=column;}for(const row of cluster)row.columns=columns.length;cluster=[];};
 for(const row of rows){if(row.top>=end){finish();end=-1;}cluster.push(row);end=Math.max(end,row.bottom);}finish();return rows;
}
function calendarVisibleDays(range,mode,hideWeekends){
 return Array.from({length:range.days},(_,i)=>calendarAddDays(range.start,i)).filter(day=>mode==='day'||!hideWeekends||![0,6].includes(day.getDay()));
}
let calendarHideWeekends=false;
try{calendarHideWeekends=localStorage.getItem('outlook-calendar-hide-weekends')==='true';}catch{}
let calendarMode='month',calendarAnchor=calendarDay(new Date()),calendarEvents=[],calendarRequest=0,calendarChecked=null;
try{const saved=localStorage.getItem('outlook-calendar-view');if(['month','week','day'].includes(saved))calendarMode=saved;}catch{}
const calendarTime=value=>new Date(value).toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'});
function showCalendarMeeting(event){
 $('calendarMeetingTitle').textContent=event.subject;const root=$('calendarMeetingDetails');root.replaceChildren();
 root.append(text('p',event.all_day?'All day · '+new Date(event.start_time).toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric',year:'numeric'}):new Date(event.start_time).toLocaleString(undefined,{weekday:'long',month:'long',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})+' – '+new Date(event.end_time).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})));
 if(event.organizer)root.append(text('p','Organizer · '+event.organizer));if(event.location)root.append(text('p','Location · '+event.location));
 try{const url=new URL(event.join_url);if(url.protocol==='https:'&&!url.username&&!url.password&&!event.join_url.includes('[redacted]')){const join=text('a','Join meeting','feedback-link');join.href=url.href;join.target='_blank';join.rel='noopener noreferrer';root.append(join);}}catch{}
 if(!root.querySelector('a'))root.append(text('p','No call link was found in this cached event. Open the invitation in Outlook or Teams.','muted small'));
 const attendees=event.attendees||[];
 root.append(text('h3','Invited people'));
 if(attendees.length){
  const list=text('div','','meeting-attendees');
  for(const person of attendees){const row=text('div','','meeting-attendee');row.append(text('strong',person.name||person.email),text('span',[person.email,person.type==='invited'?'':person.type,person.response].filter(Boolean).join(' · '),'muted small'));list.append(row);}root.append(list);
  const addresses=[...new Set(attendees.filter(p=>p.type!=='resource'&&p.email).map(p=>p.email))];
  if(addresses.length){const actions=text('div','','actions');const create=text('button','Create group');create.onclick=()=>busy(create,async()=>{await window.createGroupFromMeeting(event);});const copy=text('button','Copy emails');copy.onclick=()=>copyGroupEmails(addresses);actions.append(create,copy);root.append(actions);}
 }else root.append(text('p',event.attendees_available?'No invitees are listed in this cached event.':'The invitee list was not saved in this calendar cache. Open the invitation in Outlook or Teams.','muted small'));
 root.append(text('p','Saved calendar event · Changes are made in Teams or Outlook.','muted small'));if(!$('calendarMeeting').open)$('calendarMeeting').showModal();
}
function calendarEventButton(event,compact=false){
 const button=text('button','','calendar-event');button.type='button';button.title=event.subject+' · '+(event.all_day?'All day':calendarTime(event.start_time)+' – '+calendarTime(event.end_time));button.setAttribute('aria-label',button.title);button.onclick=()=>showCalendarMeeting(event);
 if(!event.all_day)button.append(text('span',calendarTime(event.start_time),'calendar-event-time'));button.append(text('span',event.subject,'calendar-event-title'));if(!compact&&!event.all_day)button.append(text('small',calendarTime(event.end_time)));return button;
}
function chooseCalendarDay(day){calendarAnchor=calendarDay(day);calendarMode='day';saveCalendarMode();renderCalendar();}
function showCalendarDay(day){
 $('calendarMeetingTitle').textContent=day.toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric'});
 const root=$('calendarMeetingDetails');root.replaceChildren();
 const events=calendarEvents.filter(e=>calendarOverlaps(e,day)).sort((a,b)=>Number(b.all_day)-Number(a.all_day)||new Date(a.start_time)-new Date(b.start_time));
 const list=text('div','','calendar-day-list');for(const event of events)list.append(calendarEventButton(event));root.append(list);
 const open=text('button','Open day view');open.type='button';open.onclick=()=>{$('calendarMeeting').close();chooseCalendarDay(day);};root.append(open);$('calendarMeeting').showModal();
}
function saveCalendarMode(){try{localStorage.setItem('outlook-calendar-view',calendarMode);}catch{}}
function renderCalendar(){
 const range=calendarRange(calendarAnchor,calendarMode),days=calendarVisibleDays(range,calendarMode,calendarHideWeekends),root=$('calendarEvents');$('calendarHideWeekends').checked=calendarHideWeekends;$('calendarHideWeekendsControl').hidden=calendarMode==='day';root.style.setProperty('--calendar-columns',calendarHideWeekends?5:7);const oldScroll=root.querySelector('.calendar-time-scroll')?.scrollTop;root.replaceChildren();
 $('calendarDate').value=calendarDateKey(calendarAnchor);$('calendarTimezone').textContent=Intl.DateTimeFormat().resolvedOptions().timeZone.replaceAll('_',' ');
 $('calendarTitle').textContent=calendarMode==='month'?calendarAnchor.toLocaleDateString(undefined,{month:'long',year:'numeric'}):calendarMode==='day'?calendarAnchor.toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric',year:'numeric'}):range.start.toLocaleDateString(undefined,{month:'short',day:'numeric'})+' – '+days[days.length-1].toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
 document.querySelectorAll('[data-calendar-view]').forEach(b=>{b.classList.toggle('selected',b.dataset.calendarView===calendarMode);b.setAttribute('aria-pressed',String(b.dataset.calendarView===calendarMode));});
 const today=calendarDateKey(new Date());
 if(calendarMode==='month'){
  const headings=text('div','','calendar-weekdays');for(const day of days.slice(0,calendarHideWeekends?5:7))headings.append(text('span',day.toLocaleDateString(undefined,{weekday:'short'})));root.append(headings);
  const grid=text('div','','calendar-month');grid.style.setProperty('--calendar-weeks',range.days/7);
  for(const day of days){const cell=text('section','','calendar-month-day'+(day.getMonth()!==calendarAnchor.getMonth()?' outside-month':''));cell.setAttribute('aria-label',day.toLocaleDateString(undefined,{dateStyle:'full'}));const number=text('button',String(day.getDate()),'calendar-day-number'+(calendarDateKey(day)===today?' is-today':''));number.type='button';number.setAttribute('aria-label','View '+day.toLocaleDateString(undefined,{dateStyle:'full'}));number.onclick=()=>chooseCalendarDay(day);cell.append(number);const events=calendarEvents.filter(e=>calendarOverlaps(e,day)).sort((a,b)=>Number(b.all_day)-Number(a.all_day)||new Date(a.start_time)-new Date(b.start_time));for(const event of events.slice(0,3))cell.append(calendarEventButton(event,true));if(events.length>3){const more=text('button','+'+(events.length-3)+' more','calendar-more');more.type='button';more.setAttribute('aria-label','Show all '+events.length+' meetings on '+day.toLocaleDateString());more.onclick=()=>showCalendarDay(day);cell.append(more);}grid.append(cell);}root.append(grid);return;
 }
 const shell=text('div','','calendar-agenda calendar-'+calendarMode),head=text('div','','calendar-agenda-head');head.style.setProperty('--calendar-days',days.length);head.append(text('span','All day','calendar-gutter'));
 for(const day of days){const col=text('div','','calendar-agenda-date');const label=text('button',day.toLocaleDateString(undefined,{weekday:'short',day:'numeric'}),'calendar-date-heading'+(calendarDateKey(day)===today?' is-today':''));label.onclick=()=>chooseCalendarDay(day);col.append(label);for(const event of calendarEvents.filter(e=>e.all_day&&calendarOverlaps(e,day)))col.append(calendarEventButton(event,true));head.append(col);}shell.append(head);
 const scroll=text('div','','calendar-time-scroll'),timeline=text('div','','calendar-timeline');timeline.style.setProperty('--calendar-days',days.length);const hours=text('div','','calendar-hour-labels');
 for(let hour=0;hour<24;hour++){const label=text('span',new Date(2026,0,1,hour).toLocaleTimeString(undefined,{hour:'numeric'}));label.style.top=(hour*64)+'px';hours.append(label);}timeline.append(hours);
 for(const day of days){const col=text('div','','calendar-time-day');col.setAttribute('aria-label',day.toLocaleDateString(undefined,{dateStyle:'full'}));for(const row of calendarTimedLayout(calendarEvents,day)){const button=calendarEventButton(row.event);button.style.top=(row.top/60*64)+'px';button.style.height=(Math.min(1440-row.top,row.bottom-row.top)/60*64)+'px';button.style.left=`calc(${row.column/row.columns*100}% + 2px)`;button.style.width=`calc(${100/row.columns}% - 4px)`;col.append(button);}if(calendarDateKey(day)===today){const now=new Date(),line=text('div','','calendar-now');line.style.top=((now.getHours()+now.getMinutes()/60)*64)+'px';line.setAttribute('aria-label','Current time');col.append(line);}timeline.append(col);}scroll.append(timeline);shell.append(scroll);root.append(shell);head.style.paddingRight=(scroll.offsetWidth-scroll.clientWidth)+'px';scroll.scrollTop=oldScroll??8*64;
}
window.loadCalendar=async(force=false)=>{
 const request=++calendarRequest,range=calendarRange(calendarAnchor,calendarMode);$('refreshCalendar').disabled=true;$('calendarStatus').textContent='Reading calendar…';calendarEvents=[];renderCalendar();
 try{const q=new URLSearchParams({from:range.start.toISOString(),to:range.end.toISOString()});if(force===true)q.set('refresh','1');const data=await api('/api/calendar?'+q);if(request!==calendarRequest)return;calendarEvents=data.events;calendarChecked=data.checked;renderCalendar();$('calendarStatus').textContent=data.events.length+' meetings cached · Last read '+date(new Date(data.checked*1000).toISOString(),true)+(data.skipped?' · Some records could not be read.':'')+(!data.events.length?' · No meetings cached for these dates.':'');}catch(e){if(request===calendarRequest)$('calendarStatus').textContent=e.message;}finally{if(request===calendarRequest)$('refreshCalendar').disabled=false;}
};
for(const button of document.querySelectorAll('[data-calendar-view]'))button.onclick=()=>{calendarMode=button.dataset.calendarView;saveCalendarMode();window.loadCalendar();};
function shiftCalendar(direction){if(calendarMode==='month'){calendarAnchor.setDate(1);calendarAnchor.setMonth(calendarAnchor.getMonth()+direction);}else calendarAnchor=calendarAddDays(calendarAnchor,direction*(calendarMode==='week'?7:1));window.loadCalendar();}
$('calendarPrevious').onclick=()=>shiftCalendar(-1);$('calendarNext').onclick=()=>shiftCalendar(1);$('calendarToday').onclick=()=>{calendarAnchor=calendarDay(new Date());window.loadCalendar();};$('calendarDate').onchange=()=>{if($('calendarDate').value){calendarAnchor=calendarDay(new Date($('calendarDate').value+'T12:00:00'));window.loadCalendar();}};
$('refreshCalendar').onclick=()=>window.loadCalendar(true);$('closeCalendarMeeting').onclick=()=>$('calendarMeeting').close();
setInterval(()=>{if($('calendar').classList.contains('active')&&!document.hidden&&!$('calendarMeeting').open)window.loadCalendar();},60000);

$('calendarHideWeekends').onchange=()=>{calendarHideWeekends=$('calendarHideWeekends').checked;try{localStorage.setItem('outlook-calendar-hide-weekends',String(calendarHideWeekends));}catch{}renderCalendar();};
