"""ABBA pairing and A/A noise floor from raw measurements (not a PASS oracle)."""
from __future__ import annotations

from typing import Sequence


def aa_noise_pct(values: Sequence[float]) -> float:
    """Peak-to-mean relative range in percent: 100 * (max-min) / mean.

    Empty or zero-mean input raises; a single sample is 0%.
    """
    xs = [float(v) for v in values]
    if not xs:
        raise ValueError("aa_noise_pct requires at least one sample")
    mean = sum(xs) / len(xs)
    if mean == 0.0:
        raise ValueError("aa_noise_pct mean is 0")
    if len(xs) == 1:
        return 0.0
    return 100.0 * (max(xs) - min(xs)) / mean


def abba_deltas(a: Sequence[float], b: Sequence[float]) -> list[float]:
    """Per-pair B-A on aligned sequences (higher is better for throughput)."""
    if len(a) != len(b):
        raise ValueError(f"abba_deltas length mismatch {len(a)} vs {len(b)}")
    if len(a) < 8:
        raise ValueError(f"need >=8 ABBA pairs, got {len(a)}")
    return [float(bb) - float(aa) for aa, bb in zip(a, b)]


def abba_mean_uplift_pct(a: Sequence[float], b: Sequence[float]) -> float:
    xs = [float(v) for v in a]
    mean_a = sum(xs) / len(xs)
    if mean_a == 0.0:
        raise ValueError("baseline mean is 0")
    deltas = abba_deltas(a, b)
    mean_d = sum(deltas) / len(deltas)
    return 100.0 * mean_d / mean_a


def abba_pair_means(pairs: Sequence[dict]) -> tuple[list[float], list[float]]:
    """pairs: [{a1,a2,b1,b2}, ...] -> (A_means, B_means) length == n pairs."""
    if len(pairs) < 8:
        raise ValueError(f"need >=8 ABBA pairs, got {len(pairs)}")
    a_means = []
    b_means = []
    for i, p in enumerate(pairs):
        a_means.append((float(p["a1"]) + float(p["a2"])) / 2.0)
        b_means.append((float(p["b1"]) + float(p["b2"])) / 2.0)
    return a_means, b_means


def aa_noise_from_a_legs(pairs: Sequence[dict]) -> float:
    xs = []
    for p in pairs:
        xs.append(float(p["a1"]))
        xs.append(float(p["a2"]))
    return aa_noise_pct(xs)
