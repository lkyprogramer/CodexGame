import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('oracle_replay_analysis', ROOT / 'tools/oracle_replay/analyze.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)

# Small raw fixtures exercise framing/comparison, not real model shapes or CUDA.
ORDER = 'geometry R inj mixed mixed_h mixed_bf mixed_bf_lo_present ids w resident_present compute_geometry dispatch_resident_present on_cpu cpu_selection cnt off order slot src group_geometry GU H_kind Dm shared sg bo'.split()


class OracleReplayAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.phase = Path(self.temp.name)
        self.raw = self.phase / 'replay'
        self.raw.mkdir()
        self.rows = []
        for p in (0, 1):
            for field in ORDER:
                data = struct.pack('<fff', 0.0, 1.0, -2.0) if field in analysis.FLOAT_OUTPUTS else bytes([1, 2, 3, 4])
                self.rows.append(dict(analysis.TARGET, marker='P14_REPLAY', **{'pass': p}, field=field,
                                      bytes=len(data), guard=field not in analysis.FLOAT_OUTPUTS))
                (self.raw / f'pass{p}-{field}.bin').write_bytes(data)
        self.save()
        self.run_result(None, None)
        (self.phase / 'stderr.log').write_text(analysis.COMPLETE + '/remote/phase/replay\n')

    def save(self):
        (self.raw / 'records.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in self.rows))

    def run_result(self, negative, error):
        (self.phase / 'RUN_RESULT.json').write_text(json.dumps({'negative': negative, 'native_error': error}))

    def result(self, negative=None):
        return analysis.analyze(self.phase, negative)

    def test_equal_complete_phase_compares_all_bytes_in_record_order(self):
        # Tiny chunk exercises multiple reads and a short final block.
        with patch.object(analysis, 'CHUNK_BYTES', 8):
            result = self.result()
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual([f['field'] for f in result['fields']], ORDER)
        self.assertEqual(result['total_compared_bytes'], sum(r['bytes'] for r in self.rows if r['pass'] == 0))
        dm = next(f for f in result['fields'] if f['field'] == 'Dm')
        self.assertEqual(dm['finite'], [3, 3])
        self.assertEqual(dm['different_elements'], 0)

    def test_output_and_guard_differences_retain_first_in_record_order(self):
        (self.raw / 'pass1-Dm.bin').write_bytes(struct.pack('<fff', 0.0, 2.0, -2.0))
        (self.raw / 'pass1-mixed.bin').write_bytes(b'\x01\x02\x03\x05')
        result = self.result()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['first_different_field'], 'mixed')
        self.assertEqual(result['guard_differences'], ['mixed'])
        self.assertEqual(result['output_differences'], ['Dm'])
        dm = next(f for f in result['fields'] if f['field'] == 'Dm')
        self.assertEqual(dm['different_elements'], 1)
        self.assertEqual(dm['max_abs_finite'], 1.0)
        self.assertGreater(dm['different_bits'], 0)

    def test_half_outputs_and_nonfinite_values_are_reported(self):
        for p in (0, 1):
            self.rows.append(dict(analysis.TARGET, marker='P14_REPLAY', **{'pass': p}, field='Hh', bytes=4, guard=False))
            (self.raw / f'pass{p}-Hh.bin').write_bytes(struct.pack('<ee', 1.0, float('inf')))
        # All pass0 rows must precede pass1 rows.
        self.rows.sort(key=lambda r: r['pass'])
        self.save()
        result = self.result()
        self.assertEqual(result['status'], 'FAIL')
        h = next(f for f in result['fields'] if f['field'] == 'Hh')
        self.assertEqual(h['inf'], [1, 1])
        self.assertEqual(h['finite'], [1, 1])
        self.assertTrue(h['bitwise_equal'])
        self.assertIn('nonfinite float outputs', result['issues'])

    def test_standard_library_comparator_matches_numpy_result(self):
        a, b = self.raw / 'pass0-Dm.bin', self.raw / 'pass1-Dm.bin'
        b.write_bytes(struct.pack('<fff', -0.0, 2.0, float('nan')))
        expected = analysis.compare_files(a, b, 12, 4)
        with patch.object(analysis, 'np', None), patch.object(analysis, 'CHUNK_BYTES', 8):
            actual = analysis.compare_files(a, b, 12, 4)
        self.assertEqual(expected, actual)

    def test_missing_file_and_wrong_length_fail(self):
        path = self.raw / 'pass1-Dm.bin'
        original = path.read_bytes()
        path.unlink()
        self.assertIn('missing raw file', ' '.join(self.result()['issues']))
        path.write_bytes(original[:-1])
        self.assertIn('raw size mismatch', ' '.join(self.result()['issues']))

    def test_duplicate_wrong_context_and_changed_metadata_fail(self):
        original = list(self.rows)
        self.rows.append(self.rows[-1])
        self.save()
        self.assertIn('duplicate', ' '.join(self.result()['issues']))
        self.rows = [dict(row) for row in original]
        self.rows[0]['T'] = 4096
        self.save()
        self.assertIn('wrong target', ' '.join(self.result()['issues']))
        self.rows = [dict(row) for row in original]
        self.rows[-1]['guard'] = True
        self.save()
        self.assertIn('guard policy', ' '.join(self.result()['issues']))

    def test_missing_pass_field_and_declared_length_fail(self):
        self.rows = [r for r in self.rows if not (r['pass'] == 1 and r['field'] == 'Dm')]
        (self.raw / 'pass1-Dm.bin').unlink()
        self.save()
        self.assertIn('field set/order', ' '.join(self.result()['issues']))
        self.rows[-1]['bytes'] = 8
        (self.raw / 'pass1-bo.bin').write_bytes(b'\0' * 8)
        # Restore Dm to get to the length equality check.
        dm0 = next(r for r in self.rows if r['pass'] == 0 and r['field'] == 'Dm')
        index = next(i for i, r in enumerate(self.rows) if r['pass'] == 1 and r['field'] == 'shared')
        self.rows.insert(index, dict(dm0, **{'pass': 1}))
        (self.raw / 'pass1-Dm.bin').write_bytes((self.raw / 'pass0-Dm.bin').read_bytes())
        self.save()
        self.assertIn('pass length/guard mismatch', ' '.join(self.result()['issues']))

    def test_incomplete_native_error_and_unexpected_outputs_never_pass(self):
        (self.phase / 'stderr.log').write_text('ordinary process exit\n')
        self.assertEqual(self.result()['status'], 'FAIL')
        (self.phase / 'stderr.log').write_text(analysis.COMPLETE + 'x\n')
        self.run_result(None, 'native driver failed')
        self.assertIn('native_error', ' '.join(self.result()['issues']))
        self.run_result(None, None)
        (self.raw / 'pass1-extra.bin').write_bytes(b'')
        self.assertIn('unexpected raw', ' '.join(self.result()['issues']))

    def test_native_error_keeps_failure_and_retains_complete_byte_diagnostics(self):
        self.run_result(None, "FileNotFoundError: /proc/123/exe after native exit0")
        (self.raw / 'pass1-Dm.bin').write_bytes(struct.pack('<fff', 0.0, 2.0, -2.0))
        result = self.result()
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('native_error is not empty', result['issues'])
        self.assertEqual(result['first_different_field'], 'Dm')
        self.assertEqual(result['output_differences'], ['Dm'])
        self.assertEqual(result['total_compared_bytes'], sum(r['bytes'] for r in self.rows if r['pass'] == 0))
        dm = next(f for f in result['fields'] if f['field'] == 'Dm')
        self.assertEqual(dm['different_elements'], 1)
        self.assertEqual(dm['max_abs_finite'], 1.0)

    def negative(self, mode, reason, cutoff, partial=None):
        names = ORDER[:ORDER.index(cutoff)]
        self.rows = [r for r in self.rows if r['pass'] == 0 or r['field'] in names]
        for f in self.raw.glob('pass1-*.bin'):
            if f.name.removeprefix('pass1-').removesuffix('.bin') not in names:
                f.unlink()
        if partial is not None:
            (self.raw / f'pass1-{cutoff}.bin').write_bytes(partial)
        self.save()
        self.run_result(mode, 'native ended before output')
        (self.phase / 'stderr.log').write_text('P14_REPLAY REJECT ' + reason + '\nP14_REPLAY REJECT target not completed (hit=1)\n')

    def test_input_negative_requires_exact_reject_and_changed_partial(self):
        self.negative('input', 'snapshot mismatch: mixed block 0', 'mixed', b'\x02\x02\x03\x04')
        result = self.result('input')
        self.assertEqual(result['status'], 'NEGATIVE_CONTROL_PASS', result)
        self.assertEqual(result['rejection']['affected_field'], 'mixed')
        (self.raw / 'pass1-mixed.bin').write_bytes(b'\x01\x02\x03\x04')
        self.assertEqual(self.result('input')['status'], 'FAIL')

    def test_dispatch_negative_allows_unflushed_zero_partial_with_explicit_limit(self):
        self.negative('dispatch', 'snapshot mismatch: on_cpu block 0', 'on_cpu', b'')
        result = self.result('dispatch')
        self.assertEqual(result['status'], 'NEGATIVE_CONTROL_PASS', result)
        self.assertIn('zero-byte', result['rejection']['limitation'])

    def test_mapping_validity_negative_and_wrong_failure_stage(self):
        self.negative('mapping', 'slot/src expert/token mapping', 'cnt')
        self.assertEqual(self.result('mapping')['status'], 'NEGATIVE_CONTROL_PASS')
        (self.phase / 'stderr.log').write_text('P14_REPLAY REJECT snapshot mismatch: slot block 0\n')
        self.assertIn('affected guard', ' '.join(self.result('mapping')['issues']))

    def test_arbitrary_process_failure_and_wrong_negative_are_not_success(self):
        self.negative('dispatch', 'out of GPU memory', 'dispatch_resident_present')
        self.assertEqual(self.result('dispatch')['status'], 'FAIL')
        (self.phase / 'stderr.log').write_text('P14_REPLAY REJECT invalid replay CPU expert\n')
        self.assertEqual(self.result('dispatch')['status'], 'NEGATIVE_CONTROL_PASS')
        self.assertEqual(self.result('input')['status'], 'FAIL')
        (self.raw / 'pass0-Dm.bin').unlink()
        self.assertEqual(self.result('dispatch')['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
