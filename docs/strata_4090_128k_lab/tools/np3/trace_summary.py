"""Summarise STRATA_LAB_NP3_TRACE output (tools/np3/trace_patch.py) from engine stderr logs.

  python tools/np3/trace_summary.py workspace/np3/tk-48.err [more.err ...] [--json out.json]

Per log it takes the last block of trace lines (`final` when the pool was destroyed, else the last `periodic`) and
splits each native row phase (gate/up = gu, down = dn, by experts in the phase) into:
  sync    host pre + pub + repark (+ gap on down phases: the serial quantize between the two phases)
  lag     publish -> a thread's first claim, mean over threads
  rows    rows time per thread (busy / threads)
  claims  mean last-task end - first claim - rows per thread (the claims after the first)
  tail    publish -> wait_done returned, minus the mean last-task end
`in-task GB/s` is the phase's bytes over the rows time per thread: the rate while the threads are inside tasks.
The matching `.out` file (same stem), when present, gives the generate-mode pool / decode summary lines.
"""
import json, re, sys
from pathlib import Path

NUM = r'([-0-9.]+)'
FIELDS = {
    'phases': r'phases=(\d+)', 'pre': r'pre ' + NUM, 'pub': r'pub ' + NUM, 'done': r'done ' + NUM,
    'repark': r'repark ' + NUM, 'gap': r'gap ' + NUM, 'wake': r'wake ' + NUM, 'first': r'first ' + NUM,
    'finish': r'finish ' + NUM, 'exit': r'exit ' + NUM, 'busy': r'busy/phase ' + NUM, 'util': r'util ' + NUM,
    'task': r'task ' + NUM, 'claim': r'claim ' + NUM, 'tasks': r'tasks/phase ' + NUM, 'host': r'host ' + NUM,
    'idle': r'idle ' + NUM, 'experts': r'experts/phase ' + NUM, 'nt': r'nt/expert ' + NUM, 'mb': r'MB/phase ' + NUM,
}


def parse(path):
    lines = Path(path).read_text(errors='replace').splitlines()
    workers = None
    for l in lines:
        m = re.search(r'LAB_NP3_TRACE enabled=1 every=\d+ workers=(\d+)', l)
        if m: workers = int(m.group(1))
    trace = [l for l in lines if l.startswith('LAB_NP3_TRACE ') and 'enabled=' not in l]
    if not trace: return None
    why = 'final' if any(l.startswith('LAB_NP3_TRACE final ') for l in trace) else 'periodic'
    block = [l for l in trace if l.startswith('LAB_NP3_TRACE ' + why + ' ')]
    # each print ends with its threads line: keep the last print
    idx = [i for i, l in enumerate(block) if ' threads(' in l]
    if len(idx) >= 2: block = block[idx[-2] + 1:]
    kinds = {}
    for l in block:
        if ' threads(' in l: continue
        name = l.split()[2]
        kinds[name] = {k: float(re.search(rx, l).group(1)) for k, rx in FIELDS.items()}
    out = {}
    p = Path(path).with_suffix('.out')
    if p.exists():
        t = p.read_text(errors='replace')
        for key, rx in (('pool_ms', r'CPU pool call ' + NUM), ('gu_ms', r'gate/up ' + NUM), ('q_ms', r'quantize ' + NUM),
                        ('dn_ms', r'down ' + NUM + r' ms/round'), ('tok_s', r'->\s+' + NUM + r' tok/s'),
                        ('distinct', r'CPU experts ' + NUM + r' distinct'), ('rows_gbs', NUM + r' GB/s over the rows'),
                        ('rounds', r'speculation\s+(\d+) rounds'), ('tok_round', NUM + r' tokens per round'),
                        ('rings_ms', r'wait for rings ' + NUM), ('decode_ms', r'decode\s+\d+ tokens in ' + NUM),
                        ('pcie_distinct', r'pcie experts\s+' + NUM), ('pcie_share', r'share (\d+)/256')):
            m = re.search(rx, t)
            if m: out[key] = float(m.group(1))
        if out.get('rounds') and out.get('decode_ms'): out['ms_round'] = out['decode_ms'] / out['rounds']
    return {'file': str(path), 'why': why, 'threads': (workers or 15) + 1, 'kinds': kinds, 'gen': out}


