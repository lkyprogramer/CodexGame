
import json,sys,statistics as S,collections as C
d=sys.argv[1]
for c in ["burst","burstdh","burstdf","k7","k7dh","k7df"]:
    by=C.defaultdict(list); tot=0; n=0
    for l in open(f"{d}/{c}.rounds.jsonl"):
        r=json.loads(l); by[r["k"]].append(r["ms"]); tot+=r["ms"]; n+=1
    print(c, "rounds",n,"mean_ms %.3f"%(tot/n), " ".join("k%d:%.3f(n%d)"%(k,S.median(v),len(v)) for k,v in sorted(by.items())))
