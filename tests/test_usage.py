import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from outlook_plugin import usage
class UsageTests(unittest.TestCase):
    def test_persistent_totals_separate_unknown_from_zero_and_exclude_content(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(usage,'USAGE_FILE',Path(tmp)/'usage.json'):
            usage.record(True,{'session_costs':.3,'prompt':'private content','api_key':'secret'})
            usage.record(False,{})
            usage.record(True,{'session_costs':0})
            usage.record(False,{'session_costs':'NaN'})
            data=json.loads(usage.USAGE_FILE.read_text());total=data['total']
            self.assertEqual({k:total[k] for k in ('requests','succeeded','failed','reported_units','unreported')},dict(requests=4,succeeded=2,failed=2,reported_units=.3,unreported=2))
            self.assertNotIn('private content',usage.USAGE_FILE.read_text());self.assertNotIn('secret',usage.USAGE_FILE.read_text())
            self.assertEqual(usage.USAGE_FILE.stat().st_mode&0o777,0o600)
    def test_tracking_failure_does_not_break_ai_request(self):
        with patch.object(usage,'write_json',side_effect=OSError('disk full')),patch.object(usage,'read_json',return_value={'started_at':'today','total':usage.empty(),'days':{}}):
            usage.record(True,{'session_costs':1})
            self.assertTrue(usage.LAST_ERROR)
        usage.LAST_ERROR=False

    def test_tokens_preserve_missing_counts_and_migrate_old_totals(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(usage,'USAGE_FILE',Path(tmp)/'usage.json'):
            usage.USAGE_FILE.write_text(json.dumps({'started_at':'2026-01-01','total':dict(requests=2,succeeded=2,failed=0,reported_units=.2,unreported=0),'days':{}}))
            usage.record(True,{'session_costs':.1,'input_tokens':120,'output_tokens':30,'cache_read_tokens':0,'cache_write_tokens':-1})
            data=json.loads(usage.USAGE_FILE.read_text())['total']
            self.assertEqual(data['requests'],3)
            self.assertEqual(data['input_tokens'],120)
            self.assertEqual(data['input_tokens_reports'],1)
            self.assertEqual(data['cache_read_tokens_reports'],1)
            self.assertEqual(data['cache_write_tokens_reports'],0)
