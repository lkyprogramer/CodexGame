"""Validate the complete P23 trace before relating physical slots to real routed work and transfers."""
import argparse
import json
import math
from pathlib import Path


def records(text):
    return [(line.split(' ', 1)[0], json.loads(line.split(' ', 1)[1])) for line in text.splitlines()
            if line.startswith('P23_')]


def inspect_arm(folder, arm):
    folder = Path(folder)
    cache_rows = [r for m, r in records((folder / 'engine.log').read_text()) if m == 'P23_CACHE' and r['mode'] == 'serve']
    if len(cache_rows) != 1: raise RuntimeError('CACHE_RECORD_COVERAGE')
    cache = cache_rows[0]
    offsets, resident = cache['slot_offsets'], cache['host_res']
    if (cache['slots'] != 10272 or cache['full_slots'] != 10272 or cache['n_expert'] != 512 or
            cache['variable_offsets'] is not True or cache['cache_bytes'] // 1048576 != 17055 or
            len(offsets) != 10273 or offsets[0] != 0 or offsets[-1] != cache['cache_bytes'] or
            any(b <= a for a, b in zip(offsets, offsets[1:])) or len(resident) != 48 * 512):
        raise RuntimeError('PHYSICAL_CACHE_CHANGED')
    present = [s for s in resident if s >= 0]
    if sorted(present) != list(range(10272)) or any(s < -1 for s in resident):
        raise RuntimeError('INITIAL_RESIDENT_IDENTITY_INVALID')
    request_log = (folder / 'request.engine.log').read_text()
    metrics = json.loads((folder / 'metrics.json').read_text())['metrics']
    if any(metrics.get(k) != v for k, v in {'prompt_tokens': 102400, 'read_tokens': 102400,
                                           'generated_tokens': 2048, 'reused_tokens': 0}.items()):
        raise RuntimeError('FROZEN_REQUEST_NOT_COMPLETED')
    parsed = records(request_log)
    chunks, layers, h2d, complete, timings = {}, {}, {}, [], []
    loans, refills, done_refills = [], [], []
    active = None
    for marker, row in parsed:
        if marker == 'P23_LOAN':
            if active is not None or row['mode'] != 'serve' or row['dev'] != -1 or row['slots'] != 10272:
                raise RuntimeError('LOAN_LIFECYCLE_INVALID')
            first = row['first']; pairs = row['lent']
            if (not 0 <= first < 10272 or row['borrow_slots'] != 10272 - first or
                    row['borrow_bytes'] != offsets[-1] - offsets[first] or
                    len(pairs) != row['borrow_slots'] or sorted(s for _, s in pairs) != list(range(first, 10272)) or
                    len({i for i, _ in pairs}) != len(pairs) or
                    any(not 0 <= i < len(resident) or resident[i] != s for i, s in pairs)):
                raise RuntimeError('LOAN_SLOT_IDENTITY_INVALID')
            active = dict(row, index=len(loans), issued=False)
            loans.append(active)
        elif marker == 'P23_CHUNK':
            key = (row['p0'], row['T'])
            if (active is None or key in chunks or row['LB'] != 0 or row['LE'] != 48 or row['n_expert'] != 512 or
                    row['K'] != 10 or not 0 < row['T'] <= row['allocated_T'] <= 16384):
                raise RuntimeError('CHUNK_GEOMETRY_OR_LOAN_INVALID')
            chunks[key] = dict(row, loan_index=active['index'])
        elif marker == 'P23_LAYER':
            key = (row['p0'], row['T']); full_key = (*key, row['layer'])
            if active is None or key not in chunks or full_key in layers or not 0 <= row['layer'] < 48:
                raise RuntimeError('LAYER_RECORD_IDENTITY_INVALID')
            if row['route_counts_available'] is not True or row['fused_l'] or row['fused_nat']:
                raise RuntimeError('ROUTE_COUNTS_UNAVAILABLE')
            mask, cnt, cpu = row['host_res'], row['cnt'], row['on_cpu']
            base = resident[row['layer'] * 512:(row['layer'] + 1) * 512]
            lent = {i for i, _ in active['lent']}
            expected = [-1 if row['layer'] * 512 + e in lent else s for e, s in enumerate(base)]
            if mask != expected: raise RuntimeError('ACTUAL_RESIDENT_MASK_DIFFERS_FROM_LOAN')
            if (len(cnt) != 512 or len(cpu) != 512 or any(type(x) is not int or not 0 <= x <= row['T'] for x in cnt) or
                    sum(cnt) != row['T'] * 10 or any(x not in (0, 1) for x in cpu) or row['blob_bytes'] <= 0 or
                    row['n_cpu'] != sum(cpu) or row['rows_cpu'] != sum(c for c, on in zip(cnt, cpu) if on) or
                    any(on and (c <= 0 or s >= 0) for c, on, s in zip(cnt, cpu, mask)) or
                    row['stream_all'] != chunks[key]['stream_all']):
                raise RuntimeError('ROUTE_COUNTS_OR_CPU_DISPATCH_INVALID')
            layers[full_key] = row
        elif marker == 'P23_H2D':
            key = (row['p0'], row['T'])
            if key not in chunks or key in h2d or row['submitted_only'] is not True:
                raise RuntimeError('H2D_RECORD_COVERAGE')
            if (row['bytes'] != sum(row[n + '_bytes'] for n in ('inline', 'issuer', 'staged')) or
                    row['count'] != sum(row[n + '_count'] for n in ('inline', 'issuer', 'staged'))):
                raise RuntimeError('H2D_COUNTER_SUM_INVALID')
            h2d[key] = row
        elif marker == 'P23_PREFILL_COMPLETE':
            if row['compute_copy_sync_ok'] is not True or row['timing_enabled'] is not True:
                raise RuntimeError('PREFILL_SYNC_NOT_COMPLETE')
            complete.append(row)
        elif marker == 'P23_TIMING':
            if row['scope'] != 'run_impl' or row['copy_sum_is_critical_path'] is not False or any(
                    not isinstance(row[k], (int, float)) or not math.isfinite(row[k]) or row[k] < 0
                    for k in ('wait_copy_ms', 'host_group_ms')):
                raise RuntimeError('EXPOSED_WAIT_INTERVAL_INVALID')
            timings.append(row)
        elif marker == 'P23_REFILL_ISSUE':
            if (active is None or active['issued'] or row['mode'] != 'serve' or row['dev'] != -1 or
                    row['count'] != len(active['lent']) or row['chunk'] != active['chunk'] or
                    row['count'] != sum(row[k] for k in ('parts_experts', 'queued_experts', 'blocking_experts'))):
                raise RuntimeError('REFILL_SUBMISSION_INVALID')
            expected_bytes = 0
            for i, _ in active['lent']:
                layer_rows = [r for key, r in layers.items() if key[2] == i // 512]
                if not layer_rows: raise RuntimeError('REFILL_LAYER_METADATA_MISSING')
                sizes = {r['blob_bytes'] for r in layer_rows}
                if len(sizes) != 1: raise RuntimeError('LAYER_BLOB_SIZE_CHANGED')
                expected_bytes += sizes.pop()
            if row['bytes'] != expected_bytes or row['copy_calls'] < row['count']:
                raise RuntimeError('REFILL_BYTES_DIFFERS_FROM_ACTUAL_EXPERTS')
            active['issued'] = True; refills.append(row)
        elif marker == 'P23_REFILL_SYNC':
            if (active is None or not active['issued'] or row['dev'] != -1 or row['sync_ok'] is not True or
                    row['count'] != len(active['lent'])):
                raise RuntimeError('REFILL_SYNC_NOT_COMPLETE')
            active = None
        elif marker == 'P23_REFILL_DONE':
            if (active is not None or row['mode'] != 'serve' or row['participants'] != 1 or row['sync_ok'] is not True or
                    len(done_refills) >= len(refills) or row['count'] != refills[len(done_refills)]['count'] or
                    not math.isfinite(row['wall_ms']) or row['wall_ms'] < 0):
                raise RuntimeError('REFILL_DONE_NOT_COMPLETE')
            done_refills.append(row)
        else:
            raise RuntimeError('UNEXPECTED_COST_RECORD: ' + marker)
    if active is not None or not loans or len(refills) != len(loans) or len(done_refills) != len(loans):
        raise RuntimeError('LOAN_NOT_FULLY_RESTORED')
    if not chunks or max(t for _, t in chunks) != 16384 or not 100000 <= sum(t for _, t in chunks) <= 102400:
        raise RuntimeError('ACTUAL_100K_PREFILL_MISSING')
    native_chunks = [json.loads(s.split(' ', 1)[1]) for s in request_log.splitlines() if s.startswith('P19_CHUNK ')]
    actual = [{k: r[k] for k in ('p0', 'T', 'allocated_T', 'stream_all')} for r in chunks.values()]
    if actual != [{k: r[k] for k in ('p0', 'T', 'allocated_T', 'stream_all')} for r in native_chunks] or any(
            r['cpu_share_limit'] != 4096 for r in native_chunks):
        raise RuntimeError('NATIVE_CHUNK_COVERAGE_DIFFERS')
    if len(layers) != len(chunks) * 48 or set(h2d) != set(chunks): raise RuntimeError('INCOMPLETE_LAYER_OR_COPY_COVERAGE')
    for key, chunk in chunks.items():
        expected_count = expected_bytes = 0
        for l in range(48):
            row = layers[(*key, l)]
            n = sum(s < 0 if chunk['stream_all'] else s < 0 and c > 0 and not cpu
                    for s, c, cpu in zip(row['host_res'], row['cnt'], row['on_cpu']))
            expected_count += n; expected_bytes += n * row['blob_bytes']
        if h2d[key]['count'] != expected_count or h2d[key]['bytes'] != expected_bytes:
            raise RuntimeError('ACTUAL_H2D_DIFFERS_FROM_DISPATCH')
    scopes = [(r['pos0'], r['n']) for r in complete]
    if (not scopes or len(set(scopes)) != len(scopes) or scopes != [(r['pos0'], r['n']) for r in timings] or
            sum(n for _, n in scopes) != sum(t for _, t in chunks)):
        raise RuntimeError('PREFILL_COMPLETION_OR_TIMER_COVERAGE')
    covered = set()
    for pos, n in scopes:
        selected = sorted(k for k in chunks if pos <= k[0] < pos + n)
        cursor = pos
        for key in selected:
            if key[0] != cursor or key in covered: raise RuntimeError('PREFILL_INTERVAL_GAP_OR_OVERLAP')
            cursor += key[1]; covered.add(key)
        if cursor != pos + n: raise RuntimeError('PREFILL_INTERVAL_NOT_COMPLETE')
    if covered != set(chunks): raise RuntimeError('UNCOMPLETED_CHUNKS')
    report = {'status': 'PASS', 'arm': arm, 'physical_slots': cache['slots'], 'cache_bytes': cache['cache_bytes'],
        'chunks': list(chunks.values()), 'batched_tokens': sum(t for _, t in chunks), 'FFN_records': len(layers),
        'expert_H2D_bytes': sum(r['bytes'] for r in h2d.values()), 'expert_H2D_count': sum(r['count'] for r in h2d.values()),
        'refill_bytes': sum(r['bytes'] for r in refills), 'refill_experts': sum(r['count'] for r in refills),
        'exposed_wait_copy_ms': sum(r['wait_copy_ms'] for r in timings),
        'refill_wall_ms': sum(r['wall_ms'] for r in done_refills), 'metrics': metrics,
        'scope': 'prefill expert streaming and borrowed-slot refill; excludes startup/decode/KV transfers',
        'diagnostic_only': True}
    return report, {'cache': cache, 'layers': layers, 'chunks': chunks, 'h2d': h2d, 'loans': loans}


def validate_arm(folder, arm):
    return inspect_arm(folder, arm)[0]


def compare(task):
    task = Path(task)
    for arm in ('A', 'C'):
        if json.loads((task / arm / 'RUN_RESULT.json').read_text())['status'] != 'PASS':
            raise RuntimeError('COST_ARM_NOT_PASS: ' + arm)
    a, ad = inspect_arm(task / 'A', 'A'); c, cd = inspect_arm(task / 'C', 'C')
    if ad['cache'] != cd['cache']: raise RuntimeError('A_C_INITIAL_PHYSICAL_CACHE_DIFFERS')
    geometry = lambda d: [{k: r[k] for k in ('p0', 'T', 'allocated_T', 'LB', 'LE', 'K', 'stream_all', 'ring')}
                          for r in d['chunks'].values()]
    if geometry(ad) != geometry(cd): raise RuntimeError('A_C_CHUNK_GEOMETRY_DIFFERS')
    retained, per_chunk, main_counts = {}, [], []
    for key, chunk in ad['chunks'].items():
        chunk_retained = set(); routed_c = routed_a = rows_c = rows_a = saved_blob_bytes = 0
        for layer in range(48):
            ar, cr = ad['layers'][(*key, layer)], cd['layers'][(*key, layer)]
            if any(ar[k] != cr[k] for k in ('blob_bytes', 'gu_type', 'd_type', 'native', 'use_mmq', 'fused_l', 'fused_nat')):
                raise RuntimeError('A_C_EXPERT_PATH_DIFFERS')
            for expert, (aa, cc) in enumerate(zip(ar['host_res'], cr['host_res'])):
                if aa >= 0 and cc != aa: raise RuntimeError('C_LOST_OR_REMAPPED_RESIDENT_EXPERT')
                if aa < 0 <= cc:
                    identity = layer * 512 + expert; chunk_retained.add(identity)
                    routed_a += ar['cnt'][expert] > 0; routed_c += cr['cnt'][expert] > 0
                    rows_a += ar['cnt'][expert]; rows_c += cr['cnt'][expert]
                    saved_blob_bytes += cr['blob_bytes']
                    offsets = cd['cache']['slot_offsets']
                    retained[identity] = {'layer': layer, 'expert': expert, 'slot': cc,
                        'slot_bytes': offsets[cc + 1] - offsets[cc], 'blob_bytes': cr['blob_bytes']}
        actual_delta = ad['h2d'][key]['bytes'] - cd['h2d'][key]['bytes']
        if chunk['stream_all'] and actual_delta != saved_blob_bytes:
            raise RuntimeError('RETAINED_EXPERT_TRANSFER_DELTA_NOT_CONFIRMED')
        if key[1] == 16384: main_counts.append(len(chunk_retained))
        per_chunk.append({'p0': key[0], 'T': key[1], 'retained_experts': len(chunk_retained),
            'routed_retained_A': routed_a, 'routed_retained_C': routed_c, 'retained_route_rows_A': rows_a,
            'retained_route_rows_C': rows_c, 'stream_all': chunk['stream_all'],
            'retained_blob_bytes': saved_blob_bytes, 'actual_expert_H2D_bytes_saved': actual_delta})
    if not main_counts or any(n != 601 for n in main_counts): raise RuntimeError('EXPECTED_16K_601_SLOT_DELTA_CHANGED')
    byte_savings = a['expert_H2D_bytes'] + a['refill_bytes'] - c['expert_H2D_bytes'] - c['refill_bytes']
    wait_savings = a['exposed_wait_copy_ms'] - c['exposed_wait_copy_ms']
    hit = sum(r['retained_route_rows_C'] for r in per_chunk) > 0
    signal = hit and (byte_savings > 0 or wait_savings > 0)
    return {'status': 'PASS_MECHANISM_SIGNAL' if signal else 'CAPACITY_ONLY_NO_SIGNAL', 'A': a, 'C': c,
        'retained_expert_ids': [retained[k] for k in sorted(retained)],
        'distinct_retained_experts': len(retained), 'distinct_retained_slot_bytes': sum(r['slot_bytes'] for r in retained.values()),
        'per_chunk': per_chunk, 'prefill_and_refill_bytes_saved': byte_savings,
        'observed_exposed_wait_copy_ms_saved': wait_savings, 'formal_performance_samples': 0,
        'limits': ['one diagnostic A/C pair; no performance CI', 'A/C route/CPU choices may naturally differ',
                   'H2D byte reduction is not a critical-path time estimate', 'host and GPU waits are not added',
                   'request and task quality adoption gates remain separate']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('task', type=Path)
    a = p.parse_args(); result = compare(a.task)
    (a.task / 'ANALYSIS.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'distinct_retained_experts', 'prefill_and_refill_bytes_saved',
                                           'observed_exposed_wait_copy_ms_saved')}))
