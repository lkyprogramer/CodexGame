#!/usr/bin/env python3
"""T19: build the logit-dump manifests (name<TAB>lengths<TAB>ids) from the W1/W2/T14 artifacts.

Set A (calibration, already seen in T10-T13): the 16 W2 reference sequences (prompt + 500
greedy tokens); lengths = prompt end Lp, Lp+1, Lp+8, Lp+32, Lp+128 and the full sequence
(the position the original V7 used). Set B (hold-out, never used for a numerical verdict):
the 16 set-b chat prompts from T14; lengths = Lp//2 and Lp.
Set C (hold-out for num-3, frozen before any candidate result): 16 new prompts
(prompts_set_c.json) with 160 greedy llama.cpp tokens; lengths as set A without the full
sequence. Optional: pass <c seq dir> (NN.ids from greedy_reference.py) and <c ids.json>.
usage: t19_manifest.py <w1 run> <w2 run> <t14 run> <out dir> [<c seq dir> <c ids.json>]
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
rows_c = []
if len(sys.argv) > 6:
    cdir, cids = sys.argv[5:7]
    for e in json.load(open(cids)):
        p = e["ids"]
        seq = [int(x) for x in open(os.path.join(cdir, "%02d.ids" % e["case"])).read().split()]
        if seq[: len(p)] != p or len(seq) < len(p) + 128:
            sys.exit("set c %02d: bad sequence" % e["case"])
        lp = len(p)
        rows_c.append(("c%02d" % e["case"], [lp, lp + 1, lp + 8, lp + 32, lp + 128], seq))
    if len(rows_c) != 16:
        sys.exit("expected 16 set-c sequences, got %d" % len(rows_c))
os.makedirs(out, exist_ok=True)
sets = [("manifest_a.tsv", rows_a), ("manifest_b.tsv", rows_b), ("manifest_ab.tsv", rows_a + rows_b)]
if rows_c:
    sets += [("manifest_c.tsv", rows_c), ("manifest_abc.tsv", rows_a + rows_b + rows_c)]
for fname, rows in sets:
    with open(os.path.join(out, fname), "w") as f:
        for name, lens, ids in rows:
            f.write("%s\t%s\t%s\n" % (name, ",".join(map(str, lens)), " ".join(map(str, ids))))
print(json.dumps({"a_positions": sum(len(r[1]) for r in rows_a), "b_positions": sum(len(r[1]) for r in rows_b),
                  "c_positions": sum(len(r[1]) for r in rows_c), "max_len": max(max(r[1]) for r in rows_a + rows_b + rows_c)}))
