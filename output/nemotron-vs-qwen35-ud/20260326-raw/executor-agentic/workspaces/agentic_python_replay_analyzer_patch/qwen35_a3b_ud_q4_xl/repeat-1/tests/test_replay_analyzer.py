import unittest
from pathlib import Path

from scripts.replay_analyzer import analyze


class ReplayAnalyzerTests(unittest.TestCase):
    def test_streaming_analysis(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = analyze(str(repo_root / "data" / "replay.jsonl"))
        self.assertEqual(result["malformed_lines"], 1)
        self.assertEqual(result["sessions"]["s1"]["turns"], 2)
        self.assertEqual(result["sessions"]["s1"]["invalid_output"], 1)
        self.assertEqual(result["sessions"]["s2"]["turns"], 2)
        self.assertEqual(result["sessions"]["s2"]["invalid_output"], 1)


if __name__ == "__main__":
    unittest.main()
