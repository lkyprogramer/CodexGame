"""Static sm89 table delta inventory; no inference about runtime hit or benefit."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re


def parse_table(source, name):
    clean = re.sub(r'//[^\n]*|/\*.*?\*/', '', source, flags=re.S)
    match = re.search(r'\b' + re.escape(name) + r'\[\]\s*=\s*\{', clean)
    if not match:
        raise ValueError('TABLE_NOT_FOUND: ' + name)
    start = match.end() - 1
    depth = 0
    for end in range(start, len(clean)):
        depth += (clean[end] == '{') - (clean[end] == '}')
        if depth == 0:
            raw = clean[start:end + 1].replace('{', '[').replace('}', ']')
            rows = json.loads(re.sub(r',\s*]', ']', raw))
            result = {}
            for type_id, values in rows:
                if type_id in result:
                    raise ValueError('DUPLICATE_TYPE')
                result[type_id] = values
            return result
    raise ValueError('UNTERMINATED_TABLE')


def parse_old_override(report):
    values = re.findall(r'^STRATA_MMVQ_IL_ROWS=([^\n`]+)', report, re.M)
    if len(values) != 1:
        raise ValueError('OLD_OVERRIDE_NOT_UNIQUE')
    result = {}
    for cell in values[0].split(';'):
        tid, nc, text = cell.split(':')
        rows = [int(x) for x in text.split(',')]
        if len(rows) != 5 or any(x not in (0, 1, 2, 4) for x in rows):
            raise ValueError('INVALID_OVERRIDE')
        key = (int(tid), int(nc))
        if key in result:
            raise ValueError('DUPLICATE_OVERRIDE')
        result[key] = rows
    return result


def row_class(n_out):
    return sum(n_out >= x for x in (2048, 4096, 8192, 12288))


def rows_for(table, single, type_id, ncols, n_out):
    if ncols < 1 or ncols > 4:
        return 0  # sm89 has no 5..8-column table
    cls = row_class(n_out)
    if ncols == 1:
        return single.get(type_id, [0] * 5)[cls]
    return table.get(type_id, [[0] * 5 for _ in range(3)])[ncols - 2][cls]


def classification(base, candidate, old):
    if base == candidate:
        return 'unchanged'
    if candidate == old:
        return 'changed_but_old_candidate_reused'
    return 'changed_not_covered_by_old_override'


def inventory(source, tensors, report):
    shared = parse_table(source, 'kIlRowsShared')
    ada = parse_table(source, 'kIlRows_89')
    single = parse_table(source, 'kIl1Rows_89')
    override = parse_old_override(report)
    for name, table, columns in [('shared', shared, 3), ('ada', ada, 3)]:
        for values in table.values():
            if len(values) != columns or any(len(v) != 5 for v in values):
                raise ValueError('INVALID_TABLE_SHAPE: ' + name)
    if any(len(v) != 5 for v in single.values()):
        raise ValueError('INVALID_SINGLE_TABLE')
    shapes = defaultdict(list)
    for name, tensor in tensors.items():
        if len(tensor['shape']) == 2:
            shapes[(tensor['type_id'], tensor['type'], *tensor['shape'])].append(name)
    cells = []
    for (tid, dtype, n_in, n_out), names in sorted(shapes.items()):
        for nc in range(1, 9):
            base = rows_for(shared, {}, tid, nc, n_out)
            candidate = rows_for(ada, single, tid, nc, n_out)
            old = override[(tid, nc)][row_class(n_out)] if (tid, nc) in override else base
            cells.append({'type_id': tid, 'dtype': dtype, 'n_in': n_in, 'n_out': n_out,
                          'ncols': nc, 'base_rows': base, 'new_rows': candidate,
                          'old_experiment_rows': old, 'tensor_count': len(names),
                          'tensors': sorted(names), 'classification': classification(base, candidate, old)})
    counts = Counter(c['classification'] for c in cells)
    changed = [c for c in cells if c['base_rows'] != c['new_rows']]
    return {'scope': 'static 2D tensor/table candidates only; not runtime eligibility/hit or benefit',
            'assumptions': ['sm89; explicit IL89=0 vs1; no user IL_ROWS override',
                            'g_multi_exact=true is a separate runtime prerequisite',
                            'Q3_K/T1/WIDE enable gates retain defaults; sm89 has no wide table',
                            'historical old rows use archived override; absent cells use current shared fallback'],
            'runtime_hit_established': False, 'tables': {'shared': shared, 'ada': ada, 'single_ada': single},
            'old_override': {f'{t}:{n}': r for (t, n), r in sorted(override.items())},
            'two_dimensional_tensor_count': sum(len(v) for v in shapes.values()),
            'unique_shapes': len(shapes), 'classification_counts': dict(counts),
            'changed_shape_cells': len(changed),
            'changed_tensor_cells': sum(c['tensor_count'] for c in changed),
            'changed_cells': changed, 'all_cells': cells}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--tensors', type=Path, required=True)
    p.add_argument('--old-report', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('output exists; preserve prior evidence')
    result = inventory(a.source.read_text(), json.loads(a.tensors.read_text()), a.old_report.read_text())
    result['input_sha256'] = {str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                              for f in (a.source, a.tensors, a.old_report)}
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['classification_counts', 'changed_shape_cells', 'changed_tensor_cells']}))
