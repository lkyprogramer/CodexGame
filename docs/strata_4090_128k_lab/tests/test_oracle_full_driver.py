"""CPU-only regressions for the full-request gate; no driver imports or GPU use."""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import struct
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SPEC = importlib.util.spec_from_file_location('full_driver_byte_analysis', ROOT / 'tools/oracle_replay/analyze.py')
byte_analysis = importlib.util.module_from_spec(ANALYSIS_SPEC)
ANALYSIS_SPEC.loader.exec_module(byte_analysis)
SOURCE = ROOT / 'tools/oracle_replay/full_request.py'


def dump(path, value):
    path.write_text(json.dumps(value))


def driver(task, state_compare):
    source = ast.parse(SOURCE.read_text())
    names = {'log_records', 'validate_capture', 'analyze_pair'}
    selected = ast.Module(body=[node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in names],
                          type_ignores=[])
    namespace = {'TASK': task, 'json': json, 'struct': struct, 'Path': Path, 'dump': dump,
                 'local_analysis': byte_analysis, 'compare_session': SimpleNamespace(compare=state_compare)}
    exec(compile(selected, str(SOURCE), 'exec'), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in names})


def sparse(path, size):
    with path.open('wb') as out:
        out.truncate(size)


def logs(folder):
    events = [
        ('P14_FULL_STATE_META', {'live_tokens': 4095, 'ple_prev': [2, 3], 'ple_token': 3,
                                 'gdn_ord0': 0, 'gdn_alloc': 36, 'qsa_ord0': 0, 'qsa_alloc': 12,
                                 'mtp_first_needed': 0, 'mtp_window': 4, 'mtp_mode': 2}),
        ('P14_FULL_REQUEST', {'input_tokens': 4095, 'max_new': 1, 'use_mtp': True}),
        ('P14_FULL_DRAFT_CALL', {'called': False, 'produced': 1, 'max_new': 1, 'T': 1}),
        ('P14_FULL_MTP_RANGE', {'stage': 'chunk', 'batched': True, 'requested_start': 0,
                               'requested_rows': 4090, 'start': 0, 'end': 4090, 'first_needed': 0, 'kv_mode': 2}),
        ('P14_FULL_MTP_BATCH', {'cell0': 0, 'n': 4090, 'r0': 0, 'B': 512,
                               'b0': 0, 'nb': 512, 'c0': 0, 'q8': 1, 'kv_mode': 2}),
    ]
    (folder / 'stderr.log').write_text(''.join(marker + ' ' + json.dumps(value) + '\n' for marker, value in events))


def pair_phase(folder):
    (folder / 'oracle').mkdir(parents=True)
    dump(folder / 'RUN_RESULT.json', {'status': 'CAPTURE_VALID'})
    dump(folder / 'MTP_RANGES.json', {'ranges': [[0, 4090]]})
    (folder / 'oracle/p0-T4090-l3-h1-body_bo.bin').write_bytes(struct.pack('<2f', 1, 2))
    (folder / 'oracle/p0-T4090-l3-h1-on_cpu.bin').write_bytes(b'\x00\x01')
    (folder / 'oracle/p0-T4090-l3-h1-host_res.bin').write_bytes(struct.pack('<2i', 1, 2))
    sparse(folder / 'think-4096.f32', 248320 * 4)
    (folder / 'session.bin').write_bytes(b'identical-state-parser-input')
    logs(folder)


