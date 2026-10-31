import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.frontier.p01b_analysis import summarize_capture


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.window = dict(window_id=0, begin_ns=10, verified_ns=20, commit_enter_ns=21,
                           commit_return_ns=30, draft_return_ns=90, end_ns=100,
                           context_tokens=103183, T=2, kept=1, emitted=1, first=False,
                           merged=False, clean_serial_gap=True, pending=0, astate=0,
                           async_job=False, job_idle=True, adapt_spawned=False)
        self.trace = dict(schema_version=1, request_index=0, clock_domain='steady_clock',
                          start_ns=1, end_ns=1000, total_windows=1, window_limit=2048,
                          overflow=False, token_ids=[42], windows=[self.window])
        self.rows = [dict(request_id='prime', execution_status='COMPLETED', completion_tokens=1,
                          start_monotonic_ns=0, end_monotonic_ns=1001)]

    def run_trace(self, trace=None, rows=None):
        (self.out/'native-trace.0.json').write_text(json.dumps(trace or self.trace))
        return summarize_capture(self.out, {}, rows or self.rows)

    def test_partial_observation_is_never_candidate_or_performance_pass(self):
        result = self.run_trace()
        self.assertEqual(result['QUALIFICATION']['status'], 'INSUFFICIENT')
        self.assertEqual(len(result['DEPENDENCIES']['edges']), 1)
        self.assertFalse(result['QUALIFICATION']['new_candidate_qualified'])
        self.assertEqual(result['ANALYSIS']['request_observations'][0]['native_token_count'], 1)

    def test_bad_native_clock_or_envelope_rejected(self):
        for field, value in [('clock_domain', 'GPU'), ('start_ns', -1), ('end_ns', 2000)]:
            trace = copy.deepcopy(self.trace); trace[field] = value
            with self.assertRaises(ValueError): self.run_trace(trace)

    def test_missing_windows_ids_or_overflow_rejected(self):
        for field, value in [('total_windows', 2), ('token_ids', [42, 43]), ('overflow', True)]:
            trace = copy.deepcopy(self.trace); trace[field] = value
            with self.assertRaises(ValueError): self.run_trace(trace)

    def test_asynchronous_work_cannot_be_counted_clean(self):
        for field, value in [('adapt_spawned', True), ('pending', 1), ('first', True), ('T', 1)]:
            trace = copy.deepcopy(self.trace); trace['windows'][0][field] = value
            with self.assertRaises(ValueError): self.run_trace(trace)
        trace = copy.deepcopy(self.trace); trace['windows'][0].update(clean_serial_gap=False, pending=1)
        self.assertEqual(self.run_trace(trace)['DEPENDENCIES']['edges'], [])

    def test_overlapping_or_unfinished_window_rejected(self):
        trace = copy.deepcopy(self.trace); trace['windows'][0]['verified_ns'] = 0
        with self.assertRaises(ValueError): self.run_trace(trace)
        trace['windows'][0]['verified_ns'] = 50
        with self.assertRaises(ValueError): self.run_trace(trace)


if __name__ == '__main__': unittest.main()
