#!/usr/bin/env python3
"""T21 report: decode tok/s per configuration and workload, round cost by drafts verified, the
per-position acceptance of the fixed-k runs, and an offline estimate of fixed k from the k = kmax
run (a round verifying k drafts accepts min(a, k) where a is what k = kmax accepted: the draft is
greedy left to right, so its first k tokens do not depend on how many are verified).
usage: t21_analyze.py <run dir>"""
import json
import os
import statistics as st
import sys

O = sys.argv[1]
ids = json.load(open(os.path.join(O, "ids.json")))
reps = int(open(os.path.join(O, "identity.txt")).read().split("reps ")[-1].split()[0])
order = [ids[0]] + ids * reps   # warm-up request, then reps passes in file order
SETS = ("sn", "sc", "ln", "lc")


def load(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def split_requests(rounds):
    """Rounds per request: a new request starts when the position does not continue."""
    out, cur, last = [], [], None
    for r in rounds:
        if last is not None and not (last["pos"] < r["pos"] <= last["pos"] + last["k"] + 1):
            out.append(cur); cur = []
        cur.append(r); last = r
    if cur:
        out.append(cur)
    return out


configs = [c for c in ("plain", "burst", "model", "burst7", "burstf16") + tuple("k%d" % i for i in range(1, 8)) if os.path.exists(os.path.join(O, c + ".jsonl"))]
tps, by_set = {}, {}
print("== decode tok/s, mean over prompts of the median over reps")
print("%-6s " % "" + " ".join("%8s" % s for s in SETS + ("all",)))
for c in configs:
    rows = load(os.path.join(O, c + ".jsonl"))
    med = {}
    for r in rows:
        med.setdefault((r["set"], r["case"]), []).append(r["decode_tps"])
    med = {k: st.median(v) for k, v in med.items()}
    tps[c] = med
    line = [st.mean([v for k, v in med.items() if k[0] == s]) if any(k[0] == s for k in med) else float("nan") for s in SETS]
    line.append(st.mean(med.values()))
    by_set[c] = dict(zip(SETS + ("all",), line))
    print("%-6s " % c + " ".join("%8.1f" % v for v in line))
print()
print("== speedup over plain (geomean over prompts)")
for c in configs:
    if c == "plain" or "plain" not in tps:
        continue
    out = []
    for s in SETS + ("all",):
        ks = [k for k in tps[c] if (s == "all" or k[0] == s) and k in tps["plain"]]
        g = st.geometric_mean([tps[c][k] / tps["plain"][k] for k in ks]) if ks else float("nan")
        out.append("%8.3f" % g)
    print("%-6s " % c + " ".join(out))

# Per-round data with the workload of each request.
rr = {}
for c in configs:
    reqs = split_requests(load(os.path.join(O, c + ".rounds.jsonl")))
    if not reqs:
        continue
    if len(reqs) == len(order) + 1 and reqs[0][0]["pos"] < len(order[0]["ids"]):
        reqs = reqs[1:]   # the server's own warm-up at startup (a few rounds from position ~4)
    if len(reqs) != len(order):
        print("\n%s: %d requests in the round log, expected %d (labels skipped)" % (c, len(reqs), len(order)))
        continue
    rr[c] = [(x["set"], x["case"], rq) for x, rq in list(zip(order, reqs))[1:]]

print()
print("== round time (ms, median / p90) by drafts verified; short = sn+sc, long = ln+lc")
cost = {}
for c in configs:
    if c not in rr or not c.startswith("k"):
        continue
    k = int(c[1:])
    for grp, sets in (("short", ("sn", "sc")), ("long", ("ln", "lc"))):
        ms = [r["ms"] for s, _, rq in rr[c] if s in sets for r in rq]
        if ms:
            ms.sort()
            cost[(k, grp)] = st.median(ms)
            print("k%d %-5s n %6d  median %6.3f  p90 %6.3f" % (k, grp, len(ms), st.median(ms), ms[int(0.9 * (len(ms) - 1))]))
plain_ms = {}
for grp, sets in (("short", ("sn", "sc")), ("long", ("ln", "lc"))):
    v = [1e3 / tps["plain"][k] for k in tps.get("plain", {}) if k[0] in sets]
    if v:
        plain_ms[grp] = st.mean(v)
        print("plain %-5s ms/token %.3f (from tok/s)" % (grp, plain_ms[grp]))

kmax = max([int(c[1:]) for c in rr if c.startswith("k")], default=0)
if kmax:
    c = "k%d" % kmax
    print()
    print("== acceptance of %s: P(accepted >= i) and P(draft i accepted | 1..i-1 accepted)" % c)
    acc_by = {}
    for s in SETS:
        a = [r["acc"] for ss, _, rq in rr[c] if ss == s for r in rq]
        if not a:
            continue
        acc_by[s] = a
        ge = [sum(x >= i for x in a) / len(a) for i in range(kmax + 1)]
        cond = [ge[i] / ge[i - 1] if ge[i - 1] else 0 for i in range(1, kmax + 1)]
        print("%s rounds %6d  mean acc %.2f  ge %s  cond %s" % (s, len(a), st.mean(a), " ".join("%.3f" % g for g in ge[1:]), " ".join("%.3f" % g for g in cond)))
    print()
    print("== offline fixed k: expected tokens per round / measured round ms -> tok/s (from %s acceptance)" % c)
    print("%-5s " % "" + " ".join("%8s" % ("k%d" % k) for k in range(1, kmax + 1)) + "   plain")
    for s, a in acc_by.items():
        grp = "short" if s in ("sn", "sc") else "long"
        row = []
        for k in range(1, kmax + 1):
            if (k, grp) not in cost:
                row.append("%8s" % "-"); continue
            e = st.mean([min(x, k) + 1 for x in a])
            row.append("%8.1f" % (1e3 * e / cost[(k, grp)]))
        print("%-5s " % s + " ".join(row) + "   %.1f" % (1e3 / plain_ms[grp] if grp in plain_ms else float("nan")))
