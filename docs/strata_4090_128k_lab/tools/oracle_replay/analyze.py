"""Compare P14 same-process raw snapshots; never treats native failure as proof.

Reads phase/replay/records.jsonl, phase/stderr.log and RUN_RESULT.json.
Memory use is bounded by CHUNK_BYTES, including the ~1 GiB Dm output.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import struct

try:
    import numpy as np
except ImportError:
    np = None

CHUNK_BYTES = 1 << 20
TARGET = {'p0': 0, 'T': 4090, 'layer': 3, 'half': 1}
FLOAT_OUTPUTS = {'GU': 4, 'H': 4, 'Hh': 2, 'cpu_rows': 4, 'Dm': 4, 'shared': 4, 'sg': 4, 'bo': 4}
REQUIRED = frozenset('geometry R inj mixed mixed_h mixed_bf mixed_bf_lo_present ids w resident_present '
                     'host_res compute_geometry dispatch_resident_present dispatch_host_res on_cpu cpu_selection '
                     'cnt off order slot src group_geometry H_kind GU Dm shared sg bo'.split()) - {'host_res', 'dispatch_host_res'}
COMPLETE = 'P14_REPLAY COMPLETE two_same_process_FFN_passes final_logits_oracle=0 path='
REJECTIONS = {
    'input': {r'snapshot mismatch: mixed block 0': 'mixed'},
    'dispatch': {r'invalid replay CPU expert': 'dispatch_resident_present',
                 r'CPU blob identity changed': 'dispatch_resident_present',
                 r'snapshot mismatch: on_cpu block 0': 'on_cpu'},
    'mapping': {r'slot/src expert/token mapping': 'cnt', r'snapshot mismatch: slot block 0': 'slot'},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def records(folder):
    passes = [{}, {}]
    for line_number, line in enumerate((folder / 'records.jsonl').read_text().splitlines(), 1):
        require(bool(line.strip()), f'empty record line {line_number}')
        row = json.loads(line)
        require(isinstance(row, dict), f'invalid record line {line_number}')
        require(row.get('marker') == 'P14_REPLAY' and all(type(row.get(k)) is int and row[k] == v for k, v in TARGET.items()),
                f'wrong target record line {line_number}')
        p, field, size, guard = (row.get(k) for k in ('pass', 'field', 'bytes', 'guard'))
        require(type(p) is int and p in (0, 1), f'invalid pass line {line_number}')
        require(isinstance(field, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', field), f'invalid field line {line_number}')
        require(type(size) is int and size >= 0 and type(guard) is bool, f'invalid length/guard line {line_number}')
        require(field not in passes[p], f'duplicate pass{p} field {field}')
        require(guard == (field not in FLOAT_OUTPUTS), f'wrong guard policy for {field}')
        require(p == 1 or not passes[1], 'pass0 record after pass1 started')
        passes[p][field] = row
    require(bool(passes[0]), 'missing pass0 records')
    require(REQUIRED <= passes[0].keys(), 'missing required pass0 fields: ' + ','.join(sorted(REQUIRED - passes[0].keys())))
    return passes


def check_files(folder, rows, p):
    for name, row in rows.items():
        file = folder / f'pass{p}-{name}.bin'
        require(file.is_file(), f'missing raw file: {file.name}')
        require(file.stat().st_size == row['bytes'], f'raw size mismatch: {file.name}')


def compare_files(a, b, size, width=None):
    result = {'bytes': size, 'different_bytes': 0, 'different_bits': 0, 'first_byte': None}
    if width:
        require(size % width == 0, f'float output alignment: {a.name}')
        result.update(element_bits=width * 8, elements=size // width, different_elements=0,
                      max_abs_finite=0.0, finite=[0, 0], nan=[0, 0], inf=[0, 0], finite_pairs=0)
    # CHUNK_BYTES is aligned for both float widths, and may be reduced in tests.
    block = max(4, CHUNK_BYTES // 4 * 4)
    with a.open('rb') as fa, b.open('rb') as fb:
        offset = 0
        while offset < size:
            n = min(block, size - offset)
            x, y = fa.read(n), fb.read(n)
            require(len(x) == len(y) == n, f'raw changed during read: {a.name}')
            if np is not None:
                ax, ay = np.frombuffer(x, dtype=np.uint8), np.frombuffer(y, dtype=np.uint8)
                xor = np.bitwise_xor(ax, ay)
                different = np.flatnonzero(xor)
                result['different_bytes'] += int(different.size)
                lookup = np.array([i.bit_count() for i in range(256)], dtype=np.uint8)
                result['different_bits'] += int(lookup[xor].sum())
                first = int(different[0]) if different.size else None
            else:
                different = [i for i, (u, v) in enumerate(zip(x, y)) if u != v]
                result['different_bytes'] += len(different)
                result['different_bits'] += sum((u ^ v).bit_count() for u, v in zip(x, y))
                first = different[0] if different else None
            if result['first_byte'] is None and first is not None:
                result['first_byte'] = offset + first
            if width:
                if np is not None:
                    fx, fy = np.frombuffer(x, dtype='<f' + str(width)), np.frombuffer(y, dtype='<f' + str(width))
                    ux, uy = np.frombuffer(x, dtype='<u' + str(width)), np.frombuffer(y, dtype='<u' + str(width))
                    result['different_elements'] += int(np.count_nonzero(ux != uy))
                    for p, values in enumerate((fx, fy)):
                        result['finite'][p] += int(np.count_nonzero(np.isfinite(values)))
                        result['nan'][p] += int(np.count_nonzero(np.isnan(values)))
                        result['inf'][p] += int(np.count_nonzero(np.isinf(values)))
                    valid = np.isfinite(fx) & np.isfinite(fy)
                    count = int(np.count_nonzero(valid))
                    result['finite_pairs'] += count
                    if count:
                        delta = np.abs(fx[valid].astype(np.float64) - fy[valid].astype(np.float64))
                        result['max_abs_finite'] = max(result['max_abs_finite'], float(delta.max()))
                else:
                    fmt = '<f' if width == 4 else '<e'
                    for i, (u, v) in enumerate(zip(struct.iter_unpack(fmt, x), struct.iter_unpack(fmt, y))):
                        u, v = u[0], v[0]
                        result['different_elements'] += x[i * width:(i + 1) * width] != y[i * width:(i + 1) * width]
                        for p, value in enumerate((u, v)):
                            result['finite'][p] += math.isfinite(value)
                            result['nan'][p] += math.isnan(value)
                            result['inf'][p] += math.isinf(value)
                        if math.isfinite(u) and math.isfinite(v):
                            result['finite_pairs'] += 1
                            result['max_abs_finite'] = max(result['max_abs_finite'], abs(u - v))
            offset += n
        require(not fa.read(1) and not fb.read(1), f'raw length changed during read: {a.name}')
    result['bitwise_equal'] = result['different_bytes'] == 0
    if width:
        result['all_finite'] = result['finite'] == [size // width, size // width]
        if not result['finite_pairs']:
            result['max_abs_finite'] = None
    return result


def negative_result(folder, passes, log, mode):
    require(mode in REJECTIONS, 'unknown negative mode')
    require(COMPLETE not in log, 'negative control unexpectedly completed')
    rejects = re.findall(r'^P14_REPLAY REJECT (.+)$', log, re.MULTILINE)
    matches = [(reason, field) for reason in rejects for pattern, field in REJECTIONS[mode].items()
               if re.fullmatch(pattern, reason)]
    require(len(matches) == 1, 'missing or ambiguous expected negative rejection')
    reason, cutoff = matches[0]
    unexpected = [r for r in rejects if r != reason and not re.fullmatch(r'target not completed \(hit=1\)', r)]
    require(not unexpected, 'unrelated rejection: ' + repr(unexpected))
    names = list(passes[0])
    require(cutoff in names, 'negative pass0 missing affected stage')
    require(list(passes[1]) == names[:names.index(cutoff)], 'negative pass1 did not stop at affected guard')
    for name, row in passes[1].items():
        old = passes[0][name]
        require(row['bytes'] == old['bytes'] and row['guard'] == old['guard'], f'negative record mismatch: {name}')
    partial = folder / f'pass1-{cutoff}.bin'
    if reason.startswith('snapshot mismatch:'):
        require(partial.is_file() and 0 <= partial.stat().st_size <= passes[0][cutoff]['bytes'],
                'negative missing/invalid rejected raw file')
        sampled = partial.stat().st_size
        if sampled:
            proof = compare_prefix(folder / f'pass0-{cutoff}.bin', partial, sampled)
            require(proof, 'negative rejected raw bytes do not differ')
    else:
        require(not partial.exists(), 'negative validity failure happened after affected record write')
    allowed = {f'pass1-{name}.bin' for name in passes[1]}
    if partial.exists():
        allowed.add(partial.name)
    require({f.name for f in folder.glob('pass1-*.bin')} == allowed, 'negative has unexpected pass1 raw outputs')
    return {'reason': reason, 'affected_field': cutoff,
            'partial_bytes': partial.stat().st_size if partial.exists() else None,
            'limitation': 'REJECT may precede stdio flush; a zero-byte partial is not a retained byte-difference proof'}


def compare_prefix(a, b, size):
    with a.open('rb') as fa, b.open('rb') as fb:
        remaining = size
        different = False
        while remaining:
            n = min(CHUNK_BYTES, remaining)
            x, y = fa.read(n), fb.read(n)
            require(len(x) == len(y) == n, 'negative raw prefix changed')
            different |= x != y
            remaining -= n
        return different


def analyze(phase: Path, negative=None):
    phase = Path(phase)
    result = {'status': 'FAIL', 'phase': str(phase), 'negative': negative, 'issues': [], 'fields': [],
              'first_different_field': None, 'guard_differences': [], 'output_differences': [],
              'total_compared_bytes': 0, 'scope': 'p0=0,T=4090,layer=3,half=1; final logits are not an oracle'}
    try:
        run = json.loads((phase / 'RUN_RESULT.json').read_text())
        require(isinstance(run, dict) and 'native_error' in run and 'negative' in run, 'invalid RUN_RESULT')
        require(run['negative'] == negative, 'negative mode differs from RUN_RESULT')
        result['native_error'] = run['native_error']
        log = (phase / 'stderr.log').read_text(errors='replace')
        folder = phase / 'replay'
        passes = records(folder)
        check_files(folder, passes[0], 0)
        check_files(folder, passes[1], 1)
        require({f.name for f in folder.glob('pass0-*.bin')} == {f'pass0-{name}.bin' for name in passes[0]},
                'unexpected pass0 raw files')
        if negative:
            result['rejection'] = negative_result(folder, passes, log, negative)
            names = list(passes[1])
        else:
            if run['native_error'] not in (None, ''):
                result['issues'].append('native_error is not empty')
            require(COMPLETE in log and len([line for line in log.splitlines() if line.startswith(COMPLETE)]) == 1,
                    'missing or duplicate COMPLETE marker')
            require('P14_REPLAY REJECT ' not in log, 'positive phase has REJECT marker')
            require(list(passes[0]) == list(passes[1]), 'pass field set/order mismatch')
            expected = {f'pass{p}-{name}.bin' for p in (0, 1) for name in passes[p]}
            require({f.name for f in folder.glob('pass*-*.bin')} == expected, 'unexpected raw files')
            names = list(passes[0])
        for name in names:
            a, b = passes[0][name], passes[1][name]
            require(a['bytes'] == b['bytes'] and a['guard'] == b['guard'], f'pass length/guard mismatch: {name}')
            field = compare_files(folder / f'pass0-{name}.bin', folder / f'pass1-{name}.bin', a['bytes'], FLOAT_OUTPUTS.get(name))
            field.update(field=name, guard=a['guard'])
            result['fields'].append(field)
            result['total_compared_bytes'] += a['bytes']
            if not field['bitwise_equal']:
                if result['first_different_field'] is None:
                    result['first_different_field'] = name
                result['guard_differences' if a['guard'] else 'output_differences'].append(name)
        if result['guard_differences'] or result['output_differences']:
            result['issues'].append('completed raw fields differ')
        if not negative and any(not field.get('all_finite', True) for field in result['fields']):
            result['issues'].append('nonfinite float outputs')
        if not result['issues']:
            result['status'] = 'NEGATIVE_CONTROL_PASS' if negative else 'PASS'
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result['issues'].append(str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', type=Path)
    parser.add_argument('--negative', choices=tuple(REJECTIONS))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = analyze(args.phase, args.negative)
    target = args.output or args.phase / 'ANALYSIS.json'
    target.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'output': str(target), 'issues': result['issues']}))
    raise SystemExit(0 if result['status'] in ('PASS', 'NEGATIVE_CONTROL_PASS') else 2)


if __name__ == '__main__':
    main()
