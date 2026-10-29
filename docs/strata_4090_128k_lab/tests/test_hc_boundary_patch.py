import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
sys.path[:0] = [str(TOOLS / 'hc_scratch'), str(TOOLS / 'oracle_replay')]
import boundary_patch
import full_request_patch
import boundary


class BoundaryPatchTests(unittest.TestCase):
    def test_wrong_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'BOUNDARY_SOURCE_DRIFT'):
            boundary_patch.transform('unknown source')

    def test_streamed_patch_keeps_computation_and_strict_oracle(self):
        path = ROOT / 'workspace/combination/hc-scratch-20261028/source-evidence/prefill-hc-only.cpp'
        source = path.read_text()
        changed = boundary_patch.transform(source)
        self.assertIn('"stream_execution"', changed)
        self.assertIn('"stream_host_res"', changed)
        self.assertIn('"fused_slot"', changed)
        self.assertIn('"fused_src"', changed)
        self.assertIn('private HC control VRAM headroom', changed)
        self.assertIn('m.T == T && !m.f16_io', changed)
        self.assertIn('!ps_on && !m.pp, "peer FFN unsupported "', changed)
        # All expert kernels and their inputs remain verbatim.
        for line in source.splitlines():
            if 'fused::experts' in line or 'fused::group(' in line or 'fused::quantize_act' in line:
                self.assertIn(line, changed)
        self.assertNotIn('T == 4090', changed)

    def test_missing_ffn_coverage_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); (folder / 'oracle').mkdir()
            (folder / 'oracle/COMPLETE.json').write_text(json.dumps({'chunks': 1, 'ffn': 47, 'records': 0}))
            with self.assertRaisesRegex(RuntimeError, 'CHUNK_FFN_COVERAGE'):
                boundary.validate(folder, 4096)

    def test_wrong_computed_geometry_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); oracle = folder / 'oracle'; oracle.mkdir()
            (oracle / 'COMPLETE.json').write_text(json.dumps({'chunks': 1, 'ffn': 48, 'records': 1}))
            row = {'p0': 0, 'T': 4096, 'layer': -1, 'half': -1, 'field': 'chunk_begin', 'bytes': 80, 'first_mismatch_byte': -1}
            (oracle / 'records.jsonl').write_text(json.dumps(row) + '\n')
            (oracle / 'p0-T4096-l-1-h-1-chunk_begin.bin').write_bytes(struct.pack('<10q', 0, 4095, 2560, 10240, 4, 320, 10, 512, 0, 48))
            with self.assertRaisesRegex(RuntimeError, 'COMPUTED_CHUNK_GEOMETRY'):
                boundary.validate(folder, 4096)

    def test_missing_records_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); oracle = folder / 'oracle'; oracle.mkdir()
            (oracle / 'COMPLETE.json').write_text(json.dumps({'chunks': 1, 'ffn': 48, 'records': 1}))
            (oracle / 'records.jsonl').write_text('')
            with self.assertRaisesRegex(RuntimeError, 'RAW_COVERAGE_OR_MISMATCH'):
                boundary.validate(folder, 4096)

    def test_failed_previous_producer_blocks_gpu_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp); (task / 'c-4096').mkdir()
            (task / 'PREREGISTRATION.json').write_text(json.dumps({'phases': ['c-4096', 'control-4096', 'c-16384', 'control-16384']}))
            (task / 'c-4096/RUN_RESULT.json').write_text(json.dumps({'status': 'FAIL'}))
            with patch.object(boundary, 'TASK', task), self.assertRaisesRegex(RuntimeError, 'EARLIER_FAILURE_STOP'):
                boundary.run('control-4096')


if __name__ == '__main__':
    unittest.main()
