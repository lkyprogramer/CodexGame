from __future__ import annotations

import unittest

from qcb.metrics import aggregate_results
from tests.helpers import row


class MetricsTest(unittest.TestCase):
    def test_category_balanced_index_equal_weights_categories(self) -> None:
        rows = [
            row("SF001", "single_file", passed=True),
            row("SF002", "single_file", passed=True),
            row("BF001", "bug_fix", passed=False, score=0.5),
        ]
        summary = aggregate_results(rows)
        self.assertAlmostEqual(summary["categories"]["single_file"]["category_index"], 1.0)
        self.assertAlmostEqual(summary["categories"]["bug_fix"]["category_index"], 0.1)
        self.assertAlmostEqual(summary["category_balanced_index"], 0.55)
        self.assertAlmostEqual(summary["hard_task_success_rate"], 2 / 3)

    def test_missing_reasoning_tokens_stays_na(self) -> None:
        summary = aggregate_results([row("SF001", "single_file", reasoning_tokens=None)])
        self.assertIsNone(summary["median_reasoning_tokens"])

    def test_fast_failure_not_used_as_success_latency(self) -> None:
        rows = [
            row("SF001", "single_file", passed=True, wall=30.0),
            row("BF001", "bug_fix", passed=False, wall=1.0),
        ]
        summary = aggregate_results(rows)
        self.assertEqual(summary["median_success_wall_seconds"], 30.0)


if __name__ == "__main__":
    unittest.main()
