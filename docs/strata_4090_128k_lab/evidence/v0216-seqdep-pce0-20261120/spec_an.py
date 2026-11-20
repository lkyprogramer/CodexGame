import sys, json, glob, statistics as st
from pathlib import Path
def parse(path):
    reqs = []; cur = None
    for l in open(path, errors='replace'):
        if l.startswith('# request prompt'):
            cur = dict(prompt=int(l.split()[3]), rounds=[]); reqs.append(cur); continue
        if not l.startswith('R ') or cur is None: continue
        parts = l.rstrip('\n').split('|')
        h = parts[0].split()
        probs = [float(x) for x in parts[1].split()] if len(parts) > 1 else []
        cur['rounds'].append(dict(p=int(h[1]), T=int(h[2]), a=int(h[3]), sfx=int(h[4]), ms=float(h[5]), k=int(h[6]), m=int(h[7]), probs=probs))
    return reqs
def summ(rs):
    if not rs: return None
    n = len(rs); mtp = [r for r in rs if not r['sfx']]; sx = [r for r in rs if r['sfx']]
    def m(x): return round(st.mean(x), 3) if x else None
    return dict(n=n, T=m([r['T'] for r in rs]), tok=m([r['a'] + 1 for r in rs]), ms=m([r['ms'] for r in rs]),
                sfx_frac=round(len(sx) / n, 3), sfx_T=m([r['T'] for r in sx]), sfx_tok=m([r['a'] + 1 for r in sx]),
                mtp_T=m([r['T'] for r in mtp]), mtp_tok=m([r['a'] + 1 for r in mtp]),
                p1=m([r['probs'][0] for r in mtp if r['probs']]), p2=m([r['probs'][1] for r in mtp if len(r['probs']) > 1]),
                k_pos=round(sum(1 for r in rs if r['k'] > 0) / n, 3))
out = {}
for d in sorted(glob.glob(sys.argv[1] + '/[0-9]*')):
    f = Path(d) / 'spec.trace'
    if not f.exists(): continue
    reqs = parse(f)
    out[Path(d).name] = [dict(prompt=r['prompt'], **(summ(r['rounds']) or {})) for r in reqs]
json.dump(out, open(sys.argv[1] + '/SPEC_SUMMARY.json', 'w'), indent=1)
for k, v in out.items():
    print(k)
    for r in v: print('  ', r)
