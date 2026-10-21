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
