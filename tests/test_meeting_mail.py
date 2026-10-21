import unittest
from outlook_plugin.meeting_mail import discover,parse_ics
class MeetingMailTests(unittest.TestCase):
 def test_deleted_folder_included_without_claiming_acceptance(self):
  class Engine:
   def get_emails(self,**kw):
    assert kw['folder']=='all'
    return [{'id':'deleted','subject':'Accepted: Planning meeting','folder':'Deleted Items','received_time':'2026-10-21'}]
   def get_email_details(self,id):return {'body':''}
   def get_active_backend(self):return self
  data=discover(Engine());self.assertTrue(data['includes_deleted']);self.assertEqual(data['items'][0]['folder'],'Deleted Items');self.assertEqual(data['items'][0]['details'],[])
 def test_structured_times_and_cancellation_are_evidence_only(self):
  rows=parse_ics('BEGIN:VCALENDAR\nMETHOD:CANCEL\nBEGIN:VEVENT\nUID:fixture\nDTSTART:20261022T120000Z\nDTEND:20261022T130000Z\nSTATUS:CANCELLED\nRRULE:FREQ=WEEKLY\nEND:VEVENT\nEND:VCALENDAR')
  self.assertEqual(rows[0]['status'],'CANCELLED');self.assertEqual(rows[0]['start_time'],'2026-10-22T12:00:00+00:00');self.assertEqual(len(rows),1)
 def test_floating_time_not_assumed_to_be_local(self):
  rows=parse_ics('BEGIN:VEVENT\nDTSTART:20261022T120000\nEND:VEVENT')
  self.assertEqual(rows[0]['start_time'],'')
