from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/hc_scratch'))
import perf


def fixtures(task, ttft_ratio=.94, wall_ratio=1.0, decode_ratio=1.0):
    cases = [{'id': 'think-102400', 'request_sha256': 'long', 'counted_prompt_tokens': 102400},
             {'id': 'think-4096', 'request_sha256': 'short', 'counted_prompt_tokens': 4095}]
    appends = [{'case': {'id': 'append-prime', 'request_sha256': 'prime', 'counted_prompt_tokens': 32771}},
               {'case': {'id': 'append-0', 'request_sha256': 'append', 'counted_prompt_tokens': 35993}}]
    (task / 'cases.json').write_text(json.dumps(cases)); (task / 'append.json').write_text(json.dumps(appends))
    for row in perf.schedule():
        folder = task / f"{row['index']:02d}-{row['group']}-{row['arm']}"; folder.mkdir()
        (folder / 'RUN_RESULT.json').write_text(json.dumps({'status': 'PASS', 'identity': row}))
        selected = [cases[0 if row['group'] == '100K' else 1]] if row['group'] != 'append' else [x['case'] for x in appends]
        results = []
        for c in selected:
            candidate = row['arm'] == 'C'
            results.append({'id': c['id'], 'request_sha256': c['request_sha256'], 'score': {'pass': True}, 'metrics': {
                'prompt_tokens': c['counted_prompt_tokens'], 'read_tokens': 3225 if c['id'] == 'append-0' else c['counted_prompt_tokens'],
                'reused_tokens': 32768 if c['id'] == 'append-0' else 0, 'generated_tokens': 2 if row['group'] == 'append' else 2048,
                'ttft_s': 100 * (ttft_ratio if candidate else 1), 'wall_s': 200 * (wall_ratio if candidate else 1),
                'decode_ms': 100000 * (decode_ratio if candidate else 1)}})
        (folder / 'RESULTS.json').write_text(json.dumps(results))


class PerfTests(unittest.TestCase):
    def test_exact_pair_schedule_and_whole_round_bootstrap(self):
        rows = perf.schedule()
        self.assertEqual(len(rows), 20)
        self.assertEqual(sum(2 if r['group'] == 'append' else 1 for r in rows), 24)
        self.assertEqual([r['arm'] for r in rows[:12]], list('AC C A C A A C A C C A'.replace(' ', '')))
        result = perf.paired_exact([100] * 6, [90] * 6)
        self.assertEqual(result['bootstrap_draws'], 46656)
        self.assertAlmostEqual(result['improvement_pct'], 10)
        self.assertAlmostEqual(result['ratio_ci95'][0], .9)
        self.assertAlmostEqual(result['ratio_ci95'][1], .9)
        with self.assertRaises(ValueError): perf.paired_exact([1] * 5, [1] * 5)
        with self.assertRaises(ValueError): perf.paired_exact([1] * 6, [float('nan')] * 6)

    def test_ttft_and_full_request_noninferiority_are_separate_gates(self):
        for ttft, wall, decode, expected in [(.94, 1, 1, 'PASS_PERFORMANCE_SCREEN'),
                (.98, 1, 1, 'PERFORMANCE_GATE_NOT_MET'), (.94, 1.03, 1, 'PERFORMANCE_GATE_NOT_MET'),
                (.94, 1, 1.03, 'PERFORMANCE_GATE_NOT_MET')]:
            with self.subTest(ttft=ttft, wall=wall, decode=decode), tempfile.TemporaryDirectory() as d:
                task = Path(d); fixtures(task, ttft, wall, decode)
                self.assertEqual(perf.analyze(task)['status'], expected)

    def test_failed_short_or_changed_identity_cannot_be_dropped_or_substituted(self):
        for fault in ('failed', 'short', 'hash', 'warm', 'missing'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                task = Path(d); fixtures(task); folder = task / '01-100K-C'
                if fault == 'failed':
                    run = json.loads((folder / 'RUN_RESULT.json').read_text()); run['status'] = 'FAIL'
                    (folder / 'RUN_RESULT.json').write_text(json.dumps(run))
                elif fault == 'missing': (folder / 'RESULTS.json').unlink()
                else:
                    data = json.loads((folder / 'RESULTS.json').read_text())
                    if fault == 'short': data[0]['metrics']['generated_tokens'] = 2047
                    elif fault == 'hash': data[0]['request_sha256'] = 'other'
                    else: data[0]['metrics']['reused_tokens'] = 80
                    (folder / 'RESULTS.json').write_text(json.dumps(data))
                with self.assertRaises((RuntimeError, FileNotFoundError)): perf.analyze(task)

    def test_complete_primary_is_preserved_when_support_fails(self):
        with tempfile.TemporaryDirectory() as d:
            task = Path(d); fixtures(task)
            first = task / '12-4K-A/RUN_RESULT.json'
            run = json.loads(first.read_text()); run['status'] = 'FAIL'; first.write_text(json.dumps(run))
            (task / '13-4K-C/RESULTS.json').unlink()
            result = perf.analyze(task)
            self.assertEqual(result['status'], 'INCOMPLETE_OR_INVALID')
            self.assertEqual(result['primary']['ttft_s']['pairs'], 6)
            self.assertEqual([x['identity']['index'] for x in result['invalid_support_samples']], [12, 13])
            self.assertEqual(json.loads(first.read_text())['status'], 'FAIL')

    def test_final_configuration_removes_inherited_timing_and_other_lab_flags(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); original = root / 'original.json'; memcheck = root / 'memcheck'; memcheck.mkdir()
            original.write_text(json.dumps({'args': ['--expert-cache', 'auto'], 'env': {
                'STRATA_PREFILL_TIMING': '0', 'STRATA_DECODE_TIMING': '1', 'STRATA_LAB_HC_COST': '1', 'STRATA_FROZEN': '1'}}))
            c = {'deployed_config': str(original), 'deployed_repo': str(root), 'max_context': 131072,
                 'conversation_cache_mib': 2048, 'port': 18089, 'extra_frozen_env': {'STRATA_LAB_ORACLE_DIR': '/unused'}}
            expected = perf.make_run_config(c, perf.TREE, 'cfg', {}, root)
            (memcheck / 'plan.json').write_text(json.dumps(expected))
            with patch.object(perf.lifecycle, 'TASK', root):
                ready, cfg = perf.configuration(c, root, 'C')
            self.assertNotIn('STRATA_PREFILL_TIMING', cfg['env'])
            self.assertNotIn('STRATA_DECODE_TIMING', cfg['env'])
            self.assertNotIn('STRATA_LAB_HC_COST', cfg['env'])
            self.assertNotIn('STRATA_LAB_ORACLE_DIR', cfg['env'])
            self.assertEqual(cfg['env']['STRATA_LAB_HC_REGION'], '1')
            self.assertIsNone(ready['common']['env']['STRATA_PREFILL_TIMING'])


if __name__ == '__main__': unittest.main()
