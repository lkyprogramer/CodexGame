import unittest

from reconcile.matcher import find_discrepancies
from reconcile.models import Row
from reconcile.report import render_summary


class ReconcileTests(unittest.TestCase):
    def test_detects_missing_amount_mismatch_and_duplicate(self) -> None:
        left = [
            Row("O-1", "P-1", 100, "SETTLED"),
            Row("O-2", "P-2", 200, "SETTLED"),
            Row("O-2", "P-2", 200, "SETTLED"),
            Row("O-3", "P-3", 300, "REFUNDED"),
        ]
        right = [
            Row("O-1", "P-1", 100, "SETTLED"),
            Row("O-2", "P-2", 250, "SETTLED"),
            Row("O-4", "P-4", 900, "SETTLED"),
        ]
        discrepancies = find_discrepancies(left, right)
        kinds = sorted(item.kind for item in discrepancies)
        self.assertEqual(kinds, ["amount_mismatch", "duplicate_left", "missing_left", "missing_right"])

    def test_summary_mentions_counts(self) -> None:
        left = [Row("O-1", "P-1", 100, "SETTLED")]
        right = [Row("O-2", "P-2", 100, "SETTLED")]
        summary = render_summary(find_discrepancies(left, right))
        self.assertIn("missing_left=1", summary)
        self.assertIn("missing_right=1", summary)


if __name__ == "__main__":
    unittest.main()