def split(k, threads):
    rows = k['busy'] / threads
    sync = k['pre'] + k['pub'] + k['repark'] + k['gap']
    claims = max(0.0, k['finish'] - k['first'] - rows)
    return {'sync': sync, 'lag': k['first'], 'rows': rows, 'claims': claims, 'tail': k['done'] - k['finish'],
            'total': k['pre'] + k['pub'] + k['done'] + k['repark'] + k['gap'],
            'gbs_in_task': k['mb'] * 1e3 / rows if rows else 0.0}


def main(argv):
    js = None
    if '--json' in argv:
        i = argv.index('--json'); js = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    res = []
    for f in argv:
        r = parse(f)
        if r is None:
            print(f'{f}: no trace lines'); continue
        res.append(r)
        th = r['threads']
        g = r['gen']
        print(f"## {Path(f).name} ({r['why']}, {th} threads)" + (
            f"  pool {g.get('pool_ms')} ms/round = gu {g.get('gu_ms')} + q {g.get('q_ms')} + dn {g.get('dn_ms')}; "
            f"{g.get('distinct')} distinct/layer; {g.get('tok_s')} tok/s" if g else ''))
        if g.get('ms_round'):
            print(f"   round {g['ms_round']:.2f} ms ({g.get('tok_round')} tok/round, {g['ms_round'] / g['tok_round']:.3f} ms/token);"
                  f" rings {g.get('rings_ms')} ms; PCIe {g.get('pcie_distinct')} distinct/layer, share {g.get('pcie_share')}/256")
        print('kind   phases  exp   nt    MB    total  sync   lag   rows  claims  tail  util  task  claim  tasks  inGB/s')
        agg = {}
        for name, k in r['kinds'].items():
            s = split(k, th)
            print(f"{name:5s} {int(k['phases']):7d} {k['experts']:4.2f} {k['nt']:4.2f} {k['mb']:5.3f} {s['total']:7.2f}"
                  f" {s['sync']:5.2f} {s['lag']:5.2f} {s['rows']:6.2f} {s['claims']:5.2f} {s['tail']:6.2f} {k['util']:5.3f}"
                  f" {k['task']:5.2f} {k['claim']:5.3f} {k['tasks']:5.1f} {s['gbs_in_task']:6.2f}")
            fam = name[:2]
            if fam not in ('gu', 'dn'): continue
            a = agg.setdefault(fam, {x: 0.0 for x in ('phases', 'experts', 'mb', 'total', 'sync', 'lag', 'rows', 'claims', 'tail')})
            w = k['phases']
            a['phases'] += w; a['experts'] += w * k['experts']; a['mb'] += w * k['mb']
            for x in ('total', 'sync', 'lag', 'rows', 'claims', 'tail'): a[x] += w * s[x]
        if 'gu' in agg and 'dn' in agg:
            # per expert, both phases: where a CPU miss's time goes
            ex = agg['gu']['experts']
            parts = {x: (agg['gu'][x] + agg['dn'][x]) / ex for x in ('total', 'sync', 'lag', 'rows', 'claims', 'tail')}
            mb = (agg['gu']['mb'] + agg['dn']['mb']) / ex
            print('per expert (gu + dn, phase-weighted): ' + '  '.join(f'{x} {v:.2f}' for x, v in parts.items()) +
                  f' us; {mb:.3f} MB; in-task {mb * 1e3 / parts["rows"]:.2f} GB/s; whole phase {mb * 1e3 / parts["total"]:.2f} GB/s')
            r['per_expert'] = dict(parts, mb=mb)
        print()
    if js: Path(js).write_text(json.dumps(res, indent=1))


if __name__ == '__main__':
    main(sys.argv[1:])
