import json, sys, statistics as st
from pathlib import Path
BD = Path(sys.argv[1])
M = ['d3k_tps', 'f10k_tps', 'c100k_tps', 'd3k_pf_ms', 'c32k_pf_ms', 'f10k_pf_ms', 'c100k_pf_ms']
SAME = {'B0', 'AM24K', 'NOAM'}
rows = []
for run in ('screen', 'chunk', 'mig'):
    f = BD / 'runs' / run / 'ANALYSIS.json'
    if f.exists():
        for r in json.loads(f.read_text()):
            r['run'] = run; rows.append(r)
ok = [r for r in rows if not r.get('failed')]
def q(v):
    v = sorted(v); n = len(v)
    return '%.1f [%.1f..%.1f]' % (st.median(v), v[n // 4], v[(3 * n) // 4]) if n >= 4 else '%.1f (%s)' % (st.median(v), '/'.join('%.1f' % x for x in v))
cls = {}
for r in ok: cls.setdefault('B0-config' if r['arm'] in SAME else r['arm'], []).append(r)
print('pooled medians [IQR]')
for k in ('A0', 'B0-config', 'AM32K'):
    rs = cls.get(k, [])
    print(k, len(rs))
    for m in M: print('   %-12s %s' % (m, q([x[m] for x in rs])))
    print('   hits(c100k) %s' % q([x['hits'][3] for x in rs]), ' accept(d3k) %s' % q([x['d3k_acc'] for x in rs]))
# A0 vs B0 pairs: screen rounds (A0 with same-round B0) + mig consecutive pairs
pairs = []
scr = [r for r in ok if r['run'] == 'screen']
def rnd(s): n = int(s.split('-')[0]); return 1 if n <= 9 else 2 if n <= 17 else 3
for k in (1, 2, 3):
    a = [r for r in scr if r['arm'] == 'A0' and rnd(r['stage']) == k]; b = [r for r in scr if r['arm'] == 'B0' and rnd(r['stage']) == k]
    if a and b: pairs.append((a[0], b[0]))
mig = sorted([r for r in ok if r['run'] == 'mig'], key=lambda r: r['stage'])
for i in range(0, len(mig) - 1, 2):
    x, y = mig[i], mig[i + 1]
    if {x['arm'], y['arm']} == {'A0', 'B0'}: pairs.append((x, y) if x['arm'] == 'A0' else (y, x))
print('\nA0/B0 ratio per pair (%d pairs): decode >1 = A0 faster; prefill ms >1 = A0 slower' % len(pairs))
for m in M:
    v = sorted(a[m] / b[m] for a, b in pairs)
    print('   %-12s median %.3f  min %.3f max %.3f  [%s]' % (m, st.median(v), v[0], v[-1], ' '.join('%.3f' % x for x in v)))
