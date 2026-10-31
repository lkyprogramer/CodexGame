"""Validate native host observations; GPU internal intervals remain unknown."""
import hashlib
import json
from pathlib import Path

TIMES = ('begin_ns', 'verified_ns', 'commit_enter_ns', 'commit_return_ns', 'draft_return_ns', 'end_ns')


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def summarize_capture(out, identity, rows):
    out = Path(out)
    windows, requests, edges = [], [], []
    for index, row in enumerate(rows):
        _require(row.get('request_id') == ('prime', 'append_1', 'append_2')[index], 'request ordering')
        _require(row.get('execution_status') == 'COMPLETED', 'incomplete request')
        path = out / f'native-trace.{index}.json'
        trace = json.loads(path.read_text())
        _require(trace.get('schema_version') == 1 and trace.get('request_index') == index, 'trace identity')
        _require(trace.get('clock_domain') == 'steady_clock', 'native clock')
        _require(row['start_monotonic_ns'] <= trace['start_ns'] <= trace['end_ns'] <= row['end_monotonic_ns'],
                 'native/HTTP monotonic clock envelope')
        ids = trace['token_ids']
        _require(isinstance(ids, list) and all(type(x) is int and x >= 0 for x in ids), 'invalid native token IDs')
        _require(0 < len(ids) == row['completion_tokens'] <= 2048, 'native output token accounting')
        _require(trace.get('overflow') is False and trace.get('window_limit') == 2048, 'capture overflow/limit')
        _require(type(trace.get('total_windows')) is int and
                 0 < len(trace['windows']) == trace['total_windows'] <= len(ids), 'incomplete window coverage')
        token_hash = hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()
        raw_gap = clean_gap = window_ns = emitted = clean_count = 0
        previous_end = trace['start_ns']
        for n, w in enumerate(trace['windows']):
            _require(w.get('window_id') == n, 'window ordering')
            ts = [w[k] for k in TIMES]
            _require(all(type(t) is int for t in ts) and ts == sorted(ts)
                     and previous_end <= ts[0] and ts[-1] <= trace['end_ns'], 'window clock/order')
            previous_end = ts[-1]
            _require(type(w['T']) is int and 1 <= w['kept'] <= w['T'] <= 8, 'window acceptance')
            _require(type(w['emitted']) is int and 1 <= w['emitted'] <= w['kept'], 'window output')
            for flag in ('first', 'merged', 'clean_serial_gap', 'async_job', 'job_idle', 'adapt_spawned'):
                _require(type(w[flag]) is bool, 'invalid window flag')
            clean = w['clean_serial_gap']
            if clean:
                _require(not w['first'] and not w['merged'] and w['T'] > 1
                         and w['pending'] == 0 and not w['adapt_spawned']
                         and (not w['async_job'] or (w['astate'] == 0 and w['job_idle'])),
                         'unclosed asynchronous dependency marked clean')
            gap = w['commit_enter_ns'] - w['verified_ns']
            raw_gap += gap
            if clean:
                clean_gap += gap
                clean_count += 1
                edges.append({'from': f'{index}:{n}:verified', 'to': f'{index}:{n}:commit_enter',
                              'verified': True, 'reason': 'existing verify/head synchronization before host commit call; no pending necessary branch',
                              'evidence_ref': f'{path.name}#/windows/{n}'})
            emitted += w['emitted']
            window_ns += w['end_ns'] - w['begin_ns']
            windows.append({**w, 'window_id': str(n), 'engine_id': 'D1', 'request_id': row['request_id'],
                            'clock_domain': 'host CLOCK_MONOTONIC', 'unit': 'ns',
                            'start': w['begin_ns'], 'end': w['end_ns'], 'host_dependency_gap_ns': gap,
                            'critical_exposure': 'SOURCE_CLOSED_HOST_GAP' if clean else 'UNKNOWN',
                            'gpu_internal_times': None, 'cpu_expert_dtype_nt': None})
        _require(emitted == len(ids), 'emitted window/token total mismatch')
        duration = trace['end_ns'] - trace['start_ns']
        _require(duration > 0 and 0 <= clean_gap <= raw_gap <= duration, 'request duration/accounting')
        requests.append({'request_id': row['request_id'], 'native_trace_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'native_token_ids_sha256': token_hash, 'native_token_count': len(ids),
                         'windows': trace['total_windows'], 'closed_host_gap_windows': clean_count,
                         'all_host_dependency_gaps_ms': raw_gap / 1e6, 'source_closed_host_gap_ms': clean_gap / 1e6,
                         'native_decode_observation_ms': duration / 1e6,
                         'observed_gap_delete_all_fraction': raw_gap / duration,
                         'observed_source_closed_fraction': clean_gap / duration,
                         'scope': 'entire observed serial decode; no extrapolation to uninstrumented execution'})
    complete = len(requests) == 3
    unknown = ['GPU internal work and overlap intervals', 'CPU expert task completion/park separation and dtype/nt',
               'exposure of gaps with pending asynchronous work', 'uninstrumented counterfactual and causal speedup']
    warm = [r for r in requests if r['request_id'] != 'prime']
    under_floor = bool(warm) and all(r['observed_gap_delete_all_fraction'] < .04 for r in warm)
    qualification = {'status': 'INSUFFICIENT', 'new_candidate_qualified': False, 'causal_speedup_claim': False,
                     'performance': 'NOT_EVALUATED', 'quality': 'NOT_EVALUATED', 'p05': 'BLOCKED_EVIDENCE',
                     'host_gap_screen': 'BELOW_4_PERCENT_IN_OBSERVED_RUN' if under_floor else 'REQUIRES_SOURCE_DELTA_REVIEW',
                     'reason': 'No new concrete mechanism qualified; unknown GPU/CPU internals retained',
                     'all_three_requests_complete': complete, 'original_six': 'FAIL_UNCHANGED'}
    return {'ANALYSIS': {'request_observations': requests, 'all_three_requests_complete': complete,
                         'native_ids_retokenized_from_text': False, 'unobserved_dependencies': unknown},
            'WINDOWS': windows, 'DEPENDENCIES': {'status': 'PARTIAL_SOURCE_CLOSED', 'edges': edges,
                                              'clock_domain': 'host CLOCK_MONOTONIC', 'unknown_dependencies': unknown},
            'QUALIFICATION': qualification}
