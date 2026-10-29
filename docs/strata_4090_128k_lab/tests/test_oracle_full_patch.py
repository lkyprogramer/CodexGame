import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('full_request_patch_tested', ROOT / 'tools/oracle_replay/full_request_patch.py')
full = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(full)
FROZEN = ROOT / 'workspace/continuation-20261029/source-read/src/prefill/prefill.cpp'


class OracleFullPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = FROZEN.read_text()
        cls.patched = full.transform(cls.original)
        cls.header = full.HEADER.read_text()

    def test_only_original_source_and_no_repatch(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_IDENTITY'):
            full.transform(self.original + '\n')
        with self.assertRaisesRegex(ValueError, 'ALREADY_PATCHED'):
            full.transform(self.patched)
        with self.assertRaisesRegex(ValueError, 'ANCHOR_COUNT'):
            full.once('x x', 'x', 'y')

    def test_every_original_compute_runs_once_and_layer_major_is_untouched(self):
        p = self.patched
        for call in ['route(m.logits, m.ids, m.w, T, m.g->n_expert, m.cs);',
                     'm.mmq_ctx->run(gu, m.cs);', 'm.mmq_ctx->run(dn, m.cs);',
                     'std::future<bool> cpu_fut;', 'StagerDone stager_done{stream_all ? nullptr : m.stager.get()};',
                     'pt.mark(kPfHcWrite, cs);', 'm.stager->start(std::move(js));',
                     'moe_combine(m.Dm, m.slot_dev, m.w, m.shared, m.sg, m.bo, T, m.cs,']:
            self.assertEqual(self.original.count(call), p.count(call), call)
        tail = 'void Prefill::lm_release()'
        self.assertEqual(self.original[self.original.index(tail):], p[p.index(tail):])
        self.assertNotIn('replay_pass', p)
        self.assertNotIn('cudaMemsetAsync(m.Dm,', p)
        self.assertIn('!stream_all && !ps_on && !m.pp', p)
        self.assertIn('!fused_l', p)

    def test_arm_and_dispatch_restored_before_original_consumers(self):
        p = self.patched
        restore = p.index('cpu_arm = saved[0] != 0;')
        self.assertLess(restore, p.index('if (m.cpu_x_n < want)', restore))
        restore = p.index('on_cpu = oracle.load<char>')
        compare = p.index('oracle.vec(oracle_key, "on_cpu", on_cpu);', restore)
        self.assertLess(restore, compare)
        self.assertLess(compare, p.index('cpu_fut = std::async', restore))
        for check in ['!resident && c > 0 && c <= strata::kernels::cpu::MAXT',
                      'm.src->pinned(l, e) || !m.src->transient(l, e)',
                      'const uint8_t* b = m.src->blob_stable(l, e);', 'b != nullptr']:
            self.assertIn(check, p)
        self.assertNotIn('replay.blobs', p)
        self.assertIn('cpu_share_env() != 0.0', p)

    def test_real_routing_group_tables_and_per_group_geometry_are_compared(self):
        p = self.patched
        for field in ['ids', 'w', 'host_res', 'cnt', 'off', 'order', 'slot', 'src', 'bounds',
                      'mmq_geometry', 'native_geometry', 'group_geometry', 'dispatch_path']:
            self.assertIn('"' + field + '"', p)
        compare = p.index('oracle.host(oracle_key, "slot", slot_h')
        self.assertLess(compare, p.index('copy_i32(m.slot_dev, m.grp_dev + m.grp_tk', compare))
        self.assertIn('std::vector<int32_t> members(order.begin() + j0, order.begin() + j + 1);', p)
        self.assertIn('ngx, maxr, r0, nr, direct, wmma_l, T * K', p)
        self.assertIn('e, cslot, gp != nullptr, ns', p)
        self.assertIn('"fp16_expert_"', p)
        # No router values or actual grouping tables are overwritten by the diagnostic.
        for line in p.splitlines():
            if 'oracle.' in line or 'oracle_' in line:
                self.assertNotIn('cudaMemcpyHostToDevice', line)

    def test_hc_reads_only_initialized_regions_and_excludes_row_padding(self):
        p = self.patched
        self.assertIn('p0 == 0 && T == 4090 && l == 3 && half == 1', p)
        self.assertIn('if (!gr_unfused()) oracle_gpu(oracle_key, "hc_grs"', p)
        self.assertIn('else oracle_gpu(oracle_key, "hc_xn"', p)
        self.assertIn('if (!upmixed) oracle_gpu(oracle_key, "hc_gated"', p)
        self.assertIn('"hc_xn16", m.xn16, (size_t) D * 2, (size_t) ldx * 2', p)
        for field in ['hc_entry_R', 'hc_lo', 'hc_lo16', 'hc_inj', 'hc_mixed', 'body_bo', 'body_inj', 'hc_write_R', 'chunk_end_R']:
            self.assertIn('"' + field + '"', p)
        write = p.index('oracle_gpu(oracle_key, "hc_write_R"')
        self.assertLess(p.rindex('strata::kernels::cvec_apply(', 0, write), write)
        self.assertIn('if (oracle_handoff)', p)
        self.assertIn('if (normed) {\n                        oracle_gpu(oracle_key, "cached_grs"', p)
        self.assertIn('if (m.xn16_lo)', p)

    def test_initial_state_uses_effective_carves_and_rejects_nonzero_prefix(self):
        p = self.patched
        self.assertIn('pos0 == 0 && !initial_oracle.initial_seen', p)
        self.assertIn('cudaDeviceSynchronize() == cudaSuccess', p)
        self.assertIn('(size_t) ss.gdn_alloc * gdn_floats * sizeof(float)', p)
        self.assertIn('strata::kernels::NG_HIST * strata::kernels::NG_HC_DIM * sizeof(float)', p)
        self.assertIn('ss.ple_prev[0], ss.ple_prev[1], ss.ple_token', p)
        self.assertIn('ss.gdn_ord0, ss.gdn_alloc, ss.qsa_ord0, ss.qsa_alloc', p)
        self.assertNotIn('sizeof(ss)', p)
        self.assertIn('"initial_kv_prefix_tokens"', p)

    def test_reference_consumption_is_exact_and_mismatch_raw_is_closed_before_rejection(self):
        h = self.header
        self.assertIn('std::memcmp(now.data(), before.data(), n)', h)
        self.assertIn('consumed == expected.size() && chunks == ref_chunks && ffn == ref_ffn', h)
        self.assertIn('e.key == k.str() && e.field == field && e.bytes == bytes', h)
        self.assertIn('expected.size() == n', h)
        self.assertIn('std::fgetc(prior) == EOF', h)
        self.assertLess(h.index('require(std::fclose(out) == 0, "raw close'), h.index('require(mismatch < 0'))
        self.assertLess(h.index('record(k, field, bytes, mismatch);'), h.index('require(mismatch < 0'))
        self.assertIn('!chunk_open && chunks && ffn', h)
        self.assertIn('P15_ORACLE COMPLETE chunks=', h)
        self.assertNotIn('fnv', h.lower())
        self.assertNotIn('SAVE', h)

    def test_mtp_batches_are_observed_without_changing_loop(self):
        p = self.patched
        self.assertIn('P14_FULL_MTP_BATCH', p)
        start = p.index('P14_FULL_MTP_BATCH')
        marker = p[start:p.index('for (int64_t i = 0; i < nb;', start)]
        for field in ['cell0', 'n', 'r0', 'B', 'b0', 'nb', 'c0', 'q8', 'kv_mode', 'n_slots']:
            self.assertIn('\\"' + field + '\\"', marker)
        loop = 'for (int64_t b0 = r0; b0 < n; b0 += B)'
        self.assertEqual(self.original.count(loop), p.count(loop))

    def test_apply_rejects_before_writing_and_leaves_frozen_input_unchanged(self):
        original_bytes = FROZEN.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            tree = Path(folder) / 'tree'
            path = tree / full.RELATIVE
            path.parent.mkdir(parents=True)
            path.write_text(self.original)
            patch = Path(folder) / 'full.patch'
            patch.write_text('retained evidence')
            with self.assertRaisesRegex(ValueError, 'PATCH_OUTPUT_EXISTS'):
                full.apply(tree, patch)
            self.assertEqual(path.read_text(), self.original)
            patch.unlink()
            receipt = full.apply(tree, patch)
            self.assertEqual(receipt['source_sha256'], full.SOURCE_SHA256)
            self.assertEqual(path.read_text(), self.patched)
        self.assertEqual(FROZEN.read_bytes(), original_bytes)


if __name__ == '__main__':
    unittest.main()
