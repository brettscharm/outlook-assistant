import json,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import calendar_cache as c

class SnapshotTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  for key,value in [('CACHE_FILE',Path(tmp.name)/'calendar.json'),('_CACHE',{}),('_LOCK',threading.Lock()),('_REFRESH_LOCK',threading.Lock()),('_DISK_LOADED',False),('_LAST_ATTEMPT',0),('_LAST_ERROR','')]:
   p=patch.object(c,key,value);p.start();self.addCleanup(p.stop)
  self.row={'objectId':'saved','subject':'Saved meeting','startTime':'2026-10-22T12:00:00Z','endTime':'2026-10-22T13:00:00Z'}
  self.options={'start':'2026-10-21T00:00:00Z','end':'2026-10-24T00:00:00Z'}
 def finish(self):
  self.assertTrue(c._REFRESH_LOCK.acquire(timeout=3));c._REFRESH_LOCK.release()
 def test_disk_snapshot_returns_while_one_refresh_is_running(self):
  c.CACHE_FILE.write_text(json.dumps({'events':[self.row],'checked':time.time()-3600}))
  started=threading.Event();release=threading.Event()
  def read():
   started.set();release.wait(3)
   return {'events':[dict(self.row,subject='Updated meeting')],'checked':time.time()}
  with patch.object(c,'_read_calendar',side_effect=read) as reader:
   try:
    before=time.monotonic();result=c.snapshot(background=True,**self.options)
    self.assertLess(time.monotonic()-before,1);self.assertEqual(result['events'][0]['subject'],'Saved meeting')
    self.assertTrue(started.wait(1));self.assertTrue(result['refreshing'])
    c.snapshot(background=True,force=True,**self.options);self.assertEqual(reader.call_count,1)
   finally:release.set();self.finish()
   self.assertEqual(c.snapshot(background=True,**self.options)['events'][0]['subject'],'Updated meeting')
  self.assertEqual(c.CACHE_FILE.stat().st_mode&0o777,0o600)
  c._CACHE.clear();c._DISK_LOADED=False
  with patch.object(c,'_read_calendar') as reader:
   self.assertEqual(c.snapshot(background=True,**self.options)['events'][0]['subject'],'Updated meeting');reader.assert_not_called()
 def test_failed_refresh_preserves_saved_file_and_does_not_retry_loop(self):
  saved={'events':[self.row],'checked':time.time()-3600};raw=json.dumps(saved);c.CACHE_FILE.write_text(raw)
  with patch.object(c,'_read_calendar',side_effect=RuntimeError('private path')) as reader:
   c.snapshot(background=True,**self.options);self.finish()
   result=c.snapshot(background=True,**self.options)
   self.assertEqual(result['events'][0]['subject'],'Saved meeting');self.assertIn('refresh failed',result['refresh_error']);self.assertNotIn('private',result['refresh_error']);self.assertEqual(reader.call_count,1)
  self.assertEqual(c.CACHE_FILE.read_text(),raw)
 def test_first_read_is_empty_but_refreshes_without_blocking(self):
  gate=threading.Event()
  def read():gate.wait(3);return {'events':[],'checked':time.time()}
  with patch.object(c,'_read_calendar',side_effect=read):
   try:
    result=c.snapshot(background=True,**self.options);self.assertFalse(result['has_snapshot']);self.assertIsNone(result['checked']);self.assertEqual(result['events'],[])
   finally:gate.set();self.finish()
   self.assertTrue(c.snapshot(background=True,**self.options)['has_snapshot'])
