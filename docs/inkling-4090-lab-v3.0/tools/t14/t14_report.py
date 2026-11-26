"""T14 report: per-config medians, TTFT / ITL percentiles, paired CSVs for paired_stats.py."""
import json, sys, statistics as st, csv, os, glob
import numpy as np
O = sys.argv[1]
rows = {}
for f in sorted(glob.glob(f"{O}/*.jsonl")):
    lab = os.path.basename(f)[:-6]
    rows[lab] = [json.loads(l) for l in open(f)]
summary, med = {}, {}
for lab, rs in rows.items():
    if not rs:
        continue
    cases = sorted({(r["set"], r["case"]) for r in rs})
    med[lab] = {c: {"ms": st.median([r["decode_ms_per_tok"] for r in rs if (r["set"], r["case"]) == c]),
                    "ttft": st.median([r["ttft_ms"] for r in rs if (r["set"], r["case"]) == c])} for c in cases}
    itl = np.array([v for r in rs for v in r["itl_ms"]])
    tps = [1000 / m["ms"] for m in med[lab].values()]
    reps = sorted({r["rep"] for r in rs})
    rep_means = [st.mean([r["decode_tps"] for r in rs if r["rep"] == k]) for k in reps]
    summary[lab] = {"cases": len(cases), "reps": len(reps), "decode_tps_mean_of_case_medians": round(st.mean(tps), 1),
                    "decode_tps_min_case": round(min(tps), 1), "decode_tps_max_case": round(max(tps), 1),
                    "rep_mean_tps": [round(x, 1) for x in rep_means],
                    "ttft_ms_p50": round(float(np.median([m["ttft"] for m in med[lab].values()])), 1),
                    "itl_ms_p50": round(float(np.percentile(itl, 50)), 2), "itl_ms_p95": round(float(np.percentile(itl, 95)), 2),
                    "itl_ms_p99": round(float(np.percentile(itl, 99)), 2)}
    for s in ("a", "b"):
        v = [1000 / m["ms"] for c, m in med[lab].items() if c[0] == s]
        summary[lab][f"set_{s}_tps"] = round(st.mean(v), 1) if v else None
json.dump(summary, open(f"{O}/summary.json", "w"), indent=1)
print(json.dumps(summary, indent=1))
ld = [l for l in med if l.startswith("llama-dspark")]
best_ld = max(ld, key=lambda l: summary[l]["decode_tps_mean_of_case_medians"]) if ld else None
pairs = [("llama-ar", "astral-ar"), (best_ld, "astral-dspark"), ("astral-ar", "astral-dspark"), ("llama-ar", best_ld)]
for b, c in pairs:
    if b not in med or c not in med:
        continue
    path = f"{O}/pair_{b}__{c}.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["pair_id", "case_id", "stratum", "baseline_ms", "candidate_ms"])
        for i, cs in enumerate(sorted(med[b])):
            w.writerow([i, f"{cs[0]}{cs[1]:02d}", "decode", f"{med[b][cs]['ms']:.4f}", f"{med[c][cs]['ms']:.4f}"])
    print(path)
