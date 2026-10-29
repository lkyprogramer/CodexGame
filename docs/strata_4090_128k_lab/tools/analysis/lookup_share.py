"""Lookup (suffix) draft share per engine call, from serve engine logs (#4040 Gate A).

  python tools/analysis/lookup_share.py workspace/reports/chain/*/engine.log workspace/reports/session/*/engine.log

Each engine call logs `strata decode timing: ...`, then `strata serve: prompt ... N generated in M ms`, then (when the
call had suffix windows) `strata serve: suffix drafts: W windows, A of D drafts accepted` - per call, not cumulative.
The accepted suffix drafts over the generated tokens is the call's lookup share.  Calls with a share of 20% or more are
the ones a longer lookup window (#4040) could speed up; the script prints their share of the decode time.
Counter probes (<= 4 generated tokens) are skipped.
"""
import re,sys
SUF=re.compile(r"suffix drafts: (\d+) windows, (\d+) of (\d+) drafts accepted")
SRV=re.compile(r"strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+) read in \d+ ms.*?, (\d+) generated in (\d+) ms")
DEC=re.compile(r"strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window")
tot=dict(G=0,A=0,ms=0,hiG=0,hiA=0,hims=0,n=0,hin=0)
for f in sys.argv[1:]:
    cur=None; reqs=[]; dec=None
    for l in open(f,errors="replace"):
        m=DEC.search(l)
        if m: dec=(float(m.group(3)),float(m.group(4))); continue
        m=SRV.search(l)
        if m:
            cur=dict(prompt=int(m.group(1)),gen=int(m.group(4)),ms=int(m.group(5)),acc=0,dec=dec); reqs.append(cur); dec=None; continue
        m=SUF.search(l)
        if m and cur is not None: cur["acc"]=int(m.group(2))
    reqs=[r for r in reqs if r["gen"]>4]
    if not reqs: continue
    G=sum(r["gen"] for r in reqs); A=sum(r["acc"] for r in reqs); MS=sum(r["ms"] for r in reqs)
    hi=[r for r in reqs if r["acc"]/r["gen"]>=0.2]
    hG=sum(r["gen"] for r in hi); hA=sum(r["acc"] for r in hi); hMS=sum(r["ms"] for r in hi)
    tw=[f"{r['dec'][0]:.2f}" for r in hi if r["dec"]]
    name=f.split("/engine")[0]
    print(f"{name:42s} calls {len(reqs):2d} lookup {A/G:5.1%} | calls>=20%: {len(hi):2d}, their lookup {hA/max(hG,1):5.1%}, {hMS/MS:5.1%} of decode ms, tok/window {','.join(tw[:6])}")
    for k,v in dict(G=G,A=A,ms=MS,hiG=hG,hiA=hA,hims=hMS,n=len(reqs),hin=len(hi)).items(): tot[k]+=v
print(f"ALL: calls {tot['n']} lookup {tot['A']/tot['G']:.1%}; calls>=20%: {tot['hin']} lookup {tot['hiA']/max(tot['hiG'],1):.1%}, {tot['hims']/tot['ms']:.1%} of decode ms")
