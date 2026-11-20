"""Analysis for mig17 seq: per-stage legs, c100k decode windows, tail-skip counts, c100k trajectories."""
import glob, json, re, statistics as st, sys
from pathlib import Path
RUN = Path(sys.argv[1]); OLD = Path('/data/strata-data/v0216-baseline-20261120/runs/seqtrace')
rx = re.compile(r'decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = .*?GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+) \[.*?CPU ([\d.]+)\].*?draft ([\d.]+).*?CPU experts ([\d.]+) \(([\d.]+) entries\), VRAM hits ([\d.]+), PCIe ([\d.]+)')
K = ('windows', 'avgT', 'tok_win', 'ms_win', 'reach', 'host', 'cpu', 'draft', 'cpu_exp', 'cpu_ent', 'vram', 'pcie')
skip = re.compile(r'route tail skip: (\d+) missed experts skipped \((\d+) entries\)')
def text(sse):
    out = []
    for l in open(sse, 'rb'):
        if not l.startswith(b'data:') or l[5:].strip() == b'[DONE]': continue
        try: it = json.loads(l[5:])
        except ValueError: continue
        for ch in it.get('choices', []):
            dl = ch.get('delta', {}); out.append((dl.get('reasoning_content') or '') + (dl.get('content') or ''))
    return ''.join(out)
rows = []
for d in sorted(p for p in RUN.iterdir() if p.is_dir() and p.name[:2].isdigit()):
    _, arm, kind = d.name.split('-')
    row_f = d / 'ROW.json'
    if not row_f.exists(): continue
    row = json.loads(row_f.read_text()); el = (d / 'engine.log').read_text(errors='replace')
    L = [dict(zip(K, map(float, m.groups()))) for m in map(rx.search, el.splitlines()) if m]
    sk = [tuple(map(int, m.groups())) for m in map(skip.search, el.splitlines()) if m]
    exp = 8 if kind == 'S' else 2
    assert len(L) >= exp - 2, (d.name, len(L))
    seg = L[4:6] if kind == 'S' else L[0:2]
    legs = {k: dict(tps=(v.get('timings') or {}).get('predicted_per_second'), prompt_ms=(v.get('timings') or {}).get('prompt_ms'),
                    cache_n=(v.get('timings') or {}).get('cache_n'), acc=round((v['timings']['draft_n_accepted'] / v['timings']['draft_n']), 3) if (v.get('timings') or {}).get('draft_n') else None)
            for k, v in row['legs'].items()}
    for s in seg: s['cpu_per_ent'] = round(s['cpu'] / s['cpu_ent'], 3) if s['cpu_ent'] else None
    rows.append(dict(stage=d.name, arm=arm, kind=kind, n_timing=len(L), legs=legs, c100k_seg=seg, skip_last=sk[-1] if sk else None,
                     skip_on='STRATA_ROUTE_TAIL_SKIP=7 is ON' in el, c100k_head=text(d / 'c100k.sse')[:400]))
# trajectories (first 400 chars), including the v0.2.16 seqtrace fresh B0/A0 texts for reference
ref = {}
for d in sorted(OLD.glob('*-F')):
    ref[d.name] = text(d / 'c100k.sse')[:400]
heads = {}
for r in rows: heads.setdefault(r['c100k_head'], []).append(r['stage'])
for k, v in ref.items(): heads.setdefault(v, []).append('v0216:' + k)
traj = sorted(heads.values(), key=lambda v: -len(v))
def med(x): x = [y for y in x if y is not None]; return round(st.median(x), 3) if x else None
summ = {}
for arm in ('B1', 'B2', 'TS0'):
    for kind in ('S', 'F'):
        R = [r for r in rows if r['arm'] == arm and r['kind'] == kind]
        if not R: continue
        s = dict(n=len(R), c100k_tps=[r['legs']['c100k']['tps'] for r in R])
        for i in range(2):
            for f in ('avgT', 'tok_win', 'ms_win', 'reach', 'host', 'cpu', 'cpu_ent', 'cpu_per_ent', 'vram', 'pcie', 'draft'):
                s['seg%d_%s' % (i + 1, f)] = med([r['c100k_seg'][i][f] for r in R if len(r['c100k_seg']) > i])
        if kind == 'S':
            for leg in ('d3k', 'c32k', 'f10k', 'c100k', 'fork60', 'fork90'):
                s[leg + '_tps'] = med([r['legs'][leg]['tps'] for r in R]); s[leg + '_prompt_ms'] = med([r['legs'][leg]['prompt_ms'] for r in R])
                s[leg + '_cache_n'] = sorted({r['legs'][leg]['cache_n'] for r in R})
        else:
            s['c100k_prompt_ms'] = med([r['legs']['c100k']['prompt_ms'] for r in R])
        s['skip_on'] = sorted({r['skip_on'] for r in R}); s['skip_entries_last'] = [r['skip_last'][1] if r['skip_last'] else 0 for r in R]
        summ['%s-%s' % (arm, kind)] = s
json.dump(dict(rows=rows, summary=summ, trajectories=traj), open(RUN / 'ANALYSIS.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(summ, indent=1)); print('TRAJ', json.dumps(traj))
