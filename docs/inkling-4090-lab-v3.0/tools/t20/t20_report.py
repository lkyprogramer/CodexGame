#!/usr/bin/env python3
"""T20 summary of a judged run dir: num-3 checks per path, verify row coverage, cross-engine
numbers, and strict token agreement of free-running greedy (Astral generate vs llama.cpp).
usage: t20_report.py <run dir>"""
import glob
import json
import os
import re
import sys

o = sys.argv[1]
for f in sorted(glob.glob(os.path.join(o, "num3_*.json"))):
    v = json.load(open(f))
    label = os.path.basename(f)[5:-5]
    print("%-12s complete=%s passed=%s positions=%d %s" % (label, v["complete"], v["passed"], v["positions"], v["problems"]))
    for k, c in v.get("checks", {}).items():
        if k == "argmax":
            print("    argmax flips %d, at margin >= limit %s" % (c["flips"], c["flips_at_margin_ge_limit"]))
        else:
            print("    %-14s cand %.4g ref %.4g ratio %.3f %s" % (k, c["cand"], c["ref"], c["ratio"], "ok" if c["ok"] else "FAIL"))
    mn = v.get("recorded", {}).get("max_near")
    if mn:
        print("    max_near (recorded) cand max %.3f ref max %.3f" % (mn["cand"]["max"], mn["ref"]["max"]))
for f in sorted(glob.glob(os.path.join(o, "vf", "verify*.tsv"))):
    rows = [line.split("\t") for line in open(f).read().split("\n") if line]
    hist = {}
    for r in rows:
        hist[int(r[2])] = hist.get(int(r[2]), 0) + 1
    print("%s: %d positions, rows per pass %s, by row index %s" % (os.path.basename(f), len(rows), rows[0][3] if rows else "-", dict(sorted(hist.items()))))
for f in sorted(glob.glob(os.path.join(o, "cross_*.json"))):
    s = json.load(open(f))["summary"]
    n = sum(1 for _ in open(f[:-5] + ".jsonl"))
    print("%-18s n=%d near_w mean %.4g  kl mean %.4g p90 %.4g max %.4g  argmax differ %d" % (
        os.path.basename(f)[:-5], n, s["near_w"]["mean"], s["kl"]["mean"], s["kl"]["p90"], s["kl"]["max"], s["argmax_mismatch"]))
ref = {r["i"]: r for r in json.load(open(os.path.join(o, "bseq", "ref.json")))}
tot = same_prefix = equal_pos = 0
first = []
for i in sorted(ref):
    p = os.path.join(o, "gen_%02d.txt" % i)
    m = re.search(r"tokens: \[([^\]]*)\]", open(p).read()) if os.path.exists(p) else None
    if not m:
        print("gen_%02d: no tokens" % i)
        continue
    a = [int(x) for x in m.group(1).split(",") if x.strip()]
    g = ref[i]["gen"][: len(a)]
    k = next((j for j, (x, y) in enumerate(zip(a, g)) if x != y), min(len(a), len(g)))
    tot += len(g)
    same_prefix += k
    equal_pos += sum(x == y for x, y in zip(a, g))
    first.append((i, k, ref[i]["ref_margin"][k] if k < len(g) else None))
print("free-running greedy: %d prompts, %d tokens; identical prefix %d (%.1f%%); position-wise equal %d" % (len(first), tot, same_prefix, 100.0 * same_prefix / max(tot, 1), equal_pos))
for i, k, mg in first:
    print("    b%02d first difference at generated token %s, llama.cpp top-2 margin there %s" % (i, k if mg is not None else "none (all equal)", "%.3f" % mg if mg is not None else "-"))
