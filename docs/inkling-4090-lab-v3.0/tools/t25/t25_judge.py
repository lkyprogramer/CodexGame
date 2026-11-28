#!/usr/bin/env python3
"""T25: judge a t25_run.sh directory by a frozen num-4L rule (rule_num4l.json).

  t25_judge.py <run dir> <tag> <rule.json> [--cases N] [--negs-expect FILE]
  exit 0 PASS, 1 FAIL, 2 INCOMPLETE, 3 INVALID (a negative control expected to be caught was not,
  or a listed negative has no registered expectation)
Pools all positions of the set per pair (from t25_kld.py's .npz), compares candidate pairs with
llama.cpp's own shape control on the same positions, and prints one JSON report.
Fail-closed (T41): missing / extra cases, missing pairs, wrong position counts, duplicate positions,
non-finite KL and missing negative controls are INCOMPLETE; negatives are part of the verdict.
"""
import argparse, glob, json, os, sys
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir"); ap.add_argument("tag"); ap.add_argument("rule")
    ap.add_argument("--cases", type=int, help="expected number of cases (default: from ids in identity / inputs)")
    ap.add_argument("--negs-expect", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "negs_expect.json"))
    a = ap.parse_args()
    d, tag, rf = a.dir, a.tag, a.rule
    rule = json.load(open(rf))
    lim = rule["limits"]
    cases = sorted(glob.glob(os.path.join(d, tag + "[0-9]*.json")), key=lambda p: int(os.path.basename(p)[len(tag):-5]))
    probs, data = [], {}
    for c in cases:
        name = os.path.basename(c)[:-5]
        js = json.load(open(c))
        lens = json.load(open(os.path.join(d, name, "lens.json"))) if os.path.exists(os.path.join(d, name, "lens.json")) else None
        n = len(open(os.path.join(d, name, "ids.txt")).read().split())
        nsamp = len(open(os.path.join(d, name, "sample.tsv")).read().split("\t")[1].split(","))
        for k in map(str, range(8)):
            if k not in js:
                probs.append("%s: pair %s missing" % (name, k)); continue
            want = n - 1 - rule["first"] if k in "01234" else nsamp
            if js[k]["positions"] != want:
                probs.append("%s pair %s: %d positions, expected %d" % (name, k, js[k]["positions"], want))
            if js[k].get("nonfinite_rows", 0):
                probs.append("%s pair %s: non-finite rows" % (name, k))
        data[name] = ({os.path.basename(f)[len(name) + 6:-4]: dict(np.load(f)) for f in glob.glob("%s.*.npz" % c)}, lens)
        for k, z in data[name][0].items():
            if not np.all(np.isfinite(z["kl"])):
                probs.append("%s pair %s: non-finite KL" % (name, k))
            if np.unique(z["pos"]).size != z["pos"].size:
                probs.append("%s pair %s: duplicate positions" % (name, k))
    if not cases:
        probs.append("no cases")
    if a.cases is not None and len(cases) != a.cases:
        probs.append("%d cases, expected %d" % (len(cases), a.cases))
    nf = os.path.join(d, "negs.txt")
    neg_names = open(nf).read().split() if os.path.exists(nf) else []
    expect = json.load(open(a.negs_expect)) if os.path.exists(a.negs_expect) else {}
    for j_, name in enumerate(neg_names):
        if any(str(8 + j_) not in z for z, _ in data.values()):
            probs.append("negative %s missing in some cases" % name)
    if probs:
        print(json.dumps({"policy": rule["policy"], "verdict": "INCOMPLETE", "problems": probs}, indent=1)); return 2
    pool = lambda k, f: np.concatenate([f(z[k]) for z, _ in data.values()])
    out, ok_all = [], True
    for ch in rule["checks"]:
        c, r = str(ch["cand"]), str(ch["ref"])
        kc, kr = pool(c, lambda z: z["kl"]), pool(r, lambda z: z["kl"])
        q = 99 if ch["kind"] == "dense" else 90
        ql = lim["dense_p99_ratio"] if ch["kind"] == "dense" else lim["sampled_p90_ratio"]
        res = {"path": ch["path"], "cand": rule["pairs"][c], "ref": rule["pairs"][r], "positions": int(kc.size),
               "mean": [float(kc.mean()), float(kr.mean()), float(kc.mean() / kr.mean())],
               "p%d" % q: [float(np.percentile(kc, q)), float(np.percentile(kr, q)), float(np.percentile(kc, q) / np.percentile(kr, q))]}
        ok = res["mean"][2] <= lim["mean_ratio"] and res["p%d" % q][2] <= ql
        for m in lim["flip_margins"]:
            fc = int(pool(c, lambda z: (~z["agree"]) & (z["ref_margin"] >= m)).sum())
            fr = int(pool(r, lambda z: (~z["agree"]) & (z["ref_margin"] >= m)).sum())
            res["flips_margin_ge_%g" % m] = [fc, fr]
            ok &= fc <= lim["flip_factor"] * fr + lim["flip_slack"]
        if ch["kind"] == "dense":
            per = {n: float(z[c]["kl"].mean() / z[r]["kl"].mean()) for n, (z, _) in data.items()}
            res["per_document_mean_ratio"] = per
            ok &= max(per.values()) <= lim["per_document_mean_ratio"]
            gen = [(z[c]["kl"][z[c]["pos"] >= l["prompt_len"] - 1], z[r]["kl"][z[r]["pos"] >= l["prompt_len"] - 1]) for z, l in data.values() if l and l["len"] > l["prompt_len"]]
            if gen:
                gc, gr = np.concatenate([a for a, _ in gen]), np.concatenate([b for _, b in gen])
                res["generated_region_recorded"] = {"positions": int(gc.size), "mean": [float(gc.mean()), float(gr.mean())], "max": [float(gc.max()), float(gr.max())]}
        res["kl_max_recorded"] = [float(kc.max()), float(kr.max())]
        res["ok"] = bool(ok)
        ok_all &= ok
        out.append(res)
    # Negative controls (pairs 8, ...; negs.txt): judged like the cross serve check; each should FAIL.
    negs, invalid = [], []
    for j, name in enumerate(neg_names):
        k = str(8 + j)
        zs = [z for z, _ in data.values()]
        kc, kr = np.concatenate([z[k]["kl"] for z in zs]), np.concatenate([z["0"]["kl"] for z in zs])
        fc = [int(np.concatenate([(~z[k]["agree"]) & (z[k]["ref_margin"] >= m) for z in zs]).sum()) for m in lim["flip_margins"]]
        fr = [int(np.concatenate([(~z["0"]["agree"]) & (z["0"]["ref_margin"] >= m) for z in zs]).sum()) for m in lim["flip_margins"]]
        per = max(float(z[k]["kl"].mean() / z["0"]["kl"].mean()) for z in zs)
        mr, pr = float(kc.mean() / kr.mean()), float(np.percentile(kc, 99) / np.percentile(kr, 99))
        passes = mr <= lim["mean_ratio"] and pr <= lim["dense_p99_ratio"] and per <= lim["per_document_mean_ratio"] and all(a <= lim["flip_factor"] * b + lim["flip_slack"] for a, b in zip(fc, fr))
        e = expect.get(name, {}).get("expect")
        negs.append({"name": name, "mean_ratio": mr, "p99_ratio": pr, "max_per_document_ratio": per, "flips": [fc, fr], "caught": not passes, "expect": e})
        if e not in ("caught", "below_resolution"):
            invalid.append("negative %s has no registered expectation in %s" % (name, a.negs_expect))
        elif e == "caught" and passes:
            invalid.append("negative %s expected to be caught but passes the rule" % name)
    if not any(n["expect"] == "caught" and n["caught"] for n in negs):
        invalid.append("no negative control registered as caught was caught (no evidence the rule has power)")
    verdict = "INVALID" if invalid else ("PASS" if ok_all else "FAIL")
    print(json.dumps({"policy": rule["policy"], "cases": list(data), "verdict": verdict, "invalid": invalid, "checks": out, "negative_controls": negs}, indent=1))
    return 3 if invalid else (0 if ok_all else 1)


if __name__ == "__main__":
    sys.exit(main())
