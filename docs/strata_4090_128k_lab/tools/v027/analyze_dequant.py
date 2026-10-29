"""Read-only Nsight dequant candidate accounting; not a critical-path proof."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3


def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if end < start:
            raise ValueError('NEGATIVE_INTERVAL')
        if end == start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def interval_length(intervals):
    return sum(end - start for start, end in merge_intervals(intervals))


def intersection_length(left, right):
    left, right = merge_intervals(left), merge_intervals(right)
    i = j = total = 0
    while i < len(left) and j < len(right):
        total += max(0, min(left[i][1], right[j][1]) - max(left[i][0], right[j][0]))
        if left[i][1] <= right[j][1]:
            i += 1
        else:
            j += 1
    return total


def optimistic_launch_window(start, end, api_start):
    if end < start:
        raise ValueError('NEGATIVE_INTERVAL')
    # API entry is the earliest possible enqueue, unlike API return.
    return min(end - start, max(0, start - api_start))


def candidate_class(name):
    if 'dequant' not in name.lower():
        return None
    if 'dequant_flat' in name:
        return 'iq_flat_potentially_mixed_candidate'
    if 'dequant_kernel<' in name and 'H16' in name:
        return 'h16_dispatch_dense_candidate'
    return 'other_dequant_candidate'


def _quote(name):
    return '"' + name.replace('"', '""') + '"'


def _schema(connection):
    names = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    return {name: [r[1] for r in connection.execute('PRAGMA table_info(' + _quote(name) + ')')]
            for name in names}


def _require(schema, table, fields):
    return sorted(set(fields) - set(schema.get(table, [])))


def _read(connection, table, fields):
    return [dict(zip(fields, row)) for row in connection.execute(
        'SELECT ' + ','.join(_quote(x) for x in fields) + ' FROM ' + _quote(table))]


def _clip(row, start, end):
    a, b = max(row['start'], start), min(row['end'], end)
    return [a, b] if b > a else None


def _runtime_match(kernel, runtime):
    matches = runtime.get(kernel['correlationId'], [])
    if len(matches) != 1:
        return None, 'missing' if not matches else 'ambiguous'
    api = matches[0]
    if api['end'] < api['start']:
        return None, 'invalid_runtime_interval'
    if api['returnValue'] != 0 or 'Launch' not in api['name']:
        return None, 'not_successful_launch'
    return api, None


def window_metrics(kernels, copies, start, end, runtime, memcpy_available=True):
    selected = [k for k in kernels if _clip(k, start, end)]
    candidates = [k for k in selected if candidate_class(k['name'])]
    target = merge_intervals([_clip(k, start, end) for k in candidates])
    other = [_clip(k, start, end) for k in selected if not candidate_class(k['name'])]
    memcpy = [_clip(k, start, end) for k in copies if _clip(k, start, end)]
    target_ns = interval_length(target)
    kernel_overlap = intersection_length(target, other)
    copy_overlap = intersection_length(target, memcpy)
    combined_overlap = intersection_length(target, other + memcpy)
    groups = {}
    for k in selected:
        key = (k['name'], k['deviceId'], k['contextId'], k['streamId'],
               k['gridX'], k['gridY'], k['gridZ'])
        group = groups.setdefault(key, {'name': k['name'], 'device': k['deviceId'],
            'context': k['contextId'], 'stream': k['streamId'],
            'grid': [k['gridX'], k['gridY'], k['gridZ']],
            'candidate_class': candidate_class(k['name']), 'count': 0, 'cumulative_ns': 0})
        a, b = _clip(k, start, end)
        group['count'] += 1
        group['cumulative_ns'] += b - a
    attributed = 0
    window_sum = 0
    api_names = Counter()
    failures = Counter()
    examples = []
    api_after_gpu_start = 0
    for kernel in candidates:
        api, error = _runtime_match(kernel, runtime)
        if error:
            failures[error] += 1
            if len(examples) < 20:
                examples.append({'correlation_id': kernel['correlationId'], 'reason': error})
            continue
        attributed += 1
        api_names[api['name']] += 1
        api_after_gpu_start += api['start'] > kernel['start']
        a, b = _clip(kernel, start, end)
        window_sum += optimistic_launch_window(a, b, api['start'])
    unresolved_names = sum(k['name'] == '<UNRESOLVED_NAME>' for k in selected)
    by_class = {}
    for kind in sorted({candidate_class(k['name']) for k in candidates}):
        subset = [k for k in candidates if candidate_class(k['name']) == kind]
        intervals = [_clip(k, start, end) for k in subset]
        by_class[kind] = {'count': len(subset), 'union_ns': interval_length(intervals),
                         'cumulative_ns': sum(b - a for a, b in intervals),
                         'maximum_grid_x': max(k['gridX'] for k in subset),
                         'grid_x_4096_count': sum(k['gridX'] == 4096 for k in subset)}
    state = ('NO_KERNEL_TRACE' if not selected else 'UNATTRIBUTED' if failures or unresolved_names
             else 'CANDIDATE_SUPERSET_OBSERVED' if candidates else 'NO_CANDIDATE_KERNEL_OBSERVED')
    return {'state': state, 'start_ns': start, 'end_ns': end, 'wall_ns': end - start,
        'kernel_count': len(selected), 'candidate_count': len(candidates),
        'candidate_class_counts': dict(Counter(candidate_class(k['name']) for k in candidates)),
        'candidate_class_metrics': by_class,
        'kernel_groups': sorted(groups.values(), key=lambda x: (-x['cumulative_ns'], x['name'])),
        'candidate_cumulative_ns': sum(_clip(k, start, end)[1] - _clip(k, start, end)[0] for k in candidates),
        'candidate_union_ns': target_ns, 'candidate_union_intervals_ns': target,
        'candidate_union_fraction_of_wall': target_ns / (end - start) if end > start else None,
        'overlap_other_kernel_ns': kernel_overlap,
        'overlap_memcpy_ns': copy_overlap if memcpy_available else None,
        'overlap_other_kernel_or_memcpy_ns': combined_overlap if memcpy_available else None,
        'candidate_time_without_other_traced_gpu_work_ns': target_ns - combined_overlap if memcpy_available else None,
        'overlap_is_not_causal_hiding': True,
        'runtime_attributed_candidates': attributed, 'runtime_match_failures': dict(failures),
        'runtime_failure_examples': examples, 'runtime_launch_names': dict(api_names),
        'api_start_after_gpu_start_count': api_after_gpu_start,
        'known_candidate_api_start_window_sum_ns': window_sum,
        'candidate_api_start_window_sum_ns': window_sum if not failures and not unresolved_names else None,
        'unresolved_kernel_names': unresolved_names,
        'exact_critical_path_reconstructed': False,
        'bound_assumptions': ['candidate names are an upper superset, not proven dense/eligible calls',
            'runtime API start is earliest possible enqueue, not observed actual enqueue',
            'weight ready, scratch free and unlimited concurrent resources assumed for launch-window bound',
            'non-target activity durations held fixed; contention effects not modeled',
            'profiled wall time may be perturbed; fractions are not unprofiled performance estimates',
            'overlap does not identify dependencies or prove the dequant is hidden',
            'all intervals are clipped to this NVTX window; only traced engine GPU work counted']}


def expected_pid_from_folder(folder):
    if folder is None:
        return None
    path = Path(folder) / 'engine-argv.json'
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        return data.get('pid') if isinstance(data.get('pid'), int) else None
    if isinstance(data, list):
        engines = [row for row in data if isinstance(row, dict) and isinstance(row.get('pid'), int)
                   and Path(row.get('exe', '')).name == 'strata']
        if len(engines) != 1:
            raise ValueError('RUN_FOLDER_ENGINE_PID_NOT_UNIQUE')
        return engines[0]['pid']
    raise ValueError('UNSUPPORTED_ENGINE_ARGV_RECEIPT')


def analyze_trace(path, expected_pid=None, run_folder=None):
    path = Path(path).resolve()
    result = {'trace': str(path), 'state': 'NO_TRACE', 'requests': [],
              'original_six_status': 'FAIL_UNCHANGED', 'scoring_changed': False,
              'exact_critical_path_reconstructed': False}
    if not path.is_file() or path.stat().st_size == 0:
        result['error'] = 'TRACE_FILE_MISSING_OR_EMPTY'
        return result
    try:
        connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    except sqlite3.Error as error:
        result['error'] = str(error)
        return result
    try:
        connection.execute('BEGIN')
        schema = _schema(connection)
        result['actual_schema'] = schema
        needed = {'StringIds': ['id', 'value'], 'PROCESSES': ['globalPid', 'pid', 'name'],
            'CUPTI_ACTIVITY_KIND_KERNEL': ['start', 'end', 'deviceId', 'contextId', 'streamId',
                'correlationId', 'globalPid', 'demangledName', 'gridX', 'gridY', 'gridZ'],
            'NVTX_EVENTS': ['start', 'end', 'text', 'textId']}
        missing = {table: fields for table, required in needed.items()
                   if (fields := _require(schema, table, required))}
        if missing:
            result['error'] = 'REQUIRED_TRACE_SCHEMA_MISSING'
            result['missing_schema'] = missing
            return result
        strings = dict(connection.execute('SELECT id,value FROM StringIds'))
        processes = _read(connection, 'PROCESSES', needed['PROCESSES'])
        kernels = _read(connection, 'CUPTI_ACTIVITY_KIND_KERNEL', needed['CUPTI_ACTIVITY_KIND_KERNEL'])
        if not kernels:
            result['error'] = 'KERNEL_TRACE_EMPTY'
            return result
        expected_pid = expected_pid if expected_pid is not None else expected_pid_from_folder(run_folder)
        kernel_pids = {k['globalPid'] for k in kernels}
        owners = [p for p in processes if p['globalPid'] in kernel_pids and
                  (p['pid'] == expected_pid if expected_pid is not None else Path(p['name'] or '').name == 'strata')]
        if len(owners) != 1 or owners[0]['globalPid'] is None or owners[0]['globalPid'] % (1 << 24):
            result.update(state='UNATTRIBUTED', error='ENGINE_PROCESS_MAPPING_NOT_UNIQUE_OR_ALIGNED',
                          process_candidates=owners, expected_pid=expected_pid)
            return result
        owner = owners[0]
        gpid = owner['globalPid']
        result['engine_process'] = owner
        result['process_attribution'] = 'PROCESSES record; runtime globalTid checked in aligned globalPid+[0,2^24)'
        kernels = [k for k in kernels if k['globalPid'] == gpid]
        for kernel in kernels:
            kernel['name'] = strings.get(kernel['demangledName'], '<UNRESOLVED_NAME>')
            if kernel['end'] < kernel['start']:
                raise ValueError('NEGATIVE_KERNEL_INTERVAL')
        runtime_fields = ['start', 'end', 'globalTid', 'correlationId', 'nameId', 'returnValue']
        runtime = defaultdict(list)
        if not _require(schema, 'CUPTI_ACTIVITY_KIND_RUNTIME', runtime_fields):
            wanted = {k['correlationId'] for k in kernels if candidate_class(k['name'])}
            for row in _read(connection, 'CUPTI_ACTIVITY_KIND_RUNTIME', runtime_fields):
                tid = row['globalTid']
                if tid is not None and gpid <= tid < gpid + (1 << 24) and row['correlationId'] in wanted:
                    row['name'] = strings.get(row['nameId'], '<UNRESOLVED_API>')
                    runtime[row['correlationId']].append(row)
        else:
            result['runtime_schema_missing'] = _require(schema, 'CUPTI_ACTIVITY_KIND_RUNTIME', runtime_fields)
        copy_fields = ['start', 'end', 'globalPid', 'deviceId']
        copies = []
        if not _require(schema, 'CUPTI_ACTIVITY_KIND_MEMCPY', copy_fields):
            copies = [r for r in _read(connection, 'CUPTI_ACTIVITY_KIND_MEMCPY', copy_fields) if r['globalPid'] == gpid]
            if any(r['end'] < r['start'] for r in copies):
                raise ValueError('NEGATIVE_MEMCPY_INTERVAL')
        result['memcpy_trace_available'] = not _require(schema, 'CUPTI_ACTIVITY_KIND_MEMCPY', copy_fields)
        diagnostic_tables = [n for n in schema if any(s in n.lower() for s in ['drop', 'lost', 'diagnostic', 'warning', 'error'])]
        diagnostic_columns = {n: [c for c in columns if any(s in c.lower() for s in ['drop', 'lost', 'diagnostic'])]
                              for n, columns in schema.items()}
        indicators = {}
        for table in ['META_DATA_CAPTURE', 'META_DATA_EXPORT']:
            if not _require(schema, table, ['name', 'value']):
                values = _read(connection, table, ['name', 'value'])
                indicators[table] = values
        result['trace_diagnostics'] = {'indicator_tables': diagnostic_tables,
            'indicator_columns': {n: cols for n, cols in diagnostic_columns.items() if cols},
            'indicator_table_row_counts': {n: connection.execute('SELECT COUNT(*) FROM ' + _quote(n)).fetchone()[0] for n in diagnostic_tables},
            'capture_and_export_metadata': indicators,
            'dropped_event_status': 'NOT_ESTABLISHED_FROM_THIS_EXPORT',
            'absence_of_indicator_is_not_proof_of_zero_drops': True}
        markers = _read(connection, 'NVTX_EVENTS', needed['NVTX_EVENTS'])
        for row in markers:
            row['label'] = row['text'] or strings.get(row['textId'], '')
        requests = [r for r in markers if r['label'].startswith('P10_REQUEST/')]
        if not requests:
            result.update(state='NO_REQUEST_MARKERS', error='P10_REQUEST_RANGE_MISSING')
            return result
        for request in sorted(requests, key=lambda r: r['start']):
            name = request['label'].split('/', 1)[1]
            first = [r for r in markers if r['label'] == 'P10_FIRST/' + name and r['end'] is None
                     and request['end'] is not None and request['start'] <= r['start'] <= request['end']]
            if request['end'] is None or len(first) != 1 or first[0]['start'] <= request['start']:
                result['requests'].append({'name': name, 'state': 'INVALID_REQUEST_MARKERS'})
                continue
            selected = [k for k in kernels if _clip(k, request['start'], request['end'])]
            devices = {k['deviceId'] for k in selected}
            if len(devices) != 1:
                result['requests'].append({'name': name, 'state': 'UNATTRIBUTED', 'error': 'REQUEST_HAS_NO_SINGLE_DEVICE_KERNEL_TRACE'})
                continue
            copies_here = [c for c in copies if c['deviceId'] in devices]
            result['requests'].append({'name': name,
                'ttft': window_metrics(kernels, copies_here, request['start'], first[0]['start'], runtime, result['memcpy_trace_available']),
                'request': window_metrics(kernels, copies_here, request['start'], request['end'], runtime, result['memcpy_trace_available'])})
        result['state'] = ('OBSERVED' if all('request' in r and all(r[w]['state'] not in ['UNATTRIBUTED', 'NO_KERNEL_TRACE'] for w in ['request', 'ttft'])
                                          for r in result['requests']) else 'UNATTRIBUTED')
        result['time_unit'] = 'ns in the same Nsight exported time base; no application-clock subtraction'
        return result
    except (sqlite3.Error, ValueError) as error:
        result.update(state='INVALID_TRACE', error=str(error))
        return result
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, action='append', required=True)
    parser.add_argument('--run-folder', type=Path, action='append')
    parser.add_argument('--expected-pid', type=int)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    folders = args.run_folder or [None] * len(args.trace)
    if len(folders) != len(args.trace):
        parser.error('--run-folder count must match --trace count')
    if args.output.exists():
        parser.error('output exists; preserve prior analysis')
    result = {'traces': [analyze_trace(t, args.expected_pid, f) for t, f in zip(args.trace, folders)],
              'original_six_status': 'FAIL_UNCHANGED', 'scoring_changed': False}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'states': [t['state'] for t in result['traces']],
                      'requests': [r['name'] for t in result['traces'] for r in t['requests']]}))
