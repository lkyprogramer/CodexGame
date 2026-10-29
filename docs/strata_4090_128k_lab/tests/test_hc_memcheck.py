from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/hc_scratch'))
import memcheck


class MemcheckTests(unittest.TestCase):
    def test_freeze_original_nominal_budget_only(self):
        source = ROOT / 'workspace/combination/hc-lifecycle-20261029'
        plan = json.loads((source / 'memcheck/plan.json').read_text())
        args, env = memcheck.frozen_plan(plan, (source / 'lifecycle/stderr.log').read_text())
        i = args.index('--expert-cache') + 1
        self.assertEqual(args[i], '7677')
        restored = list(args); restored[i] = 'auto'
        self.assertEqual(restored, plan['args'])
        self.assertEqual(env.pop('CUDA_MODULE_LOADING'), 'LAZY')
        self.assertEqual(env, plan['env'])

    def test_changed_baseline_or_cache_argument_rejected(self):
        for plan, log in [({'args': ['--expert-cache', '1'], 'env': {}}, 'expert cache auto: x -> 7677 slots\nexpert cache 10272 slots,'),
                          ({'args': ['--expert-cache', 'auto'], 'env': {}}, 'expert cache auto: x -> 7676 slots\nexpert cache 10272 slots,')]:
            with self.subTest(plan=plan, log=log), self.assertRaises(RuntimeError):
                memcheck.frozen_plan(plan, log)

    def test_actual_baseline_capture_passes_and_dispatch_drift_fails(self):
        folder = ROOT / 'workspace/combination/hc-boundary-20261029/c-16384'
        log = (ROOT / 'workspace/combination/hc-lifecycle-20261029/lifecycle/long.engine.log').read_text()
        done = {'finish': 'length', 'produced': 1, 'input_tokens': 16389, 'reused': 0, 'read_tokens': 16389}
        expected = memcheck.boundary.records(folder, 'P13_HC_ALLOCATION')
        memcheck.validate_capture(log, done, [1], expected)
        for changed in [log.replace('"stream_all":true', '"stream_all":false'),
                        log.replace('P14_FULL_MTP_RANGE ', 'REMOVED '), log + '\nP15_ORACLE {}']:
            with self.subTest(changed=changed[-100:]), self.assertRaises(RuntimeError):
                memcheck.validate_capture(changed, done, [1], expected)
        with self.assertRaises(RuntimeError):
            memcheck.validate_capture(log, dict(done, reused=1), [1], expected)
        with self.assertRaises(RuntimeError):
            memcheck.validate_capture(log, done, [1], [])

    def test_zero_summary_cannot_hide_incomplete_tool(self):
        memcheck.validate_tool('========= ERROR SUMMARY: 0 errors\n')
        for log in ['ERROR SUMMARY: 1 error', 'no summary', 'Internal Sanitizer Error\nERROR SUMMARY: 0 errors',
                    'Errors might go undetected\nERROR SUMMARY: 0 errors', 'Suppressed 1 errors\nERROR SUMMARY: 0 errors']:
            with self.subTest(log=log), self.assertRaises(RuntimeError): memcheck.validate_tool(log)


if __name__ == '__main__':
    unittest.main()
