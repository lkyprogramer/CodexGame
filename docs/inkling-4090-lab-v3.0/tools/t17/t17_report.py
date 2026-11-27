#!/usr/bin/env python3
"""T17 stage 3-4 summary: V4 at 16K / 32K against N0 on the same file, the perplexity ladder,
prefill vs decode, the probes' attention reconstruction, timing, memory against the 01 section 3
budget, pass-key retrieval and DSpark at 32K. usage: t17_report.py <run dir>"""
import json
import os
import re
import sys

o = sys.argv[1]


def J(name):
    p = os.path.join(o, name)
    return json.load(open(p)) if os.path.exists(p) else None


res = {}
for line in open(os.path.join(o, "res.tsv")):
    tag, rc, sec, peak = line.rstrip("\n").split("\t")
    res[tag] = (int(rc), float(sec), int(peak) if peak.strip().isdigit() else None)
idle = int(open(os.path.join(o, "mem_idle.txt")).read().split()[0])
print("idle GPU memory %d MiB" % idle)
print("\nV4 (05 section 3): mean <= max(2 N0_mean, 0.005), p99 <= max(2 N0_p99, 0.05), top-1 at margin >= 0.5 >= 99.5%")
for k in (16, 32):
    n0 = J("n0_%d.json" % k)
    if not n0:
        continue
    lm, lp = max(2 * n0["kld_mean"], 0.005), max(2 * n0["kld_p99"], 0.05)
    print("%dK: N0 mean %.4f p99 %.4f top1 %.4f%% -> limits mean %.4f p99 %.4f" % (k, n0["kld_mean"], n0["kld_p99"], 100 * n0["top1_agree_margin_ge_0.5"], lm, lp))
    for path in ("step", "serve"):
        r = J("%s%d.json" % (path, k))
        ok = r["kld_mean"] <= lm and r["kld_p99"] <= lp and r["top1_agree_margin_ge_0.5"] >= 0.995
        print("   %-5s positions %d mean %.4f p99 %.4f max %.2f top1 %.2f%% ppl %.4f (llama %.4f) -> %s" % (
            path, r["positions"], r["kld_mean"], r["kld_p99"], r["kld_max"], 100 * r["top1_agree_margin_ge_0.5"], r["ppl_q"], r["ppl_p"], "PASS" if ok else "FAIL"))
    sv = J("step_vs_serve%d.json" % k)
    print("   step vs serve: mean %.4f p99 %.4f" % (sv["kld_mean"], sv["kld_p99"]))

print("\nlevel | ppl all scored (last 4095) | prefill vs decode at C-63, C: KL max, argmax differ | attn reconstruction max | far mass (>=1024) global p50 | prompt prefill s | decode tok/s | peak MiB (ladder / gen) | KV MiB (formula) | 01 budget KV MiB")
budget = {16: None, 32: 1.16 * 1024, 64: 2.16 * 1024, 128: 4.16 * 1024}
for k in (16, 32, 64, 128):
    lad, lf = J("ladder%d.json" % k), J("lf%d.json" % k)
    tr = os.path.join(o, "trace%d" % k, "trace.jsonl")
    err, far = None, []
    if os.path.exists(tr):
        recs = [json.loads(x) for x in open(tr)]
        err = max(v for r in recs if r["stage"] == "head" for kk, v in r["checks"].items() if kk == "attn.out")
        far = sorted(r["attn"]["mass_mean"]["far_1024"] for r in recs if r.get("attn") and r["attn"]["window"] == 0)
    g = open(os.path.join(o, "gen%d.log" % k)).read() if os.path.exists(os.path.join(o, "gen%d.log" % k)) else ""
    m = re.search(r"prompt (\d+) tok in ([\d.]+) s; decode \d+ tok at ([\d.]+) tok/s", g)
    c = k * 1024
    kv = (8 * c + 40 * min(c, 3072)) * 4096 / 2**20
    print("%dK | %s (%s) | %s, %s | %s | %s | %s | %s | %s / %s | %.0f | %s" % (
        k, "%.4f" % lad["ppl"] if lad else "-", "%.4f" % lad["ppl_last"] if lad else "-",
        "%.2e" % lf["summary"]["kl"]["max"] if lf else "-", lf["summary"]["argmax_mismatch"] if lf else "-",
        "%.2e" % err if err is not None else "-", "%.3f" % far[len(far) // 2] if far else "-",
        m.group(2) if m else "-", m.group(3) if m else "-",
        res.get("ladder%d" % k, (0, 0, None))[2], res.get("gen%d" % k, (0, 0, None))[2], kv, "%.0f" % budget[k] if budget[k] else "-"))
print("\nruns (tag rc seconds peak MiB):")
for t, v in res.items():
    print("  %-16s %d %8.1f %s" % (t, v[0], v[1], v[2]))
print("\npass key:")
if os.path.exists(os.path.join(o, "needle.jsonl")):
    for line in open(os.path.join(o, "needle.jsonl")):
        print("  " + line.strip())
    print("  peak MiB during the server run:", open(os.path.join(o, "needle_peak.txt")).read().strip())
g, s = os.path.join(o, "gen32.log"), os.path.join(o, "spec32.log")
if os.path.exists(g) and os.path.exists(s):
    tok = lambda t: [int(x) for x in re.search(r"tokens: \[([^\]]*)\]", t).group(1).split(",")] if re.search(r"tokens: \[", t) else []
    a, b = tok(open(g).read()), tok(open(s).read())
    same = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    print("\nDSpark at 32K: greedy equal to plain for the first %d of %d tokens; %s" % (same, min(len(a), len(b)), " ".join(open(s).read().split("\n")[-3:])))
