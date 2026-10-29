import importlib.util
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / 'tools/v027/analyze_dequant.py'
spec = importlib.util.spec_from_file_location('dequant_analysis_tested', PATH)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class DequantAnalysisTests(unittest.TestCase):
    def test_union_does_not_double_count_concurrent_or_adjacent_intervals(self):
        intervals = [(1, 5), (3, 8), (8, 10), (12, 14), (13, 13)]
        self.assertEqual(analysis.merge_intervals(intervals), [[1, 10], [12, 14]])
        self.assertEqual(analysis.interval_length(intervals), 11)
        with self.assertRaisesRegex(ValueError, 'NEGATIVE'):
            analysis.merge_intervals([(3, 2)])

    def test_intersection_deduplicates_each_side(self):
        self.assertEqual(analysis.intersection_length([(0, 10), (5, 15)], [(2, 8), (6, 12)]), 10)
        self.assertEqual(analysis.intersection_length([(0, 2)], [(2, 4)]), 0)

    def test_launch_window_uses_api_start_and_is_duration_limited(self):
        self.assertEqual(analysis.optimistic_launch_window(100, 120, 90), 10)
        self.assertEqual(analysis.optimistic_launch_window(100, 120, 50), 20)
        self.assertEqual(analysis.optimistic_launch_window(100, 120, 110), 0)
        # API can return after the GPU started. Its end must not replace start.
        api = {'start': 90, 'end': 110}
        self.assertEqual(analysis.optimistic_launch_window(100, 120, api['start']), 10)

    def kernel(self, start, end, correlation, name='dequant_kernel<H16>'):
        return {'start': start, 'end': end, 'correlationId': correlation, 'name': name,
                'deviceId': 0, 'contextId': 1, 'streamId': 7, 'gridX': 200, 'gridY': 1, 'gridZ': 1}

    def test_overlap_union_and_missing_runtime_are_not_no_hit(self):
        kernels = [self.kernel(10, 30, 1), self.kernel(20, 40, 2),
                   self.kernel(15, 25, 3, 'gemm')]
        copies = [{'start': 20, 'end': 35}]
        result = analysis.window_metrics(kernels, copies, 0, 50, {})
        self.assertEqual(result['candidate_cumulative_ns'], 40)
        self.assertEqual(result['candidate_union_ns'], 30)
        self.assertEqual(result['overlap_other_kernel_ns'], 10)
        self.assertEqual(result['overlap_memcpy_ns'], 15)
        self.assertEqual(result['overlap_other_kernel_or_memcpy_ns'], 20)
        self.assertEqual(result['state'], 'UNATTRIBUTED')
        self.assertIsNone(result['candidate_api_start_window_sum_ns'])

    def test_ambiguous_runtime_correlation_is_rejected(self):
        launch = {'start': 0, 'end': 1, 'returnValue': 0, 'name': 'cudaLaunchKernel'}
        result = analysis.window_metrics([self.kernel(10, 30, 1)], [], 0, 50, {1: [launch, launch]})
        self.assertEqual(result['runtime_match_failures'], {'ambiguous': 1})
        self.assertEqual(result['state'], 'UNATTRIBUTED')

    def fixture(self, path, missing_kernel=False, wrong_owner_api=False):
        gp = 123 * (1 << 24)
        with closing(sqlite3.connect(path)) as db:
            db.executescript('''
                CREATE TABLE StringIds(id INTEGER, value TEXT);
                CREATE TABLE PROCESSES(globalPid INTEGER,pid INTEGER,name TEXT);
                CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(start INTEGER,end INTEGER,deviceId INTEGER,
                  contextId INTEGER,streamId INTEGER,correlationId INTEGER,globalPid INTEGER,
                  demangledName INTEGER,gridX INTEGER,gridY INTEGER,gridZ INTEGER);
                CREATE TABLE CUPTI_ACTIVITY_KIND_RUNTIME(start INTEGER,end INTEGER,globalTid INTEGER,
                  correlationId INTEGER,nameId INTEGER,returnValue INTEGER);
                CREATE TABLE NVTX_EVENTS(start INTEGER,end INTEGER,text TEXT,textId INTEGER);
                CREATE TABLE META_DATA_EXPORT(name TEXT,value TEXT);
            ''')
            db.executemany('INSERT INTO StringIds VALUES (?,?)', [(1, 'dequant_kernel<H16>'), (2, 'cudaLaunchKernel_v7000')])
            db.execute('INSERT INTO PROCESSES VALUES (?,?,?)', (gp, 55, 'strata'))
            if not missing_kernel:
                db.execute('INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES (10,30,0,1,7,42,?,1,200,1,1)', (gp,))
            db.execute('INSERT INTO CUPTI_ACTIVITY_KIND_RUNTIME VALUES (5,7,?,42,2,0)',
                       (gp + (1 << 24) + 1 if wrong_owner_api else gp + 55,))
            db.executemany('INSERT INTO NVTX_EVENTS VALUES (?,?,?,NULL)',
                           [(0, 100, 'P10_REQUEST/example'), (50, None, 'P10_FIRST/example')])
            db.commit()
        return gp

    def test_missing_trace_and_empty_kernel_export_are_not_no_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'missing.sqlite'
            self.assertEqual(analysis.analyze_trace(path)['state'], 'NO_TRACE')
            self.assertFalse(path.exists())
            self.fixture(path, missing_kernel=True)
            result = analysis.analyze_trace(path)
            self.assertEqual(result['state'], 'NO_TRACE')
            self.assertEqual(result['error'], 'KERNEL_TRACE_EMPTY')

    def test_process_record_and_runtime_thread_ownership_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'trace.sqlite'
            gp = self.fixture(path)
            result = analysis.analyze_trace(path, expected_pid=55)
            self.assertEqual(result['state'], 'OBSERVED')
            self.assertEqual(result['engine_process']['globalPid'], gp)
            self.assertEqual(result['requests'][0]['ttft']['candidate_union_ns'], 20)
            self.assertEqual(result['requests'][0]['ttft']['candidate_api_start_window_sum_ns'], 5)
            self.assertEqual(analysis.analyze_trace(path, expected_pid=56)['state'], 'UNATTRIBUTED')
            wrong = Path(tmp) / 'wrong.sqlite'
            self.fixture(wrong, wrong_owner_api=True)
            self.assertEqual(analysis.analyze_trace(wrong, expected_pid=55)['requests'][0]['ttft']['state'], 'UNATTRIBUTED')

    def test_actual_list_shaped_engine_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'engine-argv.json').write_text(json.dumps([
                {'pid': 1, 'exe': '/usr/bin/python'}, {'pid': 55, 'exe': '/lab/strata', 'args': ['--serve']}]))
            self.assertEqual(analysis.expected_pid_from_folder(folder), 55)
            (folder / 'engine-argv.json').write_text(json.dumps([
                {'pid': 55, 'exe': '/a/strata'}, {'pid': 56, 'exe': '/b/strata'}]))
            with self.assertRaisesRegex(ValueError, 'NOT_UNIQUE'):
                analysis.expected_pid_from_folder(folder)


if __name__ == '__main__':
    unittest.main()
