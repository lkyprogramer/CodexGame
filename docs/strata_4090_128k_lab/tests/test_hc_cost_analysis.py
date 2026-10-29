from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/hc_scratch'))
import cost_analysis as analysis


def fixture(first, wait_ms):
    slots, target = 10272, 17055 * 1048576
    base = target // slots // 256 * 256
    extra = (target - base * slots) // 256
    full, tail = divmod(extra, 512)
    sizes = [base + (256 if layer < full else 0) for layer in range(48)]
    sizes[20] += tail // 32 * 256
    offsets = [0]
    for slot in range(slots): offsets.append(offsets[-1] + sizes[slot // 512])
    assert offsets[-1] == target
    original = [i if i < slots else -1 for i in range(48 * 512)]
    cache = {'mode': 'serve', 'slots': slots, 'full_slots': slots, 'cache_bytes': target,
             'variable_offsets': True, 'n_expert': 512, 'slot_offsets': offsets, 'host_res': original}
    rows = [('P23_LOAN', {'mode': 'serve', 'dev': -1, 'tokens': 102395, 'exact': -1, 'chunk': 16384,
             'first': first, 'slots': slots, 'borrow_slots': slots - first, 'borrow_bytes': target - offsets[first],
             'lent': [[s, s] for s in range(first, slots)]})]
    mask = [s if 0 <= s < first else -1 for s in original]
    native = []
    pos = 0
    for t in [16384] * 6 + [4091]:
        stream_all = t >= 4096
        chunk = {'p0': pos, 'T': t, 'allocated_T': 16384, 'LB': 0, 'LE': 48, 'n_expert': 512,
                 'K': 10, 'stream_all': stream_all, 'ring': 384}
        rows.append(('P23_CHUNK', chunk))
        native.append(dict({k: chunk[k] for k in ('p0', 'T', 'allocated_T', 'stream_all')}, cpu_share_limit=4096))
        count = byte_count = 0
        cnt = [t * 10 // 512 + int(e < t * 10 % 512) for e in range(512)]
        for layer in range(48):
            resident = mask[layer * 512:(layer + 1) * 512]
            rows.append(('P23_LAYER', {'p0': pos, 'T': t, 'layer': layer, 'use_mmq': True,
                'fused_l': False, 'fused_nat': False, 'native': True, 'gu_type': 2, 'd_type': 3,
                'blob_bytes': sizes[layer], 'stream_all': stream_all, 'route_counts_available': True,
                'host_res': resident, 'cnt': list(cnt), 'on_cpu': [0] * 512, 'n_cpu': 0, 'rows_cpu': 0, 'n_stream': 0}))
            missing = sum(s < 0 for s in resident)
            count += missing; byte_count += missing * sizes[layer]
        rows.append(('P23_H2D', {'p0': pos, 'T': t, 'inline_bytes': 0, 'inline_count': 0,
            'issuer_bytes': byte_count if stream_all else 0, 'issuer_count': count if stream_all else 0,
            'staged_bytes': 0 if stream_all else byte_count, 'staged_count': 0 if stream_all else count,
            'bytes': byte_count, 'count': count, 'submitted_only': True}))
        pos += t
    rows += [('P23_PREFILL_COMPLETE', {'pos0': 0, 'n': pos, 'compute_copy_sync_ok': True, 'timing_enabled': True}),
             ('P23_TIMING', {'pos0': 0, 'n': pos, 'scope': 'run_impl', 'wait_copy_ms': wait_ms,
                            'host_group_ms': 100, 'copy_sum_is_critical_path': False}),
             ('P23_REFILL_ISSUE', {'mode': 'serve', 'dev': -1, 'chunk': 16384,
                  'bytes': sum(sizes[s // 512] for s in range(first, slots)), 'count': slots - first,
                  'copy_calls': slots - first, 'parts_experts': 0, 'queued_experts': slots - first, 'blocking_experts': 0}),
             ('P23_REFILL_SYNC', {'mode': 'serve', 'dev': -1, 'count': slots - first, 'sync_ok': True}),
             ('P23_REFILL_DONE', {'mode': 'serve', 'count': slots - first, 'participants': 1, 'wall_ms': 30, 'sync_ok': True})]
    return cache, rows, native


def save(folder, cache, rows, native):
    folder.mkdir(parents=True, exist_ok=True)
    request = '\n'.join(marker + ' ' + json.dumps(row) for marker, row in rows) + '\n'
    request += '\n'.join('P19_CHUNK ' + json.dumps(row) for row in native) + '\n'
    (folder / 'engine.log').write_text('P23_CACHE ' + json.dumps(cache) + '\n' + request)
    (folder / 'request.engine.log').write_text(request)
    (folder / 'metrics.json').write_text(json.dumps({'metrics': {'prompt_tokens': 102400, 'read_tokens': 102400,
        'generated_tokens': 2048, 'reused_tokens': 0, 'ttft_s': 30, 'wall_s': 43, 'decode_ms': 13000}}))
    (folder / 'RUN_RESULT.json').write_text(json.dumps({'status': 'PASS'}))


class CostAnalysisTests(unittest.TestCase):
    def test_complete_identity_route_copy_refill_chain_has_601_real_experts(self):
        with tempfile.TemporaryDirectory() as d:
            task = Path(d)
            save(task / 'A', *fixture(5884, 600))
            save(task / 'C', *fixture(6485, 500))
            result = analysis.compare(task)
            self.assertEqual(result['status'], 'PASS_MECHANISM_SIGNAL')
            self.assertEqual(result['distinct_retained_experts'], 601)
            self.assertEqual(result['A']['FFN_records'], 7 * 48)
            self.assertTrue(all(r['routed_retained_C'] == 601 for r in result['per_chunk']))
            self.assertEqual(result['prefill_and_refill_bytes_saved'], 8 * result['distinct_retained_slot_bytes'])

    def test_incomplete_or_stale_route_data_cannot_pass(self):
        for fault in ('missing_layer', 'fused', 'count_sum', 'native_chunk'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                cache, rows, native = fixture(5884, 600)
                i = next(i for i, r in enumerate(rows) if r[0] == 'P23_LAYER')
                if fault == 'missing_layer': rows.pop(i)
                elif fault == 'fused': rows[i][1].update(fused_l=True, route_counts_available=False, cnt=None, on_cpu=None)
                elif fault == 'count_sum': rows[i][1]['cnt'][0] += 1
                else: native.pop()
                folder = Path(d) / 'A'; save(folder, cache, rows, native)
                with self.assertRaises(RuntimeError): analysis.validate_arm(folder, 'A')

    def test_wrong_physical_or_loan_identity_and_unfinished_refill_are_rejected(self):
        for fault in ('cache', 'loan', 'mask', 'copy_bytes', 'refill_bytes', 'refill_sync', 'device'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                cache, rows, native = fixture(5884, 600)
                if fault == 'cache': cache['slot_offsets'][-1] -= 256
                elif fault == 'loan': rows[0][1]['lent'][0][1] -= 1
                elif fault == 'mask': next(r for m, r in rows if m == 'P23_LAYER')['host_res'][0] = -1
                elif fault == 'copy_bytes': next(r for m, r in rows if m == 'P23_H2D')['bytes'] -= 1
                elif fault == 'refill_bytes': next(r for m, r in rows if m == 'P23_REFILL_ISSUE')['bytes'] -= 256
                elif fault == 'device': rows[0][1]['dev'] = 0
                else: rows = [(m, r) for m, r in rows if m != 'P23_REFILL_SYNC']
                folder = Path(d) / 'A'; save(folder, cache, rows, native)
                with self.assertRaises(RuntimeError): analysis.validate_arm(folder, 'A')

    def test_failed_run_and_changed_candidate_slot_delta_block_pair(self):
        with tempfile.TemporaryDirectory() as d:
            task = Path(d)
            save(task / 'A', *fixture(5884, 600)); save(task / 'C', *fixture(6484, 500))
            with self.assertRaisesRegex(RuntimeError, 'EXPECTED_16K_601_SLOT_DELTA_CHANGED'): analysis.compare(task)
            (task / 'A/RUN_RESULT.json').write_text('{"status":"FAIL"}')
            with self.assertRaisesRegex(RuntimeError, 'COST_ARM_NOT_PASS'): analysis.compare(task)


if __name__ == '__main__':
    unittest.main()
