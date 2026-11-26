#!/usr/bin/env python3
"""T18 summary: tensor tables of A1 / A4, and per model and pass count the corpus perplexity,
KL to the same model at 3 passes and to llama.cpp A1, decode speed and greedy agreement with
3 passes; prefill vs step at R = 1 and 5. usage: t18_report.py <run dir>"""
import glob
import json
import os
import re
import sys

o = sys.argv[1]


def table(path):
    rows = {}
    for line in open(path):
        m = re.match(r"\s+(\S+)\s+(\S+)\s+\[([^\]]*)\]", line)
        if m and "." in m.group(1) and m.group(2) != "=":
            rows[m.group(1)] = (m.group(2), m.group(3))
    return rows


a1, a4 = table(os.path.join(o, "a1_tensors.txt")), table(os.path.join(o, "a4_tensors.txt"))
only1, only4 = sorted(set(a1) - set(a4)), sorted(set(a4) - set(a1))
diff = [k for k in set(a1) & set(a4) if a1[k] != a4[k]]
print("tensors: A1 %d, A4 %d, only in A1 %d, only in A4 %d, same name with other type/shape %d" % (len(a1), len(a4), len(only1), len(only4), len(diff)))
for k in (only1 + only4 + sorted(diff))[:10]:
    print("   ", k, a1.get(k), a4.get(k))


def gen(path):
    t = open(path).read()
    m = re.search(r"tokens: \[([^\]]*)\]", t)
    s = re.search(r"decode \d+ tok at ([\d.]+) tok/s", t)
    return ([int(x) for x in m.group(1).split(",")] if m else None), (float(s.group(1)) if s else None)


print("\nmodel R | ppl | KL vs same model R=3: mean p99 | top-1 vs R=3 | KL vs llama.cpp A1: mean | decode tok/s | greedy = R=3 for first n of 128")
for m in ("a4", "a1"):
    g3, _ = gen(os.path.join(o, "%s_r3.gen.txt" % m))
    rs = sorted(int(re.search(r"_r(\d+)\.vs_r3", f).group(1)) for f in glob.glob(os.path.join(o, "%s_r*.vs_r3.json" % m)))
    for r in rs:
        v3 = json.load(open(os.path.join(o, "%s_r%d.vs_r3.json" % (m, r))))
        vl = json.load(open(os.path.join(o, "%s_r%d.vs_llama_a1.json" % (m, r))))
        g, tps = gen(os.path.join(o, "%s_r%d.gen.txt" % (m, r)))
        same = next((i for i, (x, y) in enumerate(zip(g, g3)) if x != y), len(g)) if g and g3 else None
        tag = "" if m == "a1" or 1 <= r <= 5 else " (extrapolation)"
        print("%s R=%-2d | %.4f | %.4f %.4f | %.2f%% | %.4f | %s | %s%s" % (m.upper(), r, v3["ppl_q"], v3["kld_mean"], v3["kld_p99"], 100 * v3["top1_agree"], vl["kld_mean"], tps, same, tag))
print("\nprefill vs step (A4, 4 set-C sequences, 5 lengths each):")
for r in (1, 5):
    p = os.path.join(o, "pf_r%d.json" % r)
    if os.path.exists(p):
        s = json.load(open(p))["summary"]
        print("  R=%d: KL mean %.2e max %.2e, argmax differ %d" % (r, s["kl"]["mean"], s["kl"]["max"], s["argmax_mismatch"]))
