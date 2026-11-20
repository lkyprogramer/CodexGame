import json, re, sys, statistics as st
from pathlib import Path
run = Path(sys.argv[1])
rows = []
for d in sorted(p for p in run.iterdir() if p.is_dir()):
    f = d / 'ROW.json'
    if not f.exists(): continue
    r = json.loads(f.read_text())
    if not r.get('legs') or len(r['legs']) < 4: rows.append(dict(stage=d.name, arm=r['arm'], failed=True, guard=r.get('exit', {}).get('guard'))); continue
    facts = '\n'.join(r.get('startup_facts', []))
    slog = (d / 'server.log').read_text(errors='replace')
    elog = (d / 'engine.log').read_text(errors='replace')
    g = lambda pat, s=facts: (re.search(pat, s) or [None, None])[1]
    hits = [float(x) for x in re.findall(r'expert cache ([0-9.]+)% hit', slog)]
    L = r['legs']; t = {k: v['timings'] for k, v in L.items()}
    row = dict(stage=d.name, arm=r['arm'], ready=round(r['ready_s'], 1),
               slots=g(r'expert cache (\d+) slots'), borrow=g(r'borrows (\d+) CUDA0'), free=g(r'(\d+) MiB of VRAM free with everything'),
               chunk=g(r'prompt chunk auto: (\d+)'),
               lm=';'.join(sorted(set(re.findall(r'layer-major[^\n]{0,90}', elog))))[:200],
               d3k_tps=t['d3k']['predicted_per_second'], f10k_tps=t['f10k']['predicted_per_second'], c100k_tps=t['c100k']['predicted_per_second'],
               d3k_acc=round(t['d3k'].get('draft_n_accepted', 0) / max(1, t['d3k'].get('draft_n', 1)), 3),
               d3k_pf_ms=t['d3k']['prompt_ms'], c32k_pf_ms=t['c32k']['prompt_ms'], f10k_pf_ms=t['f10k']['prompt_ms'], c100k_pf_ms=t['c100k']['prompt_ms'],
               f10k_cache=t['f10k']['cache_n'], c100k_ttft=round(L['c100k']['first_s'], 2), f10k_ttft=round(L['f10k']['first_s'], 2),
               hits=hits, finishes=[L[k]['finish'] for k in ('d3k', 'c32k', 'f10k', 'c100k')],
               swpout_mb=None)
    res = [json.loads(l) for l in (d / 'resources.jsonl').read_text().splitlines() if l.strip()]
    if res: row['swpout_mb'] = round((res[-1]['swpout'] - res[0]['swpout']) * 4 / 1024); row['load_max'] = max(x['load1'] for x in res); row['temp_max'] = max(x['temp'] for x in res)
    rows.append(row)
json.dump(rows, open(run / 'ANALYSIS.json', 'w'), indent=1)
M = ['d3k_tps', 'f10k_tps', 'c100k_tps', 'd3k_pf_ms', 'c32k_pf_ms', 'f10k_pf_ms', 'c100k_pf_ms']
ok = [r for r in rows if not r.get('failed')]
print('stages', len(rows), 'ok', len(ok), 'failed', [(r['stage'], r.get('guard')) for r in rows if r.get('failed')])
by = {}
for r in ok: by.setdefault(r['arm'], []).append(r)
print('%-7s n ' % 'arm' + ' '.join('%11s' % m for m in M) + '  slots free borrow chunk')
for a, rs in sorted(by.items()):
    print('%-7s %d ' % (a, len(rs)) + ' '.join('%11.1f' % st.median([x[m] for x in rs]) for m in M), ' ', rs[0]['slots'], rs[0]['free'], rs[0]['borrow'], rs[0]['chunk'])
# paired vs B0 by round (round = index of the B0 block: stage numbers 1-9 r1, 10-17 r2, 18-25 r3)
def rnd(stage):
    n = int(stage.split('-')[0]); return (n - 1) // 3 + 1
base = {rnd(r['stage']): r for r in ok if r['arm'] == 'B0'}
print('\nratio vs same-round B0 (decode: >1 faster; prefill ms: <1 faster)')
for a, rs in sorted(by.items()):
    if a == 'B0': continue
    rat = {m: [x[m] / base[rnd(x['stage'])][m] for x in rs if rnd(x['stage']) in base] for m in M}
    print('%-7s ' % a + ' '.join('%11s' % ('/'.join('%.3f' % v for v in rat[m])) for m in M))
