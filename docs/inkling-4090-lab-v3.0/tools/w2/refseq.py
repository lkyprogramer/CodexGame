"""Greedy reference sequences from llama-server for V5/V6/V7 (prompts: W1 V2 chat-template ids)."""
import json, sys, urllib.request
base, prompts, outdir, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
items = json.load(open(prompts))
res = []
for i, it in enumerate(items):
    body = {"prompt": it["ids"], "n_predict": n, "temperature": 0, "top_k": 1, "cache_prompt": False,
            "return_tokens": True, "n_probs": 2, "ignore_eos": True}
    r = json.loads(urllib.request.urlopen(urllib.request.Request(base + "/completion", data=json.dumps(body).encode(),
                   headers={"Content-Type": "application/json"}), timeout=600).read())
    gen = r["tokens"]
    margins, top1 = [], []
    for cp in r["completion_probabilities"]:
        tl = cp["top_logprobs"]
        margins.append(tl[0]["logprob"] - tl[1]["logprob"] if len(tl) > 1 else None)
        top1.append(tl[0]["id"])   # raw argmax; differs from gen only where ignore_eos banned an EOG token
    seq = it["ids"] + gen
    open(f"{outdir}/{i:02d}.ids", "w").write(" ".join(map(str, seq)))
    res.append({"i": i, "plen": len(it["ids"]), "gen": gen, "ref_margin": margins, "ref_top1": top1, "tps": r["timings"]["predicted_per_second"]})
json.dump(res, open(f"{outdir}/ref.json", "w"))
print("ok", len(res))
