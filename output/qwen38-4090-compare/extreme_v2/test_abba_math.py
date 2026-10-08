"""Unit tests for ABBA helpers — drive the shipped functions, no hardcoded PASS oracle."""
from __future__ import annotations

import unittest

from abba import aa_noise_pct, abba_deltas, abba_mean_uplift_pct, abba_pair_means, aa_noise_from_a_legs


class TestAbbaMath(unittest.TestCase):
    def test_aa_noise_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            aa_noise_pct([])

    def test_aa_noise_single_is_zero(self) -> None:
        self.assertEqual(aa_noise_pct([10.0]), 0.0)

    def test_aa_noise_from_raw_spread(self) -> None:
        xs = [100.0, 101.0, 99.5, 100.5, 100.2, 99.8, 100.1, 100.4]
        n = aa_noise_pct(xs)
        self.assertGreater(n, 0.0)
        self.assertLessEqual(n, 3.0)

    def test_aa_noise_over_floor(self) -> None:
        xs = [100.0, 110.0]
        self.assertGreater(aa_noise_pct(xs), 3.0)

    def test_abba_requires_eight_pairs(self) -> None:
        with self.assertRaises(ValueError):
            abba_deltas([1] * 7, [1] * 7)

    def test_abba_uplift_uses_paired_raw(self) -> None:
        a = [100.0] * 8
        b = [110.0] * 8
        self.assertAlmostEqual(abba_mean_uplift_pct(a, b), 10.0, places=6)
        self.assertEqual(abba_deltas(a, b), [10.0] * 8)


    def test_abba_pair_means_eight(self) -> None:
        pairs = [{"a1": 100.0, "a2": 102.0, "b1": 90.0, "b2": 91.0} for _ in range(8)]
        a, b = abba_pair_means(pairs)
        self.assertEqual(len(a), 8)
        self.assertAlmostEqual(a[0], 101.0)
        self.assertAlmostEqual(b[0], 90.5)
        noise = aa_noise_from_a_legs(pairs)
        self.assertGreaterEqual(noise, 0.0)
        self.assertLess(abba_mean_uplift_pct(a, b), 0.0)

    def test_abba_pair_means_rejects_short(self) -> None:
        with self.assertRaises(ValueError):
            abba_pair_means([{"a1":1,"a2":1,"b1":1,"b2":1}]*7)

if __name__ == "__main__":
    unittest.main()
