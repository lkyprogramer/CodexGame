import json,glob
mt=0;ma=10**9;ms=0;n=0
for f in glob.glob("runs/mig17/*/*/resources.jsonl"):
    prev=None
    for l in open(f):
        s=json.loads(l); n+=1
        mt=max(mt,s["temp"]); ma=min(ma,s["avail_mib"])
        if prev: ms=max(ms,s["swpin"]-prev["swpin"])
        prev=s
print("samples",n,"max_temp",mt,"min_avail",ma,"max_swpin_2s",ms)
for m in ("seq","quality"):
    r=json.load(open("runs/mig17/%s/RESULT.json"%m)); print(m,r["error"],r["n"],r["protected_changed"],repr(r["listeners"]),r["final"]["gpu_used"],r["final"]["units"])
for f in sorted(glob.glob("runs/mig17/*/*/ROW.json")):
    e=json.load(open(f))["exit"]
    if e["guard"] or e.get("leftover") or e["ports"]: print("BAD",f,e)
