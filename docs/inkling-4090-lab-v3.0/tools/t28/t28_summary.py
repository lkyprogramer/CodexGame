#!/usr/bin/env python3
"""T28: summarise the ASTRAL_TRACE_SPARSE records of an astral trace (trace.jsonl).

Per sequence group (c32k / c64k / c128k / d3) and over all global-layer visits and heads: the far
mass (distance >= 1024), and for each kept-block budget and policy (bound / mean / oracle /
random) the mean, p90 and max of the true missed mass and of the relative output error; the
threshold rule's kept share, missed mass and bound.
"""
import collections, json, sys
import numpy as np


def q(a, p):
    return float(np.percentile(a, p)) if len(a) else float("nan")


def main():
    g = collections.defaultdict(lambda: collections.defaultdict(list))
    for line in open(sys.argv[1]):
        r = json.loads(line)
        sp = (r.get("attn") or {}).get("sparse")
        if not sp:
            continue
        grp = r["seq"]
        for h in sp:
            if not h:
                continue
            s = g[grp]
            s["far"].append(h["far_mass"])
            s["blocks"].append(h["far_blocks"])
            for b, pol in h["budget"].items():
                for name, (m, e) in pol.items():
                    s["miss %s %s" % (b, name)].append(m)
                    if e is not None:
                        s["err %s %s" % (b, name)].append(e)
            for t, v in h["threshold"].items():
                for k in ("kept", "missed", "bound", "out_err"):
                    if v.get(k) is not None:
                        s["thr %s %s" % (t, k)].append(v[k])
    for grp, s in sorted(g.items()):
        print("== %s: %d head-visits, far blocks %d..%d; far mass mean %.3f p50 %.3f p90 %.3f" % (grp, len(s["far"]), min(s["blocks"]), max(s["blocks"]), np.mean(s["far"]), q(s["far"], 50), q(s["far"], 90)))
        print("   budget  policy   missed mean / p90 / max        out_err mean / p90 / max")
        for b in ("0.0625", "0.125", "0.25", "0.5"):
            for name in ("bound", "mean", "oracle", "random"):
                m, e = s["miss %s %s" % (b, name)], s["err %s %s" % (b, name)]
                print("   %-7s %-7s %.4f / %.4f / %.4f    %.4f / %.4f / %.4f" % (b, name, np.mean(m), q(m, 90), max(m), np.mean(e) if e else float("nan"), q(e, 90), max(e) if e else float("nan")))
        for t in ("0.001", "0.0001"):
            print("   threshold %s: kept %.3f (p90 %.3f), missed mean %.5f max %.5f, bound mean %.4f, out_err p90 %.4f max %.4f" % (
                t, np.mean(s["thr %s kept" % t]), q(s["thr %s kept" % t], 90), np.mean(s["thr %s missed" % t]), max(s["thr %s missed" % t]),
                np.mean(s["thr %s bound" % t]), q(s["thr %s out_err" % t], 90), max(s["thr %s out_err" % t]) if s["thr %s out_err" % t] else float("nan")))


if __name__ == "__main__":
    main()
