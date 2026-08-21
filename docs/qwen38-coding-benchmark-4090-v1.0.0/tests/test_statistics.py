from __future__ import annotations

import unittest

from qcb.statistics import holm_adjust, mcnemar_exact, paired_rows, stratified_paired_bootstrap
from tests.helpers import row


class StatisticsTest(unittest.TestCase):
    def test_pairs_by_task_and_seed(self) -> None:
        left = [row("SF001", "single_file", seed=1), row("BF001", "bug_fix", seed=2)]
        right = [row("BF001", "bug_fix", model="b", seed=2), row("SF001", "single_file", model="b", seed=1)]
        pairs = paired_rows(left, right)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0][0]["task"]["id"], "BF001")

    def test_mcnemar_counts_discordant_pairs(self) -> None:
        pairs = [
            (row("A", "single_file", passed=True), row("A", "single_file", model="b", passed=False)),
            (row("B", "single_file", passed=False), row("B", "single_file", model="b", passed=True)),
            (row("C", "single_file", passed=False), row("C", "single_file", model="b", passed=True)),
        ]
        result = mcnemar_exact(pairs)
        self.assertEqual(result["a_only_pass"], 1)
        self.assertEqual(result["b_only_pass"], 2)
        self.assertEqual(result["discordant"], 3)

    def test_bootstrap_is_deterministic(self) -> None:
        pairs = [
            (row("SF001", "single_file", passed=False), row("SF001", "single_file", model="b", passed=True)),
            (row("BF001", "bug_fix", passed=False), row("BF001", "bug_fix", model="b", passed=True)),
        ]
        first = stratified_paired_bootstrap(pairs, lambda x: float(x["verification"]["passed"]), iterations=100, seed=7)
        second = stratified_paired_bootstrap(pairs, lambda x: float(x["verification"]["passed"]), iterations=100, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(first["observed_difference"], 1.0)

    def test_holm_adjust_is_monotonic(self) -> None:
        adjusted = holm_adjust({"a": 0.01, "b": 0.03, "c": 0.2})
        self.assertLessEqual(adjusted["a"], adjusted["b"])
        self.assertLessEqual(adjusted["b"], adjusted["c"])


if __name__ == "__main__":
    unittest.main()
