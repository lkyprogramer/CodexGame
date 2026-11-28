#!/usr/bin/env python3
"""T25: judge a t25_run.sh directory by a frozen num-4L rule (rule_num4l.json).

  t25_judge.py <run dir> <tag> <rule.json>    exit 0 PASS, 1 FAIL, 2 incomplete
Pools all positions of the set per pair (from t25_kld.py's .npz), compares candidate pairs with
llama.cpp's own shape control on the same positions, and prints one JSON report.
"""
import glob, json, os, sys
import numpy as np


def main():
    d, tag, rf = sys.argv[1:4]
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
        data[name] = ({os.path.basename(f)[len(name) + 6:-4]: np.load(f) for f in glob.glob("%s.*.npz" % c)}, lens)
    if not cases:
        probs.append("no cases")
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
    negs = []
    nf = os.path.join(d, "negs.txt")
    for j, name in enumerate(open(nf).read().split() if os.path.exists(nf) else []):
        k = str(8 + j)
        zs = [z for z, _ in data.values() if k in z]
        if len(zs) != len(data):
            negs.append({"name": name, "problem": "missing in some cases"}); continue
        kc, kr = np.concatenate([z[k]["kl"] for z in zs]), np.concatenate([z["0"]["kl"] for z in zs])
        fc = [int(np.concatenate([(~z[k]["agree"]) & (z[k]["ref_margin"] >= m) for z in zs]).sum()) for m in lim["flip_margins"]]
        fr = [int(np.concatenate([(~z["0"]["agree"]) & (z["0"]["ref_margin"] >= m) for z in zs]).sum()) for m in lim["flip_margins"]]
        per = max(float(z[k]["kl"].mean() / z["0"]["kl"].mean()) for z in zs)
        mr, pr = float(kc.mean() / kr.mean()), float(np.percentile(kc, 99) / np.percentile(kr, 99))
        passes = mr <= lim["mean_ratio"] and pr <= lim["dense_p99_ratio"] and per <= lim["per_document_mean_ratio"] and all(a <= lim["flip_factor"] * b + lim["flip_slack"] for a, b in zip(fc, fr))
        negs.append({"name": name, "mean_ratio": mr, "p99_ratio": pr, "max_per_document_ratio": per, "flips": [fc, fr], "caught": not passes})
    print(json.dumps({"policy": rule["policy"], "cases": list(data), "verdict": "PASS" if ok_all else "FAIL", "checks": out, "negative_controls": negs}, indent=1))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
