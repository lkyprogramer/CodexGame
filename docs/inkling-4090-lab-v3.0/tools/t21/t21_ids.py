#!/usr/bin/env python3
"""T21 workloads: the 32 serving prompts (chat template, from T14's ids.json) split into code and
natural-language requests, plus raw-text continuations of long_len tokens: natural language from
the T17 corpus (llama.cpp's markdown), code from code_ids.json (llama.cpp's Python sources,
tokenized by t21_cost.sh).
usage: t21_ids.py <t14 ids.json> <t17 ids.json> <code_ids.json> <out.json> [long_len] [n_long]"""
import json
import os
import sys

src, nl_ids, code_ids, out = sys.argv[1:5]
L = int(sys.argv[5]) if len(sys.argv) > 5 else 16384
n_long = int(sys.argv[6]) if len(sys.argv) > 6 else 4
# Code requests by (set, case) in bench/serving/prompts_set_{a,b}.json.
CODE = {("a", 3), ("a", 4), ("a", 7), ("a", 11), ("a", 13), ("a", 15), ("b", 0), ("b", 3), ("b", 8), ("b", 12), ("b", 15)}
res = []
for x in json.load(open(src)):
    kind = "sc" if (x["set"], x["case"]) in CODE else "sn"
    res.append({"set": kind, "case": len([r for r in res if r["set"] == kind]), "src": "%s%02d" % (x["set"], x["case"]), "ids": x["ids"]})
for kind, path in (("ln", nl_ids), ("lc", code_ids)):
    ids = json.load(open(path))
    span = len(ids) - L
    if span < 0:
        sys.exit("t21_ids: %s has %d tokens, need %d" % (path, len(ids), L))
    for i in range(n_long):
        o = span * i // max(1, n_long - 1)
        res.append({"set": kind, "case": i, "src": "%s[%d:%d]" % (os.path.basename(path), o, o + L), "ids": ids[o:o + L]})
json.dump(res, open(out, "w"))
print(", ".join("%s %d" % (k, sum(r["set"] == k for r in res)) for k in ("sn", "sc", "ln", "lc")))
