"""Reproduce the direct valid-byte comparison of the retained original-layout A/A dumps."""
import argparse
import json
from pathlib import Path
import numpy as np
import analyze


def compare(task):
    a, b = (task / name for name in ('raw-a-1', 'raw-a-2'))
    names = sorted(f.name for f in (a/'diag').glob('*.bin'))
    if len(names) != 5 or names != sorted(f.name for f in (b/'diag').glob('*.bin')):
        raise ValueError('RAW_CHECKPOINT_COVERAGE_MISMATCH')
    result = {'files': {}, 'scope': 'original layout A, same diagnostic-v2 binary, no HC alias; direct valid-byte comparisons'}
    for name in names:
        f, g = a/'diag'/name, b/'diag'/name
        dtype = '<u2' if 'lo16' in name else '<u4'
        x, y = np.memmap(f, dtype=dtype, mode='r'), np.memmap(g, dtype=dtype, mode='r')
        if x.shape != y.shape:
            raise ValueError('RAW_SHAPE_MISMATCH')
        diff = x != y
        count = int(np.count_nonzero(diff))
        first = int(np.flatnonzero(diff)[0]) if count else None
        row = {'bytes': f.stat().st_size, 'element_bits': x.dtype.itemsize*8, 'elements': len(x),
               'bitwise_equal': count == 0, 'different_elements': count, 'first_index': first}
        if dtype == '<u4':
            xf, yf = x.view('<f4'), y.view('<f4')
            row['max_abs'] = float(np.max(np.abs(xf-yf)))
            row['first_values'] = [float(xf[first]), float(yf[first])] if first is not None else None
        result['files'][name] = row
    logs = [d/'stderr.log' for d in (a,b)]
    result['first_checkpoint_difference'] = analyze.first_checkpoint_difference(
        *(analyze.records(f, 'P13_HC_DIAG ') for f in logs))
    result['layer3_cpu'] = [next(x for x in analyze.records(f, 'P13_HC_CPU ') if x['layer'] == 3) for f in logs]
    result['logits'] = analyze.float_comparison((a/'think-4096.f32').read_bytes(), (b/'think-4096.f32').read_bytes())
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('task', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    args.output.write_text(json.dumps(compare(args.task), indent=2) + '\n')
