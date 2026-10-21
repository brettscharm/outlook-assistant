import unittest
from datetime import datetime,timezone
from outlook_plugin.calendar_cache import normalize,instant
class CalendarTests(unittest.TestCase):
 def test_time_requires_zone_and_supports_v8_dates(self):
  self.assertIsNone(instant('2026-10-21T12:00:00'))
  self.assertEqual(instant({'$date':'2026-10-21T12:00:00Z'}).hour,12)
 def test_latest_cancellation_suppresses_old_event_and_series_not_expanded(self):
  now=datetime(2026,10,21,tzinfo=timezone.utc)
  event=dict(account='a',iCalUID='one',subject='Synthetic',startTime={'$date':'2026-10-22T12:00:00Z'},endTime={'$date':'2026-10-22T13:00:00Z'},lastModifiedTime='2026-10-20T00:00:00Z')
  cancelled=dict(event,isCancelled=True,lastModifiedTime='2026-10-21T00:00:00Z')
  rows,_=normalize([cancelled,event,dict(event,iCalUID='master',eventType='RecurringMaster')],now,30)
  self.assertEqual(rows,[])
 def test_bad_range_rejected_and_accounts_not_merged(self):
  now=datetime(2026,10,21,tzinfo=timezone.utc)
  event=dict(account='a',iCalUID='one',startTime='2026-10-22T12:00:00Z',endTime='2026-10-22T13:00:00Z')
  rows,skipped=normalize([event,dict(event,account='b'),dict(event,iCalUID='bad',endTime='2026-10-20T00:00:00Z')],now,30)
  self.assertEqual(len(rows),2);self.assertEqual(skipped,1)
 def test_embedded_outlook_occurrences_and_drafts(self):
  now=datetime(2026,10,21,tzinfo=timezone.utc)
  row=dict(account='user@example.com',iCalUID='instance',startTime='2026-10-22T12:00:00.000Z',endTime='2026-10-22T13:00:00.000Z',eventType='Exception',source='Teams calendar',responseType='Accept')
  events,skipped=normalize([row,dict(row,iCalUID='draft',isDraft=True)],now,30)
  self.assertEqual(len(events),1);self.assertEqual(events[0]['response'],'Accept');self.assertEqual(events[0]['source'],'Teams calendar');self.assertEqual(skipped,0)

 def test_meeting_link_survives_reschedule(self):
  now=datetime(2026,10,21,tzinfo=timezone.utc)
  event=dict(account='a',objectId='stable-id',iCalUID='uid',startTime='2026-10-22T12:00:00Z',endTime='2026-10-22T13:00:00Z')
  first,_=normalize([event],now,30)
  later,_=normalize([dict(event,startTime='2026-10-23T14:00:00Z',endTime='2026-10-23T15:00:00Z')],now,30)
  self.assertEqual(first[0]['meeting_id'],later[0]['meeting_id'])
 def test_explicit_calendar_range_includes_past_events(self):
  from unittest.mock import patch
  import time
  from outlook_plugin import calendar_cache as c
  row=dict(account='a',objectId='past',startTime='2026-09-22T12:00:00Z',endTime='2026-09-22T13:00:00Z')
  with patch.dict(c._CACHE,{'checked':time.time(),'events':[row]},clear=True):
   data=c.snapshot(start='2026-09-01T00:00:00Z',end='2026-10-01T00:00:00Z')
   self.assertEqual(len(data['events']),1)
   self.assertEqual(c.snapshot(start='2026-10-01T00:00:00Z',end='2026-11-01T00:00:00Z')['events'],[])
  for start,end in [('invalid','invalid'),('2026-01-01T00:00:00Z','2027-01-01T00:00:00Z'),('2026-10-01','2026-10-02')]:
   with self.assertRaises(ValueError):c.snapshot(start=start,end=end)

 def test_call_links_from_meeting_fields_and_location(self):
  from outlook_plugin.calendar_cache import meeting_url
  self.assertEqual(meeting_url({'skypeTeamsMeetingUrl':'https://teams.microsoft.com/l/meetup-join/example?context=x&y=z'}),'https://teams.microsoft.com/l/meetup-join/example?context=x&y=z')
  self.assertEqual(meeting_url({'location':'Join: https://example.webex.com/meet/room'}),'https://example.webex.com/meet/room')
  for value in ('javascript:alert(1)','https://user:pass@example.com/','https://example.com/[redacted]'):
   self.assertEqual(meeting_url({'skypeTeamsMeetingUrl':value}),'')

 def test_attendees_are_deduplicated_and_invalid_addresses_not_copyable(self):
  now=datetime(2026,10,21,tzinfo=timezone.utc)
  row=dict(account='a',objectId='event',startTime='2026-10-22T12:00:00Z',endTime='2026-10-22T13:00:00Z',attendeesAvailable=True,organizerEmail='HOST@example.com',attendees=[{'name':'Pat','email':'PAT@example.com','type':'required','response':'Accept'},{'name':'Pat duplicate','email':'pat@example.com','type':'optional'},{'name':'Room','email':'room@example.com','type':'resource'},{'name':'Name only','email':'invalid'}])
  events,_=normalize([row],now,30);event=events[0]
  self.assertEqual(len(event['attendees']),3)
  self.assertEqual(event['attendees'][0],{'name':'Pat','email':'pat@example.com','type':'required','response':'Accept'})
  self.assertEqual(event['attendees'][2]['email'],'')
  self.assertEqual(event['organizer_email'],'host@example.com')
  self.assertTrue(event['attendees_available'])
  row.pop('attendeesAvailable');row.pop('attendees')
  events,_=normalize([row],now,30)
  self.assertFalse(events[0]['attendees_available']);self.assertEqual(events[0]['attendees'],[])
