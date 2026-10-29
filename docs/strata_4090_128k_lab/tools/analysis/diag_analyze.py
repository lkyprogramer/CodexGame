"""Summarize a DIAG run: engine decode-timing lines (#1864 format) and STRATA_WINDOW_TRACE records (#3631)."""
import json, re, sys, statistics
from collections import defaultdict
from pathlib import Path

out, trace_path, tool_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(tool_dir))
from window_trace import read  # noqa: E402

rows = [json.loads(l) for l in (out / 'requests.jsonl').open()]
NUM = r'([\d.]+)'
dec = re.compile(r'strata decode timing: (\d+) windows, avg T ' + NUM + ', ' + NUM + r' tokens/window, ' + NUM +
                 r' ms/window = adapt wait ' + NUM + r' \+ verify ' + NUM + r' \(GPU-reach wait ' + NUM +
                 r' \+ per-layer host ' + NUM + r' \[plan ' + NUM + ' actq ' + NUM + ' jobs ' + NUM + ' CPU ' + NUM +
                 r'\] \+ stage ' + NUM + r'\) \+ commit/emit ' + NUM + r' \+ draft ' + NUM + r' \+ adapt join ' + NUM +
                 r' \+ other ' + NUM + r'.*?CPU experts ' + NUM + r' \(' + NUM + r' entries\), VRAM hits ' + NUM +
                 ', PCIe ' + NUM + r'.*?' + NUM + ' swaps/window')
KEYS = ('windows', 'avg_T', 'tok_per_win', 'ms', 'adapt_wait', 'verify', 'gpu_wait', 'host', 'plan', 'actq', 'jobs', 'cpu',
        'stage', 'commit', 'draft', 'join', 'other', 'cpu_experts_lw', 'entries_lw', 'vram_hits_lw', 'pcie_lw', 'swaps')

# One timing line per request, in request order within each round's log.
lines = []
for log in sorted(out.glob('round-*-cfg/engine.log')):
    rnd = int(log.parent.name.split('-')[1])
    ls = [dict(zip(KEYS, [int(m[1])] + [float(x) for x in m.groups()[1:]])) for m in map(dec.search, log.read_text(errors='replace').splitlines()) if m]
    reqs = [r for r in rows if r['round'] == rnd]
    # The engine also logs a line for tiny internal decodes; keep alignment only when counts match.
    lines.append({'round': rnd, 'n_lines': len(ls), 'n_requests': len(reqs), 'lines': ls})


def wavg(ls, key):
    w = sum(l['windows'] for l in ls)
    return sum(l['windows'] * l[key] for l in ls) / w if w else None


groups = defaultdict(list)
for blk in lines:
    reqs = [r for r in rows if r['round'] == blk['round']]
    extra = blk['n_lines'] - blk['n_requests']   # startup probes (validate_counter) log their own short lines first
    if extra >= 0:
        for r, l in zip(reqs, blk['lines'][extra:]):
            l = dict(l, case=r['case_id'], group=r['group'], prompt_tokens=r['metrics'].get('prompt_tokens'))
            groups[r['group']].append(l)
summary_lines = {g: {k: wavg([l for l in ls if l['windows'] >= 20], k) for k in KEYS[1:]} | {'windows': sum(l['windows'] for l in ls if l['windows'] >= 20)}
                 for g, ls in groups.items()}

# Window trace: records from every process appended to one file; req restarts at 0 for each process.
recs = read(trace_path)
F = ('total', 'pre', 'ram_adapt', 'tick', 'setup', 'run', 'commit', 'draft', 'join', 'wait', 'pool', 'jobs')
C = ('vram_hits', 'cpu_entries', 'cpu_misses', 'pcie', 'ram_reads', 'file_reads', 'file_bytes', 'gpu_swapped')


def agg(rs):
    n = len(rs)
    if not n:
        return None
    d = {'windows': n, 'T': sum(r['T'] for r in rs) / n, 'accepted': sum(r['accepted'] for r in rs) / n}
    d.update({k: sum(r[k] for r in rs) / n for k in F + C})
    tot = sorted(r['total'] for r in rs)
    d.update({f'p{int(q*100)}': tot[min(n - 1, int(q * n))] for q in (0.5, 0.9, 0.99)})
    d['max'] = tot[-1]
    return d


def bucket(pos):
    return '<8K' if pos < 8192 else '8-40K' if pos < 40960 else '40-80K' if pos < 81920 else '80K+'


steady = [r for r in recs if not (r['flags'] & 3)]   # drop first / prompt-merged windows
by_T = {T: agg([r for r in steady if r['T'] == T]) for T in sorted({r['T'] for r in steady})}
by_pos = {b: agg([r for r in steady if bucket(r['pos']) == b]) for b in ('<8K', '8-40K', '40-80K', '80K+')}
first = agg([r for r in recs if r['flags'] & 1])
slow = sorted(steady, key=lambda r: -r['total'])[:10]
json.dump({'timing_lines': {'per_round': [{k: v for k, v in b.items() if k != 'lines'} for b in lines],
                            'by_group': summary_lines},
           'trace': {'records': len(recs), 'steady': len(steady), 'all': agg(steady), 'by_T': by_T, 'by_pos': by_pos,
                     'first_windows': first,
                     'slowest': [{k: r[k] for k in ('req', 'win', 'T', 'accepted', 'flags', 'pos', 'total', 'pre', 'run', 'commit', 'draft', 'join', 'cpu_entries', 'pcie', 'file_reads', 'gpu_swapped')} for r in slow]}},
          sys.stdout, indent=1, default=str)
