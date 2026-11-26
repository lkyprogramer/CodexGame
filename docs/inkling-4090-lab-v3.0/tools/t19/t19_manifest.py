#!/usr/bin/env python3
"""T19: build the logit-dump manifests (name<TAB>lengths<TAB>ids) from the W1/W2/T14 artifacts.

Set A (calibration, already seen in T10-T13): the 16 W2 reference sequences (prompt + 500
greedy tokens); lengths = prompt end Lp, Lp+1, Lp+8, Lp+32, Lp+128 and the full sequence
(the position the original V7 used). Set B (hold-out, never used for a numerical verdict):
the 16 set-b chat prompts from T14; lengths = Lp//2 and Lp.
usage: t19_manifest.py <w1 run> <w2 run> <t14 run> <out dir>
"""
import json
import os
import sys

w1, w2, t14, out = sys.argv[1:5]
prompts = [p["ids"] for p in json.load(open(os.path.join(w1, "v2-llama.json")))]
rows_a = []
for i, p in enumerate(prompts):
    seq = [int(x) for x in open(os.path.join(w2, "seq", "%02d.ids" % i)).read().split()]
    if seq[: len(p)] != p:
        sys.exit("seq %02d does not start with its prompt" % i)
    lp = len(p)
    lens = sorted({lp, lp + 1, lp + 8, lp + 32, lp + 128, len(seq)})
    rows_a.append(("a%02d" % i, lens, seq))
rows_b = []
for e in json.load(open(os.path.join(t14, "ids.json"))):
    if e["set"] == "b":
        lp = len(e["ids"])
        rows_b.append(("b%02d" % len(rows_b), sorted({lp // 2, lp}), e["ids"]))
if len(rows_a) != 16 or len(rows_b) != 16:
    sys.exit("expected 16 + 16 sequences, got %d + %d" % (len(rows_a), len(rows_b)))
os.makedirs(out, exist_ok=True)
for fname, rows in (("manifest_a.tsv", rows_a), ("manifest_b.tsv", rows_b), ("manifest_ab.tsv", rows_a + rows_b)):
    with open(os.path.join(out, fname), "w") as f:
        for name, lens, ids in rows:
            f.write("%s\t%s\t%s\n" % (name, ",".join(map(str, lens)), " ".join(map(str, ids))))
print(json.dumps({"a_positions": sum(len(r[1]) for r in rows_a), "b_positions": sum(len(r[1]) for r in rows_b),
                  "max_len": max(max(r[1]) for r in rows_a + rows_b)}))
