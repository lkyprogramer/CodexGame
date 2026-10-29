import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from lab.eligibility import qualify


class RegistryEligibilityTests(unittest.TestCase):
    def run_gate(self,pr,entry,cache=512):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);config=root/'production.json'
            config.write_text(json.dumps({'args':[],'user_args':[],'env':{'STRATA_ADAPT_OVERLAP':'1'}}))
            c={'workspace':str(root/'workspace'),'deployed_config':str(config),'conversation_cache_mib':cache}
            with patch('lab.eligibility.experiment',return_value=entry):return qualify(c,pr)

    def test_disabled_research_or_historical_entry_cannot_qualify(self):
        report=self.run_gate(3453,{'execution_disabled':True})
        self.assertTrue(report['blocks'])
        self.assertNotEqual(report['status'],'NEEDS_MECHANISM_PROBE')

    def test_registry_specific_mechanism_probes_are_preserved(self):
        report=self.run_gate(2253,{'required_probes':['measure allocator residency on the pinned candidate']})
        self.assertIn('measure allocator residency on the pinned candidate',report['required_probes'])

    def test_new_cache_prs_reject_cache_off_profile(self):
        for pr in (4031,4002):
            with self.subTest(pr=pr):
                self.assertTrue(self.run_gate(pr,{},cache=0)['blocks'])

    def test_positive_cache_budget_is_only_a_probe_candidate(self):
        for pr in (4031,4002):
            with self.subTest(pr=pr):
                report=self.run_gate(pr,{},cache=512)
                self.assertEqual(report['status'],'NEEDS_MECHANISM_PROBE')
                self.assertTrue(report['required_probes'])
