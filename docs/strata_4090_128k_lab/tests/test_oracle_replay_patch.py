import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('oracle_replay_patch', ROOT / 'tools/oracle_replay/make_patch.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
FROZEN = ROOT / 'workspace/continuation-20261029/source-read/src/prefill/prefill.cpp'


class OracleReplayPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = FROZEN.read_text()
        cls.patched = probe.transform(cls.original)

    def test_strict_source_identity_and_repatch_rejection(self):
        with self.assertRaisesRegex(ValueError, 'REPLAY_SOURCE_IDENTITY'):
            probe.transform(self.original + '\n')
        with self.assertRaisesRegex(ValueError, 'REPLAY_ALREADY_PATCHED'):
            probe.transform(self.patched)
        with self.assertRaisesRegex(ValueError, 'REPLAY_ANCHOR_COUNT'):
            probe.replace_once('a a', 'a', 'b')

    def test_scope_replays_only_moe_between_single_hc_read_and_write(self):
        p = self.patched
        self.assertIn('p0 == 0 && T == 4090 && l == 3 && half == 1', p)
        self.assertIn('!stream_all && !m.pp && !ps_on', p)
        start = p.index(probe.MARKER)
        end = p.index('} // P14_REPLAY pass:')
        self.assertNotIn('gr_write(', p[start:end])
        self.assertNotIn('gr_read(', p[start:end])
        for original_call in ['pt.mark(kPfHcWrite, cs);', 'StagerDone stager_done{stream_all ? nullptr : m.stager.get()};',
                              'std::future<bool> cpu_fut;', 'cpu_fut.get()', 'm.stager->start(std::move(js));']:
            self.assertEqual(self.original.count(original_call), p.count(original_call))
        # Original computations remain in order; the replay changes dispatch only.
        cursor = 0
        for line in self.original.splitlines():
            if any(token in line for token in ('mmq::swiglu(', 'm.mmq_ctx->run(', 'm.gemm.f16(', 'moe_combine(m.Dm')):
                cursor = p.index(line, cursor) + len(line)

    def test_cpu_arm_restored_before_activation_allocation_and_rebuild_before_jobs(self):
        p = self.patched
        arm = p.index('cpu_arm = replay.arm;')
        self.assertLess(arm, p.index('if (m.cpu_x_n < want)', arm))
        rebuild = p.index('on_cpu = replay.cpu;')
        guard = p.index('replay.vec(replay_pass, "on_cpu", on_cpu);')
        jobs = p.index('cpu_fut = std::async', rebuild)
        self.assertLess(rebuild, guard)
        self.assertLess(guard, jobs)
        for check in ['!resident && m.cnt', 'strata::kernels::cpu::MAXT', 'b == replay.blobs',
                      'n_stream == replay.streamed', 'lay.blob_bytes(l)']:
            self.assertIn(check, p)

    def test_mapping_guard_precedes_real_upload_and_negative_uses_real_tables(self):
        p = self.patched
        guard = p.index('replay.mapping(ids_h, slot_h, src_h')
        self.assertLess(guard, p.index('copy_i32(m.slot_dev, m.grp_dev + m.grp_tk', guard))
        self.assertLess(p.index('std::swap(slot_h[0], slot_h[1])'), guard)
        self.assertLess(p.index('b ^= 1;'), p.index('replay_gpu("mixed",'))
        self.assertLess(p.index('on_cpu[0] ^= 1;'), p.index('replay.vec(replay_pass, "on_cpu"'))
        header = probe.HEADER.read_text()
        for failure in ['cnt/off coverage', 'row count coverage', 'CPU/GPU overlap', 'slot permutation',
                        'slot/src expert/token mapping', 'GPU order coverage', 'snapshot length mismatch']:
            self.assertIn(failure, header)
        self.assertIn('std::memcmp(now.data(), before.data(), n) == 0', header)
        self.assertIn('std::fgetc(old) == EOF', header)
        self.assertNotIn('fnv', header.lower())

    def test_only_effective_intermediates_and_output_poison(self):
        p = self.patched
        self.assertIn('(T * K - rows_cpu) * 1280 * 4', p)
        self.assertIn('if (replay_h_kind == 1) replay_gpu("H"', p)
        self.assertIn('if (replay_h_kind == 2) replay_gpu("Hh"', p)
        self.assertIn('replay_h_kind = 0; // swiglu_quant initializes Hq, not H', p)
        self.assertIn('replay_pass ? 0x5a : 0xa5', p)
        for field in ['R', 'inj', 'mixed', 'mixed_h', 'mixed_bf', 'mixed_bf_lo', 'ids', 'w', 'Dm', 'shared', 'sg', 'bo']:
            self.assertIn('replay_gpu("' + field + '"', p)
        self.assertIn('"cpu_rows", m.cpu_rows', p)
        self.assertIn('"bounds", m.bounds_host', p)
        self.assertIn('final_logits_oracle=0', p)

    def test_apply_preserves_existing_outputs_and_rejects_before_source_write(self):
        with tempfile.TemporaryDirectory() as folder:
            tree = Path(folder) / 'tree'
            path = tree / probe.RELATIVE
            path.parent.mkdir(parents=True)
            path.write_text(self.original)
            patch = Path(folder) / 'replay.patch'
            patch.write_text('existing evidence')
            with self.assertRaisesRegex(ValueError, 'REPLAY_PATCH_OUTPUT_EXISTS'):
                probe.apply(tree, patch)
            self.assertEqual(path.read_text(), self.original)
            patch.unlink()
            receipt = probe.apply(tree, patch)
            self.assertEqual(receipt['source_sha256'], probe.SOURCE_SHA256)
            self.assertEqual(path.read_text(), self.patched)
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'REPLAY_ALREADY_PATCHED'):
                probe.apply(tree, Path(folder) / 'repeat.patch')
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
