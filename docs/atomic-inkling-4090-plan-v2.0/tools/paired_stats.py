#!/usr/bin/env python3
"""Case-weighted paired latency statistics; never a qualification verdict."""
import argparse
import csv
import json
import math
from pathlib import Path
import random

FIELDS = ["pair_id", "case_id", "stratum", "baseline_ms", "candidate_ms"]


def analyze(stream, bootstrap=10000, seed=20261125):
    if not isinstance(bootstrap, int) or bootstrap < 1:
        raise ValueError("bootstrap must be a positive integer")
    reader = csv.DictReader(stream, strict=True)
    if reader.fieldnames != FIELDS:
        raise ValueError("CSV header must be exactly: " + ",".join(FIELDS))
    cases, pairs, strata = {}, set(), set()
    for line, row in enumerate(reader, 2):
        if None in row or any(row.get(key) is None for key in FIELDS):
            raise ValueError("wrong field count at row " + str(line))
        pair, case, stratum = (row[key].strip() for key in FIELDS[:3])
        if not pair or not case or not stratum:
            raise ValueError("empty identifier at row " + str(line))
        if pair in pairs:
            raise ValueError("duplicate pair_id: " + pair)
        baseline, candidate = (float(row[key]) for key in FIELDS[3:])
        if not all(math.isfinite(x) and x > 0 for x in (baseline, candidate)):
            raise ValueError("latencies must be positive and finite at row " + str(line))
        pairs.add(pair)
        strata.add(stratum)
        if len(strata) != 1:
            raise ValueError("mixed strata: analyze each stratum separately")
        ratio = baseline / candidate
        effect = math.log(ratio) if 0 < ratio < math.inf else math.log(baseline) - math.log(candidate)
        cases.setdefault(case, []).append(effect)
    if not cases:
        raise ValueError("CSV contains no observations")
    effects = [math.fsum(cases[key]) / len(cases[key]) for key in sorted(cases)]
    mean = math.fsum(effects) / len(effects)
    enough = len(effects) >= 30

    def metrics(log_speedup):
        try:
            speedup, reduction = math.exp(log_speedup), -math.expm1(-log_speedup)
        except OverflowError as error:
            raise ValueError("derived statistics exceed finite float range") from error
        if speedup <= 0 or not math.isfinite(speedup) or not math.isfinite(reduction):
            raise ValueError("derived statistics exceed finite float range")
        return speedup, reduction

    speedup, reduction = metrics(mean)
    speed_ci = reduction_ci = None
    if enough:
        rng = random.Random(seed)
        draws = sorted(math.fsum(rng.choices(effects, k=len(effects))) / len(effects)
                       for _ in range(bootstrap))
        endpoints = []
        for probability in (0.025, 0.975):
            index = probability * (bootstrap - 1)
            lo, hi = math.floor(index), math.ceil(index)
            endpoints.append(metrics(draws[lo] + (draws[hi] - draws[lo]) * (index - lo)))
        speed_ci, reduction_ci = [x[0] for x in endpoints], [x[1] for x in endpoints]
    return {"evidence_kind": "derived_statistics", "stratum": next(iter(strata)),
            "evidence_status": "INTERVAL_ESTIMATE_ONLY" if enough else "INSUFFICIENT_EVIDENCE",
            "case_count": len(effects), "pair_count": len(pairs), "gmean_speedup": speedup,
            "latency_reduction": reduction, "speedup_ci95": speed_ci,
            "latency_reduction_ci95": reduction_ci, "bootstrap_requested": bootstrap,
            "bootstrap_used": bootstrap if enough else 0, "seed": seed,
            "method": "equal-weight case log effects; percentile case bootstrap in log space",
            "qualification": "NOT_ASSESSED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20261125)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if Path(args.input).resolve() == Path(args.output).resolve():
            raise ValueError("output must not overwrite the input CSV")
        with open(args.input, newline="", encoding="utf-8-sig") as stream:
            result = analyze(stream, args.bootstrap, args.seed)
        Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, csv.Error) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()