def capture_phase(folder):
    """Sparse raw arrays satisfy full target shapes without allocating GPU-size RAM."""
    raw = folder / 'oracle'
    raw.mkdir(parents=True)
    target = 'p0-T4090-l3-h1-'
    shapes = {'hc_entry_R': 4090 * 10240 * 4, 'hc_write_R': 4090 * 10240 * 4,
              'body_bo': 4090 * 2560 * 4, 'body_inj': 4090 * 4 * 4,
              'hc_grs': 4090 * 4 * 4, 'hc_xn16': 4090 * 10240 * 2,
              'hc_lo': 4090 * 320 * 4, 'hc_lo16': 4090 * 320 * 2,
              'hc_gated': 4090 * 10240 * 4, 'hc_mixed': 4090 * 2560 * 4,
              'hc_mixed_h': 4090 * 2560 * 2, 'hc_mixed_bf': 4090 * 2560 * 2,
              'hc_inj': 4090 * 4 * 4}
    for name, size in shapes.items():
        sparse(raw / (target + name + '.bin'), size)
    (raw / (target + 'hc_path.bin')).write_bytes(struct.pack('<10q', 0, 0, 10240, 0, 0, 0, 0, 0, 0, 0))
    (raw / 'p0-T4090-l4-h0-normed_handoff.bin').write_bytes(struct.pack('<5q', 0, 10240, 0, 0, 0))
    (raw / 'p0-T4090-l-1-h-1-chunk_begin.bin').write_bytes(
        struct.pack('<10q', 0, 4090, 2560, 10240, 4, 320, 10, 512, 0, 48))
    sparse(raw / 'p0-T4090-l-1-h-1-chunk_end_R.bin', 4090 * 10240 * 4)
    initial = 'p0-T4090-l-2-h-1-'
    (raw / (initial + 'initial_geometry.bin')).write_bytes(
        struct.pack('<10q', 0, 4090, 0, 36, 0, 12, 817152, 1, 9, 10240))
    sparse(raw / (initial + 'initial_gdn_state.bin'), 36 * 817152 * 4)
    sparse(raw / (initial + 'initial_ple_hist.bin'), 9 * 10240 * 4)
    (raw / (initial + 'initial_ple_tokens.bin')).write_bytes(struct.pack('<3i', -1, -1, 0))
    (raw / (initial + 'initial_kv_prefix_tokens.bin')).write_bytes(struct.pack('<q', 0))
    for layer in range(48):
        (raw / f'p0-T4090-l{layer}-h1-mmq_geometry.bin').write_bytes(struct.pack('<q', 1))
    write_manifest(raw)
    dump(folder / 'SAVED.json', {'live_tokens': 4095})
    sparse(folder / 'think-4096.f32', 248320 * 4)
    logs(folder)


def write_manifest(raw):
    records = []
    for file in sorted(raw.glob('*.bin')):
        p0, tokens, layer, half, field = re.fullmatch(r'p(-?\d+)-T(\d+)-l(-?\d+)-h(-?\d+)-(.+)\.bin', file.name).groups()
        records.append({'p0': int(p0), 'T': int(tokens), 'layer': int(layer), 'half': int(half),
                        'field': field, 'bytes': file.stat().st_size, 'reference': False, 'first_mismatch_byte': -1})
    (raw / 'records.jsonl').write_text(''.join(json.dumps(record) + '\n' for record in records))
    dump(raw / 'COMPLETE.json', {'marker': 'P15_ORACLE_COMPLETE', 'chunks': 1, 'ffn': 48, 'records': len(records)})


class FullDriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.task = Path(self.temp.name)
        self.state_calls = []

        def state_compare(left, right, **kwargs):
            self.state_calls.append((left, right, kwargs))
            return {'status': 'PASS' if left.read_bytes() == right.read_bytes() else 'FAIL'}
        self.driver = driver(self.task, state_compare)

    def analyze(self, name):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.driver.analyze_pair(name)

    def test_natural_c_dispatch_coverage_and_mapping_changes_are_recorded_with_equal_numerics(self):
        left, right = self.task / 'capture-a', self.task / 'natural-c'
        pair_phase(left)
        pair_phase(right)
        (right / 'oracle/p0-T4090-l3-h1-on_cpu.bin').unlink()
        (right / 'oracle/p0-T4090-l3-h1-host_res.bin').write_bytes(struct.pack('<2i', 2, 1))
        result = self.analyze('natural-c')
        self.assertEqual(result['status'], 'PASS', result['issues'])
        self.assertTrue(result['execution_changes'])
        self.assertTrue(any('field coverage differs:' in value for value in result['execution_changes']))
        self.assertTrue(any('dispatch/geometry differs:' in value for value in result['execution_changes']))
        self.assertEqual(result['numerical_raw_differences'], [])
        self.assertTrue(result['logits']['bitwise_equal'])
        self.assertEqual(result['state']['status'], 'PASS')
        self.assertEqual(len(self.state_calls), 1)
        self.assertEqual(self.state_calls[0][2], {'draft_ranges': [[0, 4090]]})

    def test_natural_c_numeric_difference_still_compares_logits_and_saved_state(self):
        pair_phase(self.task / 'capture-a')
        pair_phase(self.task / 'natural-c')
        name = 'p0-T4090-l3-h1-body_bo.bin'
        (self.task / 'natural-c/oracle' / name).write_bytes(struct.pack('<2f', 1, 3))
        result = self.analyze('natural-c')
        self.assertEqual(result['status'], 'NATURAL_C_NUMERICAL_DIFFERENCE')
        self.assertEqual(result['numerical_raw_differences'], [name])
        self.assertTrue(result['logits']['bitwise_equal'])
        self.assertEqual(result['state']['status'], 'PASS')
        self.assertEqual(len(self.state_calls), 1)

    def test_missing_required_hc_intermediate_cannot_be_a_valid_capture(self):
        folder = self.task / 'capture-a'
        capture_phase(folder)
        self.driver.validate_capture(folder)
        (folder / 'oracle/p0-T4090-l3-h1-hc_mixed.bin').unlink()
        write_manifest(folder / 'oracle')  # deletion is self-consistent; the HC contract must still reject it
        with self.assertRaises(RuntimeError):
            self.driver.validate_capture(folder)

    def test_missing_hc_path_and_wrong_actual_chunk_are_rejected(self):
        folder = self.task / 'capture-a'
        capture_phase(folder)
        path = folder / 'oracle/p0-T4090-l3-h1-hc_path.bin'
        saved_path = path.read_bytes()
        path.unlink()
        write_manifest(folder / 'oracle')
        with self.assertRaises(RuntimeError):
            self.driver.validate_capture(folder)
        path.write_bytes(saved_path)
        write_manifest(folder / 'oracle')
        (folder / 'oracle/p0-T4090-l-1-h-1-chunk_begin.bin').write_bytes(
            struct.pack('<10q', 0, 4096, 2560, 10240, 4, 320, 10, 512, 0, 48))
        with self.assertRaisesRegex(RuntimeError, 'ACTUAL_CHUNK_GEOMETRY'):
            self.driver.validate_capture(folder)

    def test_private_control_requires_actual_separate_allocations(self):
        folder = self.task / 'replay-control'
        capture_phase(folder)
        with self.assertRaisesRegex(RuntimeError, 'PRIVATE_HC_CONTROL_NOT_EXECUTED'):
            self.driver.validate_capture(folder)
        with (folder / 'stderr.log').open('a') as out:
            out.write('P18_PRIVATE_HC ' + json.dumps({'T': 4090, 'bytes': 259523584,
                'separate_allocations': 4, 'loan_unchanged': True}) + '\n')
        self.driver.validate_capture(folder)

    def test_private_control_compares_c_and_keeps_dispatch_strict(self):
        pair_phase(self.task / 'natural-c')
        pair_phase(self.task / 'replay-control')
        self.assertEqual(self.analyze('replay-control')['status'], 'PASS')
        (self.task / 'replay-control/oracle/p0-T4090-l3-h1-on_cpu.bin').write_bytes(b'\x01\x00')
        result = self.analyze('replay-control')
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['raw_differences'], ['p0-T4090-l3-h1-on_cpu.bin'])


if __name__ == '__main__':
    unittest.main()
