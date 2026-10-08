"""Assert Suffix+MTP v1 from shipped live ABBA JSON (A-B-B-A x8)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from abba import aa_noise_from_a_legs, abba_mean_uplift_pct, abba_pair_means

DATA = Path(__file__).resolve().parent / "testdata" / "suffix-mtp-v1.json"


class TestSuffixMtpV1Raw(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = json.loads(DATA.read_text())

    def test_eight_abba_pairs(self) -> None:
        pairs = self.raw["pairs"]
        self.assertEqual(len(pairs), 8)
        self.assertEqual(self.raw["pattern"], "ABBA x8")
        for p in pairs:
            self.assertIn("a1", p)
            self.assertIn("b1", p)
            self.assertIn("b2", p)
            self.assertIn("a2", p)
        noise = aa_noise_from_a_legs(pairs)
        self.assertLessEqual(noise, 3.0, noise)
        self.assertAlmostEqual(noise, self.raw["aa_noise_pct_from_A_legs"], places=6)

    def test_w5_slower_than_w3(self) -> None:
        a, b = abba_pair_means(self.raw["pairs"])
        uplift = abba_mean_uplift_pct(a, b)
        self.assertLess(uplift, 0.0)
        self.assertAlmostEqual(uplift, self.raw["W5_vs_W3_uplift_pct"], places=6)
        self.assertEqual(self.raw["ctx"], 200192)

    def test_negative_control_nospec(self) -> None:
        ns = self.raw["NOSPEC"]
        self.assertEqual(len(ns), 8)
        a, _ = abba_pair_means(self.raw["pairs"])
        mean_a = sum(a) / len(a)
        mean_ns = sum(ns) / len(ns)
        self.assertGreater(mean_a, mean_ns * 1.5)
        self.assertTrue(self.raw["negative_control_pass"])


if __name__ == "__main__":
    unittest.main()
