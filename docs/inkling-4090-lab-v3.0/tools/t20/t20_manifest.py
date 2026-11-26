#!/usr/bin/env python3
"""T20: manifests (name<TAB>lengths<TAB>ids) for the coverage checks.

Set B (hold-out): the 16 set-b prompts with 160 greedy llama.cpp tokens; lengths Lp,
Lp+1..Lp+16, Lp+32, Lp+64, Lp+96, Lp+128 (consecutive early positions so verify rows of
every index occur). Set D (long documents): per document two entries over the same ids,
dNN_s with 8, 9, 64, 65 (MMA / small-batch row tiles) and 1023, 1024, 1025 (the SWA window),
dNN_l with 2040 (prompt of the decode path), 2047-2050, 2056, 2057 (the 2048-token prefill
chunk; 2049 leaves a one-token chunk) and 4096, 4097.
The first length of an entry is where the decode / verify paths start; *_gen.tsv files drop it.

usage: t20_manifest.py <b ids.json> <b seq dir> <d ids.json> <out dir>
"""
import json
import os
import sys

bids, bseq, dids, out = sys.argv[1:5]
rows_b, rows_d = [], []
for e in json.load(open(bids)):
    p = e["ids"]
    seq = [int(x) for x in open(os.path.join(bseq, "%02d.ids" % e["case"])).read().split()]
    if seq[: len(p)] != p or len(seq) < len(p) + 128:
        sys.exit("set b %02d: bad sequence" % e["case"])
    lp = len(p)
    rows_b.append(("b%02d" % e["case"], [lp] + [lp + k for k in range(1, 17)] + [lp + 32, lp + 64, lp + 96, lp + 128], seq))
for e in json.load(open(dids)):
    ids = e["ids"]
    if len(ids) < 4097:
        sys.exit("doc %d (%s): %d tokens, need 4097" % (e["case"], e.get("src"), len(ids)))
    rows_d.append(("d%02d_s" % e["case"], [8, 9, 64, 65, 1023, 1024, 1025], ids))
    rows_d.append(("d%02d_l" % e["case"], [2040, 2047, 2048, 2049, 2050, 2056, 2057, 4096, 4097], ids))
if len(rows_b) != 16 or len(rows_d) < 6:
    sys.exit("expected 16 set-b sequences and at least 3 documents")
os.makedirs(out, exist_ok=True)


def write(fname, rows, drop_first=False):
    with open(os.path.join(out, fname), "w") as f:
        for name, lens, ids in rows:
            ls = lens[1:] if drop_first else lens
            f.write("%s\t%s\t%s\n" % (name, ",".join(map(str, ls)), " ".join(map(str, ids[: max(lens)]))))


write("manifest_b.tsv", rows_b)
write("manifest_b_gen.tsv", rows_b, True)
write("manifest_d.tsv", rows_d)
write("manifest_d_gen.tsv", rows_d, True)
write("manifest_bd.tsv", rows_b + rows_d)
print(json.dumps({"b_positions": sum(len(r[1]) for r in rows_b), "d_positions": sum(len(r[1]) for r in rows_d),
                  "d_tokens": [len(r[2]) for r in rows_d[::2]]}))
