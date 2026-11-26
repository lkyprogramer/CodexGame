#!/usr/bin/env python3
"""T15: integrity and a first descriptive look at a trace (fork docs/trace.md).

Integrity: every probed position has 48 visit records and a head record; the largest relative
reconstruction errors (block mixes, messages, controllers, attention output) and router-pick
mismatches over the whole trace. Description (no hypothesis test; R2 / R3 / R5 / R8 do that):
per stage and pass, the median stream RMS, how often each coordinate is the largest one, its
energy share, attention mass buckets, router 8th/9th margins, controller gain / forget, and
the raw-lens rank of the target token.
usage: t15_summary.py <trace.jsonl>"""
import collections
import json
import statistics as S
import sys

recs = [json.loads(line) for line in open(sys.argv[1])]
heads = [r for r in recs if r["stage"] == "head"]
visits = [r for r in recs if r["stage"] != "head"]
per_pos = collections.Counter((r["seq"], r["len"]) for r in visits)
bad = [k for k, v in per_pos.items() if v != 48]
print("positions %d, visit records %d, positions without 48 visits: %d" % (len(heads), len(visits), len(bad)))
worst = collections.defaultdict(float)
for h in heads:
    for k, v in h["checks"].items():
        worst[k] = max(worst[k], v)
print("largest reconstruction errors (relative to max |device output|):", {k: "%.2e" % v for k, v in sorted(worst.items())})
print("native readout: target rank 0 at %d of %d positions with a target" % (
    sum(1 for h in heads if h["native"].get("target_rank") == 0), sum(1 for h in heads if "target_rank" in h["native"])))


def key(r):
    return (r["stage"], r["pass"])


groups = collections.defaultdict(list)
for r in visits:
    groups[key(r)].append(r)
print("\nstage pass | n | stream rms p50 | top coord (share of records) | its energy p50 | attn sink / self / near / mid / far | router margin p50 | lens target rank p50")
for k in sorted(groups, key=lambda k: ({"prelude": 0, "core": 1, "coda": 2}[k[0]], -1 if k[1] is None else k[1])):
    g = groups[k]
    tops = collections.Counter(r["stream"]["top"][0][0] for r in g)
    c, cnt = tops.most_common(1)[0]
    share = [r["stream"]["top"][0][2] for r in g if r["stream"]["top"][0][0] == c]
    am = [r["attn"]["mass_mean"] for r in g if "attn" in r]
    mm = [S.median(a[b] for a in am) for b in ("sink", "self", "near_1_63", "mid_64_1023", "far_1024")]
    rm = S.median(r["router"]["margin_k_k1"] for r in g if "router" in r)
    lr = [r["lens_raw"]["target_rank"] for r in g if "lens_raw" in r and "target_rank" in r["lens_raw"]]
    print("%-7s %-4s | %4d | %6.2f | %4d (%.0f%%) | %.2f | %s | %.4f | %s" % (
        k[0], "-" if k[1] is None else k[1], len(g), S.median(r["stream"]["rms"] for r in g), c, 100.0 * cnt / len(g), S.median(share),
        " / ".join("%.2f" % v for v in mm), rm, int(S.median(lr)) if lr else "-"))
ctrl = collections.defaultdict(list)
for r in visits:
    for c in r.get("ctrl", []):
        ctrl[(r["pass"], c["which"])].append(c)
print("\ncontroller (pass, input) | n | gain mean p50 | forget mean p50 | keep p50 p50 | gain-term / forget-term norm p50")
for k in sorted(ctrl):
    g = ctrl[k]
    print("%s | %d | %.3f | %.3f | %.3f | %.3f" % (k, len(g), S.median(c["gain"]["mean"] for c in g), S.median(c["forget"]["mean"] for c in g),
                                              S.median(c["keep"]["p50"] for c in g), S.median(c["gain_term_norm"] / max(c["forget_term_norm"], 1e-9) for c in g)))
