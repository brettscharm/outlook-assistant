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
            self.assertEqual(total,dict(requests=4,succeeded=2,failed=2,reported_units=.3,unreported=2))
            self.assertNotIn('private content',usage.USAGE_FILE.read_text());self.assertNotIn('secret',usage.USAGE_FILE.read_text())
            self.assertEqual(usage.USAGE_FILE.stat().st_mode&0o777,0o600)
    def test_tracking_failure_does_not_break_ai_request(self):
        with patch.object(usage,'write_json',side_effect=OSError('disk full')),patch.object(usage,'read_json',return_value={'started_at':'today','total':usage.empty(),'days':{}}):
            usage.record(True,{'session_costs':1})
            self.assertTrue(usage.LAST_ERROR)
        usage.LAST_ERROR=False
