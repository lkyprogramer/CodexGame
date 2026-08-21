from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qcb.audit import audit_result_file


class ResultAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.source = self.root / "examples" / "synthetic-original-normalized-smoke.jsonl"

    def test_complete_synthetic_smoke_result_passes(self) -> None:
        result = audit_result_file(self.root, self.source)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["rows"], 36)
        self.assertEqual(result["expected_pairs"], 36)
        self.assertEqual(result["actual_unique_pairs"], 36)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["duplicates"], [])

    def test_missing_task_seed_pair_fails(self) -> None:
        rows = [json.loads(line) for line in self.source.read_text(encoding="utf-8").splitlines() if line.strip()]
        with tempfile.TemporaryDirectory() as temp:
            result_file = Path(temp) / "incomplete.jsonl"
            result_file.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows[:-1]) + "\n",
                encoding="utf-8",
            )
            result = audit_result_file(self.root, result_file)
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["missing"]), 1)
        self.assertTrue(any(message.startswith("Missing task/seed pairs") for message in result["errors"]))

    def test_duplicate_task_seed_pair_fails(self) -> None:
        rows = [json.loads(line) for line in self.source.read_text(encoding="utf-8").splitlines() if line.strip()]
        with tempfile.TemporaryDirectory() as temp:
            result_file = Path(temp) / "duplicate.jsonl"
            result_file.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows + [rows[0]]) + "\n",
                encoding="utf-8",
            )
            result = audit_result_file(self.root, result_file)
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["duplicates"]), 1)
        self.assertTrue(any(message.startswith("Duplicate task/seed pairs") for message in result["errors"]))


if __name__ == "__main__":
    unittest.main()
