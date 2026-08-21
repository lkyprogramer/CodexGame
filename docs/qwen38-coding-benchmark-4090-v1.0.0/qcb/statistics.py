from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any, Callable


def paired_rows(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    def key(row: dict[str, Any]) -> tuple[str, int]:
        return row["task"]["id"], int(row.get("seed", 0))
    left = {key(row): row for row in a}
    right = {key(row): row for row in b}
    return [(left[k], right[k]) for k in sorted(left.keys() & right.keys())]


def stratified_paired_bootstrap(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    metric: Callable[[dict[str, Any]], float],
    *,
    iterations: int = 10000,
    seed: int = 20260820,
) -> dict[str, float]:
    if not pairs:
        raise ValueError("No paired rows")
    strata: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for left, right in pairs:
        strata[left["task"]["category"]].append((left, right))
    rng = random.Random(seed)
    diffs: list[float] = []
    for _ in range(iterations):
        stratum_diffs: list[float] = []
        for group in strata.values():
            sample = [rng.choice(group) for _ in group]
            stratum_diffs.append(sum(metric(r) - metric(l) for l, r in sample) / len(sample))
        diffs.append(sum(stratum_diffs) / len(stratum_diffs))
    diffs.sort()
    observed_strata = [
        sum(metric(right) - metric(left) for left, right in group) / len(group)
        for group in strata.values()
    ]
    observed = sum(observed_strata) / len(observed_strata)
    return {
        "observed_difference": observed,
        "ci95_low": diffs[int(0.025 * (len(diffs) - 1))],
        "ci95_high": diffs[int(0.975 * (len(diffs) - 1))],
        "probability_positive": sum(1 for x in diffs if x > 0) / len(diffs),
    }


def mcnemar_exact(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, float | int]:
    b = 0  # A pass, B fail
    c = 0  # A fail, B pass
    for left, right in pairs:
        lp = bool(left.get("verification", {}).get("passed"))
        rp = bool(right.get("verification", {}).get("passed"))
        if lp and not rp:
            b += 1
        elif rp and not lp:
            c += 1
    n = b + c
    if n == 0:
        p = 1.0
    else:
        k = min(b, c)
        tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
        p = min(1.0, 2 * tail)
    return {"a_only_pass": b, "b_only_pass": c, "discordant": n, "p_value_two_sided": p}


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda x: x[1])
    count = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for index, (name, value) in enumerate(ordered):
        candidate = min(1.0, value * (count - index))
        running = max(running, candidate)
        adjusted[name] = running
    return adjusted
