import unittest
from pathlib import Path

from analyzer import summarize


class AnalyzerTests(unittest.TestCase):
    def test_tolerates_bad_lines_and_counts_events(self) -> None:
        counts = summarize(Path("sample.jsonl"))
        self.assertEqual(counts["turn.start"], 2)
        self.assertEqual(counts["turn.end"], 1)
        self.assertEqual(counts["build.result"], 1)


if __name__ == "__main__":
    unittest.main()
