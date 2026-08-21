from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qcb.leaderboard import build_leaderboard, render_leaderboard
from qcb.report import generate_comparison_report, generate_model_report
from qcb.util import append_jsonl
from tests.helpers import row


class ReportTest(unittest.TestCase):
    def _write(self, path: Path, model: str, passes: list[bool]) -> None:
        categories = ["single_file", "bug_fix", "repo_engineering", "agent_tool", "long_context", "code_review"]
        for index, (category, passed) in enumerate(zip(categories, passes), 1):
            append_jsonl(path, row(f"T{index}", category, model=model, passed=passed, seed=42, wall=10 + index))

    def test_generates_model_comparison_and_leaderboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = root / "a.jsonl"
            b = root / "b.jsonl"
            self._write(a, "a", [True, True, True, False, True, True])
            self._write(b, "b", [True, True, True, True, True, True])
            model_report = root / "model.md"
            comparison = root / "comparison.md"
            leaderboard = root / "leaderboard.md"
            generate_model_report(a, model_report)
            generate_comparison_report(a, b, comparison)
            data = build_leaderboard([a, b])
            render_leaderboard(data, leaderboard)
            self.assertIn("Hard Task Success Rate", model_report.read_text(encoding="utf-8"))
            self.assertIn("配对统计", comparison.read_text(encoding="utf-8"))
            self.assertIn("QCB-4090 多模型排行榜", leaderboard.read_text(encoding="utf-8"))
            self.assertEqual(data["models"][0]["model_id"], "b")


if __name__ == "__main__":
    unittest.main()
