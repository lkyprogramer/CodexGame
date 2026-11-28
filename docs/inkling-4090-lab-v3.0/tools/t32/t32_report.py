#!/usr/bin/env python3
"""T32 report: loop self-speculation agreement (ls-diag), its control, the prefix property (trace
R = 1 vs R = 3) and A4's DSpark baseline.  usage: t32_report.py <run dir>"""
import collections, glob, json, os, sys


def rows(path):
    return [json.loads(l) for l in open(path) if l.startswith("{")]


def main():
    o = sys.argv[1]
    for m in ("a4", "a1"):
        by = collections.defaultdict(list)
        for f in sorted(glob.glob(os.path.join(o, m + ".p_*.jsonl"))):
            if f.endswith(".off.jsonl"):
                continue
            s = os.path.basename(f).split(".")[1].split("_")[1]
            by[s].append(rows(f))
        print("== %s: agreement of the pick after pass p with the full depth (generated tokens)" % m)
        for s in ("sn", "sc", "ln", "lc", "all"):
            seqs = [r for k, v in by.items() if s in (k, "all") for r in v]
            if not seqs:
                continue
            npass = len(seqs[0][0]["picks"])
            for p in range(npass):
                hit = [[r["picks"][p] == r["final"] for r in q] for q in seqs]
                n = sum(map(len, hit))
                rate = sum(map(sum, hit)) / n
                # run length of consecutive agreements from each position (teacher-forced proxy of
                # the accepted drafts per round), capped at k
                runs = []
                for h in hit:
                    run = 0
                    for x in reversed(h):
                        run = run + 1 if x else 0
                        runs.append(run)
                caps = " ".join("k%d %.2f" % (k, sum(min(r, k) for r in runs) / len(runs)) for k in (1, 2, 3, 4, 6, 8))
                print("  %-3s pass %d: %d steps in %d seqs, agree %.4f; mean accepted %s" % (s, p + 1, n, len(seqs), rate, caps))
        same, tot = 0, 0
        for f in glob.glob(os.path.join(o, m + ".p_*.off.jsonl")):
            off = [r["final"] for r in rows(f)]
            on = [r["final"] for r in rows(f.replace(".off.jsonl", ".jsonl"))]
            tot += 1
            same += off == on
        print("  control (diagnosis off vs on, full-depth picks identical): %d of %d sequences" % (same, tot))
        d1, d3 = os.path.join(o, "tr_%s_r1" % m, "trace.jsonl"), os.path.join(o, "tr_%s_r3" % m, "trace.jsonl")
        if os.path.exists(d1) and os.path.exists(d3):
            key = lambda r: (r.get("seq"), r.get("len"), r.get("visit"))
            a = {key(r): r for r in rows(d1) if r.get("visit") is not None and r["visit"] < 18}
            b = {key(r): r for r in rows(d3) if r.get("visit") is not None and r["visit"] < 18}
            common = sorted(set(a) & set(b))
            diff = [k for k in common if a[k] != b[k]]
            print("  prefix property (visits 0..17, R = 1 vs R = 3): %d records, %d differ %s" % (len(common), len(diff), diff[:5]))
    for f in glob.glob(os.path.join(o, "a4_dspark", "*", "report.txt")):
        print("== A4 + own DSpark (T21 protocol): " + f)
        print(open(f).read())


if __name__ == "__main__":
    main()
