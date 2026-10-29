import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hc_make_patch', ROOT / 'tools/hc_scratch/make_patch.py')
hc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hc)
FROZEN = ROOT / 'workspace/combination/dequant-side-20261028/source-evidence/src/prefill/prefill.cpp'


class HcScratchPatchTests(unittest.TestCase):
    def test_probe_changes_allocation_only_not_compute_or_stream_lifetimes(self):
        original = FROZEN.read_text()
        patched = hc.transform(original)
        # Every kernel launch, stream wait, copy, CPU-share choice and MTP batching stays byte-identical.
        first_run = 'bool Prefill::relayout('
        start, end = original.index(first_run), original.index('uint64_t Prefill::bytes_needed(')
        self.assertEqual(original[start:end], patched[patched.index(first_run):patched.index('uint64_t Prefill::bytes_needed(')])
        trailing = 'uint64_t Prefill::bytes_needed_no_ring('
        self.assertEqual(original[original.index(trailing):], patched[patched.index(trailing):])
        self.assertIn("e && e[0] == '1'", hc.FLAGS)
        self.assertIn('!lab_hc_region() || lab_hc_keep_loan()', patched)
        self.assertIn('STRATA_LAB_HC_MANIFEST', patched)

    def test_hc_padding_and_low_components_are_counted_and_carved_together(self):
        patched = hc.transform(FROZEN.read_text())
        self.assertIn('T * (D + (hc_pad() ? XN_PAD : 0))', hc.SIZE)
        self.assertIn('if (bf16x2_hc(f16_io))', hc.SIZE)
        self.assertIn('m.xn16_lo = h.take<uint16_t>(T * D, ok)', patched)
        self.assertIn('m.lo16_lo = h.take<uint16_t>(T * LR, ok)', patched)
        self.assertIn('!lab_hc_region() && bf16x2_hc(m.f16_io)', patched)
        self.assertIn('(!lab_hc_region() || lab_hc_keep_loan()) && bf16x2_hc(f16_io)', patched)
        self.assertIn('if (bf16x2(m.f16_io)) m.mixed_bf_lo = o.take<uint16_t>', patched)
        self.assertIn('m.inj = o.take<float>(T * HC, ok)', patched)

    def test_existing_allocator_padding_and_unrelated_accounting_are_preserved(self):
        original = FROZEN.read_text()
        patched = hc.transform(original)
        alloc_start = original.index('struct Alloc {')
        alloc_end = original.index('\n};', alloc_start) + len('\n};')
        alloc = original[alloc_start:alloc_end]
        self.assertIn(alloc, patched)
        self.assertIn('if (!emb_reuse_account()) f(T * N);', patched)
        self.assertIn('return o.used + (8u << 20);', patched)
        self.assertIn('else {   // STRATA_RING_BYTES=0: 0.1.39\'s count\n        f(T * N); f(T * D); f(T * D);', patched)

    def test_missing_anchor_and_repeat_fail_without_any_write(self):
        with tempfile.TemporaryDirectory() as folder:
            tree = Path(folder) / 'tree'
            path = tree / hc.RELATIVE
            path.parent.mkdir(parents=True)
            path.write_text(FROZEN.read_text().replace(hc.COUNT_OLD, '// changed allocation'))
            before = path.read_bytes()
            patch = Path(folder) / 'probe.patch'
            with self.assertRaisesRegex(ValueError, 'HC_ANCHOR_COUNT'):
                hc.apply(tree, patch)
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(patch.exists())
            path.write_text(FROZEN.read_text())
            hc.apply(tree, patch)
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'HC_ALREADY_PATCHED'):
                hc.apply(tree, Path(folder) / 'second.patch')
            self.assertEqual(path.read_bytes(), before)

    def test_existing_patch_output_prevents_source_write(self):
        with tempfile.TemporaryDirectory() as folder:
            tree = Path(folder) / 'tree'
            path = tree / hc.RELATIVE
            path.parent.mkdir(parents=True)
            path.write_bytes(FROZEN.read_bytes())
            patch = Path(folder) / 'probe.patch'
            patch.write_text('retained evidence\n')
            with self.assertRaisesRegex(ValueError, 'HC_PATCH_OUTPUT_EXISTS'):
                hc.apply(tree, patch)
            self.assertEqual(path.read_bytes(), FROZEN.read_bytes())
            self.assertEqual(patch.read_text(), 'retained evidence\n')


if __name__ == '__main__':
    unittest.main()
