#!/usr/bin/env python3
"""T43 Phase 0-A summary: per workload set, acceptance rate, mean accepted drafts per round (rounds =
draft_n / 7, every round drafts 7 at --spec-draft-n-max 7 without p-min), tok/s, and how many outputs
equal the no-draft arm's tokens. usage: t43_summary.py <run dir>"""
import json, os, statistics as st, sys

O = sys.argv[1]
arms = [a for a in ("none", "dspark", "dflash2-q8_0", "dflash2-bf16") if os.path.exists(os.path.join(O, a + ".jsonl"))]
rows = {a: [json.loads(l) for l in open(os.path.join(O, a + ".jsonl"))] for a in arms}
base = {(r["set"], r["case"]): r["tok_sha"] for r in rows.get("none", [])}
res = {}
print("%-13s" % "" + "".join("%34s" % s for s in ("sn", "sc", "ln", "lc", "all")))
for a, rs in rows.items():
    out, res[a] = [], {}
    for s in ("sn", "sc", "ln", "lc", None):
        x = [r for r in rs if s is None or r["set"] == s]
        dn, da = sum(r["draft_n"] or 0 for r in x), sum(r["draft_acc"] or 0 for r in x)
        acc_len = da / (dn / 7) if dn else 0.0
        tps = st.mean(r["tps"] for r in x)
        same = sum(base.get((r["set"], r["case"])) == r["tok_sha"] for r in x)
        res[a][s or "all"] = {"acc_rate": da / dn if dn else None, "acc_len": acc_len, "tps": tps, "same_as_none": same, "n": len(x)}
        out.append("%5.3f L%5.2f %6.1f t/s %2d/%-2d" % (da / dn if dn else 0, acc_len, tps, same, len(x)))
    print("%-13s" % a + "".join("%34s" % v for v in out))
if "dspark" in res:
    for a in [a for a in res if a.startswith("dflash2")]:
        print(a, "/ dspark acc_len ratio:", {s: round(res[a][s]["acc_len"] / res["dspark"][s]["acc_len"], 3) if res["dspark"][s]["acc_len"] else None for s in res[a]},
              "tps ratio:", {s: round(res[a][s]["tps"] / res["dspark"][s]["tps"], 3) for s in res[a]})
json.dump(res, open(os.path.join(O, "summary.json"), "w"), indent=1)
