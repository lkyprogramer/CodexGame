import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('hc_cost_patch_tested', ROOT / 'tools/hc_scratch/cost_patch.py')
cost = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cost)
FROZEN = ROOT / 'workspace/combination/hc-memcheck-20261029/source-evidence'


class HcCostPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = {name: (FROZEN / name).read_text() for name in cost.SOURCE_SHA256}
        cls.patched = cost.transform(cls.original)

    def test_source_drift_and_repatch_fail_before_writes(self):
        bad = dict(self.original)
        bad['src/program/generate.cpp'] += '\n'
        with self.assertRaisesRegex(ValueError, 'COST_SOURCE_IDENTITY'):
            cost.transform(bad)
        with self.assertRaisesRegex(ValueError, 'COST_ALREADY_PATCHED'):
            cost.transform(self.patched)
        with tempfile.TemporaryDirectory() as d:
            tree = Path(d) / 'tree'
            for name, text in bad.items():
                path = tree / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            output = Path(d) / 'cost.patch'
            with self.assertRaisesRegex(ValueError, 'COST_SOURCE_IDENTITY'):
                cost.apply(tree, output)
            self.assertFalse(output.exists())
            self.assertEqual((tree / 'src/prefill/prefill.cpp').read_text(), self.original['src/prefill/prefill.cpp'])

    def test_stripping_instrumentation_restores_every_original_byte(self):
        for name in self.original:
            self.assertEqual(cost.strip_cost(self.patched[name]), self.original[name], name)
        self.assertIn('std::strcmp(e, "1") == 0', cost.HELPERS)
        self.assertNotIn('cuda', cost.HELPERS)

    def test_all_gpu_operations_and_original_compute_order_are_preserved(self):
        for name in self.original:
            # Every CUDA operation, including events, waits and transfers, remains
            # text-identical and in the original order. No new GPU work is allowed.
            calls = lambda text: re.findall(r'\bcuda\w+\s*\([^;]*?;', text, flags=re.S)
            self.assertEqual(calls(self.original[name]), calls(self.patched[name]), name)
            for line in self.original[name].splitlines():
                if any(t in line for t in ('m.mmq_ctx->run(', 'fused::experts', 'moe_combine(', 'cpu_fut = std::async')):
                    self.assertEqual(self.original[name].count(line), self.patched[name].count(line))

    def test_h2d_counters_have_one_writer_and_are_read_after_original_join(self):
        p = self.patched['src/prefill/prefill.cpp']
        thread = p[p.index('issuer = std::thread([&]'):p.index('} else if (stream_all) {\n            issue_until')]
        self.assertIn('cost_issuer_bytes += bytes;', thread)
        self.assertNotIn('cost_inline_bytes +=', thread)
        self.assertNotIn('cost_staged_bytes +=', thread)
        self.assertNotIn('P23_H2D', thread)
        for block in cost.blocks(p):
            if 'cost_issuer_bytes +=' in block:
                self.assertIn(block, thread)
        output = p.index('P23_H2D')
        self.assertLess(p.index('issuer.join();'), output)
        self.assertIn('cost_inline_count', p)
        self.assertIn('cost_staged_count', p)
        # Two paths per writer: pinned blob and host-stager blob.
        self.assertEqual(p.count('cost_inline_bytes += bytes;'), 2)
        self.assertEqual(p.count('cost_issuer_bytes += bytes;'), 2)
        self.assertEqual(p.count('cost_staged_bytes += (uint64_t) lay.blob_bytes(l);'), 2)

    def test_actual_paths_and_only_fresh_ordinary_route_counts_are_logged(self):
        p = self.patched['src/prefill/prefill.cpp']
        for field in ('p0', 'T', 'layer', 'use_mmq', 'fused_l', 'fused_nat', 'native', 'gu_type', 'd_type',
                      'blob_bytes', 'host_res', 'cnt', 'on_cpu', 'route_counts_available'):
            self.assertIn('\\"' + field + '\\"', p)
        fused = next(b for b in cost.blocks(p) if 'P23_LAYER' in b and 'false' in b)
        self.assertNotIn('m.cnt', fused)
        self.assertNotIn('experts_resident', fused)
        ordinary = next(b for b in cost.blocks(p) if 'P23_LAYER' in b and 'm.cnt' in b)
        self.assertLess(p.index('std::fill(m.cnt.begin(), m.cnt.end(), 0);'), p.index(ordinary))
        self.assertIn('lab_hc_cost_cpu(on_cpu, m.g->n_expert)', ordinary)
        self.assertIn('cpu.empty() ? "0"', cost.HELPERS)
        self.assertIn('m.g->n_expert', ordinary)

    def test_slots_loans_refill_parts_and_completion_fields_exist(self):
        g = self.patched['src/program/generate.cpp']
        for marker in ('P23_CACHE', 'P23_LOAN', 'P23_REFILL_ISSUE', 'P23_REFILL_SYNC', 'P23_REFILL_DONE'):
            self.assertIn(marker, g)
        self.assertIn('cache.slot_offset(s)', g)
        self.assertIn('cache.slot_offsets() != nullptr', g)
        self.assertIn('host_res.data(), host_res.size()', g)
        self.assertIn('p.lent', g)
        self.assertIn('parts[z].n', g)
        self.assertIn('cost_refill_bytes += (uint64_t) nb;', g)
        p = self.patched['src/prefill/prefill.cpp']
        for marker in ('P23_CHUNK', 'P23_H2D', 'P23_TIMING', 'P23_PREFILL_COMPLETE'):
            self.assertIn(marker, p)
        # Read/fold at the original timer boundary; do not add another fold.
        self.assertEqual(p.count('pt.fold();'), self.original['src/prefill/prefill.cpp'].count('pt.fold();'))
        timing = p.index('P23_TIMING')
        self.assertLess(p.rindex('pt.fold();', 0, timing), timing)
        self.assertIn('pt.ms[kPfWaitCopy]', p)
        complete = p.index('P23_PREFILL_COMPLETE')
        self.assertLess(p.index('if (const cudaError_t cst = cudaStreamSynchronize(m.copy);'), complete)

    def test_apply_creates_both_files_once_and_retains_existing_patch(self):
        with tempfile.TemporaryDirectory() as d:
            tree = Path(d) / 'tree'
            for name, text in self.original.items():
                p = tree / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            output = Path(d) / 'cost.patch'
            receipt = cost.apply(tree, output)
            self.assertEqual(set(receipt['files']), set(self.original))
            for name in self.original:
                self.assertEqual((tree / name).read_text(), self.patched[name])
            retained = output.read_bytes()
            with self.assertRaisesRegex(ValueError, 'COST_PATCH_OUTPUT_EXISTS'):
                cost.apply(tree, output)
            self.assertEqual(output.read_bytes(), retained)


if __name__ == '__main__':
    unittest.main()
