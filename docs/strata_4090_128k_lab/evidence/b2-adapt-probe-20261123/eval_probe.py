import json, glob, os, re, sys
W = '/data/strata-data/upgrade-gate/b2-adapt-20261123'
REF = dict(ms_win=14.55, e2e=130.6)
docs = {}
for p in sorted(glob.glob(W + '/SMOKE-*.json')):
    d = json.load(open(p)); docs[d['arm']] = d
if not docs: sys.exit('no SMOKE files yet')
last = max(docs.values(), key=lambda d: os.path.getmtime(W + '/SMOKE-%s.json' % d['arm']))
def fig(arm):
    key = 'smoke:' + arm if arm != 'b2' else 'b2'
    for d in [docs.get(arm), last]:
        if d and key in d['per_window_same_tasks']:
            a = d['per_window_same_tasks'][key]
            return dict(e2e=d['speed_same_tasks'][key]['tok_s'], **{k: a['all'].get(k) for k in ('ms_win','tok_win','accept','reach','cpu_ms','cpu_entries','swaps','adapt_join','draft','requests','windows','unaligned_attempts','whole_log','overlap_wait_ms_per_window','decode_tok_s')},
                        lt4k=a.get('<4K', {}).get('ms_win'), k4_32=a.get('4K-32K', {}).get('ms_win'))
    return None
arms = ['b2'] + [a for a in ('b2-control','b2-adaptevery2','b2-adaptdecay092','b2-expertprofileprofileb2armlearned','b2-adaptevery2-adaptdecay092') if a in docs]
F = {a: fig(a) for a in arms}
for a in arms: print(a, json.dumps(F[a]))
for a in arms[1:]:
    d = docs[a]; print(a, 'passes', d['passes'], 'args', d.get('args'), 'not_in_help', d.get('flags_not_in_help'))
    lg = '%s/smoke/arms/%s/engine.log' % (W, a)
    if os.path.exists(lg):
        txt = open(lg, errors='replace').read()
        print('  log lines:', [l[:160] for l in txt.splitlines() if re.search(r'adapt|profile', l, re.I) and not re.search(r'decode timing|request', l)][:8])
c = F.get('b2-control')
if not c: sys.exit()
aa = abs(c['ms_win'] - REF['ms_win']) / REF['ms_win']; de = abs(c['e2e'] - REF['e2e']) / REF['e2e']
print('C0: AA=%.4f e2e_dev=%.4f -> %s' % (aa, de, 'STOP_ENV' if aa > 0.05 or de > 0.05 else 'ENV_OK'))
thr = c['ms_win'] * (1 - max(0.04, 2 * aa)); print('pass threshold ms_win <= %.3f' % thr)
for a in arms[2:]:
    f = F[a]; imp = 1 - f['ms_win'] / c['ms_win']; tw = abs(f['tok_win'] / c['tok_win'] - 1)
    v = 'INCONCLUSIVE' if tw > 0.05 else ('PASS' if f['ms_win'] <= thr and f['e2e'] > c['e2e'] else 'NO_PASS')
    extra = ''
    if a == 'b2-adaptevery2': extra = ' swaps_ratio=%.2f %s' % (f['swaps'] / c['swaps'], 'VALID' if f['swaps'] >= 1.5 * c['swaps'] else 'INVALID')
    print('%s: ms_win %.3f (%+.1f%%) e2e %.1f vs %.1f tok_win_dev %.3f -> %s%s' % (a, f['ms_win'], -100 * imp, f['e2e'], c['e2e'], tw, v, extra))
