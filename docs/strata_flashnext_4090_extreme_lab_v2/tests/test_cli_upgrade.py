import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from test_offline_plan import plan_fixture
import test_planned_statistics as planned_stats


class CliUpgradeTests(unittest.TestCase):
    def call(self, *args):
        return subprocess.run([sys.executable,'-B','-m','lab.cli',*args],
                              cwd=Path(__file__).resolve().parents[1],
                              env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)

    def test_offline_plan_cli_needs_no_local_gpu_config(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'plan.json';p.write_text(json.dumps(plan_fixture()))
            result=self.call('validate-plan','--plan',str(p))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['execution_result'],'NOT_RUN')

    def test_stats_cli_accepts_explicit_pair_and_time_metric(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);planned_stats.PlannedStatisticsTests().fixture(p)
            result=self.call('stats','--results',str(p),'--pair','p:base','--metric','decode_ms')
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads(result.stdout)
            self.assertAlmostEqual(report['comparisons']['p_vs_base']['improvement_pct'],100*(1-7/9))

    def test_stats_cli_refuses_incomplete_results_after_writing_report(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);test=planned_stats.PlannedStatisticsTests();rows=test.fixture(p)
            test.write(p,rows[:-1])
            result=self.call('stats','--results',str(p))
            self.assertEqual(result.returncode,2,result.stdout)
            self.assertTrue((p/'summary.json').exists())

    def test_stats_cli_refuses_missing_plan_hash_after_writing_report(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);planned_stats.PlannedStatisticsTests().fixture(p)
            plan=json.loads((p/'campaign.json').read_text())
            del plan['cases'][0]['request_sha256']
            (p/'campaign.json').write_text(json.dumps(plan))
            result=self.call('stats','--results',str(p))
            self.assertEqual(result.returncode,2,result.stdout)
            report=json.loads((p/'summary.json').read_text())
            self.assertEqual(report['decision'],'INCOMPLETE_OR_INVALID')
            self.assertTrue(any('planned request_sha256' in x for x in report['invalid_pairs']))
