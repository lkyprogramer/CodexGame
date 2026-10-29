"""Summarize retained P13 qualification without treating diagnostic timing as performance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def float_comparison(a, b):
    if len(a) != len(b) or not a or len(a) % 4:
        raise ValueError('FLOAT_ROW_SHAPE_MISMATCH')
    x = struct.unpack('<' + 'f' * (len(a) // 4), a)
    y = struct.unpack('<' + 'f' * (len(b) // 4), b)
    if not all(math.isfinite(v) for v in (*x, *y)):
        raise ValueError('NONFINITE_ROW')
    different = [i for i in range(len(x)) if a[i*4:i*4+4] != b[i*4:i*4+4]]
    first = different[0] if different else None
    return {'bitwise_equal': not different, 'values': len(x), 'different_f32_bits': len(different),
            'max_abs': max(abs(v-w) for v, w in zip(x, y)),
            'first': None if first is None else {'index': first, 'a': x[first], 'b': y[first]},
            'argmax': [max(range(len(x)), key=x.__getitem__), max(range(len(y)), key=y.__getitem__)],
            'sha256': [hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()]}


def records(path, prefix):
    return [json.loads(line[len(prefix):]) for line in path.read_text(errors='replace').splitlines()
            if line.startswith(prefix)]


def first_checkpoint_difference(a, b):
    key = lambda r: tuple(r[k] for k in ('chunk_p0', 'T', 'layer', 'half', 'stage', 'field', 'bytes'))
    if not a or [key(r) for r in a] != [key(r) for r in b]:
        raise ValueError('CHECKPOINT_COVERAGE_MISMATCH')
    for i, (x, y) in enumerate(zip(a, b)):
        if x['fnv1a64'] != y['fnv1a64']:
            return {'index': i, 'equal_prior_hashes': i, 'a': x, 'b': y,
                    'scope': 'first recorded checkpoint, not necessarily first kernel; hash locator, not bytewise equality proof'}
    return {'recorded_checkpoints': len(a), 'hashes_equal': True, 'bytewise_proven': False}


def analyze(task):
    task = Path(task)
    result = {'original_six_status': 'FAIL_UNCHANGED', 'formal_performance_samples': 0,
              'AA': {}, 'allocations': {}, 'diagnostics': {}}
    for label, names, case in [('4K', ('p6-aa-1','p6-aa-2'), 'think-4096'),
                               ('16K', ('p6-16k-aa-1','p6-16k-aa-2'), 'think-first16384'),
                               ('diagnostic4K', ('diag-a-1','diag-a-2'), 'think-4096')]:
        paths = [task / n / (case + '.f32') for n in names]
        if not all(p.exists() for p in paths):
            continue
        row = float_comparison(*(p.read_bytes() for p in paths))
        plans = [json.loads((task/n/'plan.json').read_text()) for n in names]
        row.update(same_binary=plans[0]['exe_sha256']==plans[1]['exe_sha256'],
                   same_args=plans[0]['args']==plans[1]['args'], same_tokens=plans[0]['tokens']==plans[1]['tokens'])
        result['AA'][label] = row
    for folder in sorted(task.iterdir()):
        log = folder / 'stderr.log'
        if not log.exists():
            continue
        rows = records(log, 'P13_HC_ALLOCATION ')
        if rows:
            result['allocations'][folder.name] = rows
    da, db = (task / n / 'stderr.log' for n in ('diag-a-1','diag-a-2'))
    if da.exists() and db.exists():
        result['diagnostics']['first_checkpoint_difference'] = first_checkpoint_difference(
            records(da, 'P13_HC_DIAG '), records(db, 'P13_HC_DIAG '))
        ca, cb = records(da, 'P13_HC_CPU '), records(db, 'P13_HC_CPU ')
        if [(r['chunk_p0'],r['T'],r['layer']) for r in ca] != [(r['chunk_p0'],r['T'],r['layer']) for r in cb]:
            raise ValueError('CPU_COVERAGE_MISMATCH')
        result['diagnostics']['cpu_path_differences'] = [
            {'layer': a['layer'], 'a': a, 'b': b} for a,b in zip(ca,cb)
            if a['on_cpu'] != b['on_cpu'] or a['host_res_fnv1a64'] != b['host_res_fnv1a64']]
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('task', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = analyze(args.task)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'AA': result['AA'], 'diagnostics': result['diagnostics'], 'allocation_phases': list(result['allocations'])}))
