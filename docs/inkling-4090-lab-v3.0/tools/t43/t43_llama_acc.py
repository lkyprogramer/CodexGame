#!/usr/bin/env python3
"""T43 Phase 0 client: one greedy 512-token /completion per T21 workload prompt against a llama-server
(with or without a draft); records draft counts, decode speed and the SHA-256 of the generated tokens
(sanity: with greedy verification every arm must produce the no-draft tokens, up to near-tie flips).
usage: t43_llama_acc.py <base url> <ids.json> <label> <out.jsonl>"""
import hashlib, json, sys, urllib.request

base, ids_file, label, out = sys.argv[1:5]
ids = json.load(open(ids_file))


def run(x):
    body = {"prompt": x["ids"], "n_predict": 512, "temperature": 0, "ignore_eos": True, "cache_prompt": False, "return_tokens": True}
    req = urllib.request.Request(base + "/completion", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=900))


run(ids[0])  # warm-up
with open(out, "w") as f:
    for x in ids:
        js = run(x)
        t = js["timings"]
        toks = js.get("tokens") or []
        r = {"label": label, "set": x["set"], "case": x["case"], "n": t.get("predicted_n"), "draft_n": t.get("draft_n"),
             "draft_acc": t.get("draft_n_accepted"), "tps": t.get("predicted_per_second"),
             "tok_sha": hashlib.sha256(json.dumps(toks).encode()).hexdigest()[:16], "tokens": toks,
             "timings": {k: v for k, v in t.items() if "draft" in k}}
        f.write(json.dumps(r) + "\n"); f.flush()
        print(label, x["set"], x["case"], r["draft_n"], r["draft_acc"], "%.1f" % (r["tps"] or 0), flush=True)
