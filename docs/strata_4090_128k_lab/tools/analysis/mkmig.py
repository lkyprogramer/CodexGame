import json,copy,sys
sys.path.insert(0,".")
from lab.core import hash_obj, dump
src=json.load(open("workspace/corpora/full-26232b9ef354.json"))
keep={"quality","tool","protocol","decode","cold-prefill","long-retrieval"}
cases=[x for x in src["cases"] if x["group"] in keep]
ex=[x for x in cases if x["group"]=="decode"][0]
print("perf body keys:",sorted(k for k in ex["body"] if k!="messages"),"case keys:",sorted(ex))
extra=[]
for x in cases:
    if x["group"] in ("decode","cold-prefill"):
        y=copy.deepcopy(x); y["id"]=x["id"]+"-sampled"; y["group"]=x["group"]+"-sampled"
        y["body"].update({"temperature":1.0,"top_p":0.95,"top_k":20}); y["request_sha256"]=hash_obj(y["body"])
        extra.append(y)
out=dict(src); out["cases"]=cases+extra; out["corpus_sha256"]=hash_obj(out["cases"])
out["derived_from"]=src["corpus_sha256"]; out["purpose"]="MIG: P vs A0; sampled copies use Pi sampling (1.0/0.95/20)"
p="workspace/corpora/mig-%s.json"%out["corpus_sha256"][:12]; dump(p,out)
print(p,len(out["cases"]))
