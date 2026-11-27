#!/usr/bin/env python3
"""T21 draft-precision arm, client: one greedy 512-token /completion per workload prompt against a
llama-server with a DSpark draft; records the server's draft counts and decode speed.
usage: t21_llama_acc.py <base url> <ids.json> <label> <out.jsonl>"""
import json
import sys
import urllib.request

base, ids_file, label, out = sys.argv[1:5]
ids = json.load(open(ids_file))


def run(x):
    body = {"prompt": x["ids"], "n_predict": 512, "temperature": 0, "ignore_eos": True, "cache_prompt": False}
    req = urllib.request.Request(base + "/completion", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=900))


run(ids[0])  # warm-up
with open(out, "w") as f:
    for x in ids:
        t = run(x)["timings"]
        r = {"label": label, "set": x["set"], "case": x["case"], "n": t.get("predicted_n"), "draft_n": t.get("draft_n"), "draft_acc": t.get("draft_n_accepted"), "tps": t.get("predicted_per_second")}
        f.write(json.dumps(r) + "\n"); f.flush()
        print(label, x["set"], x["case"], r["draft_n"], r["draft_acc"], "%.1f" % (r["tps"] or 0), flush=True)
