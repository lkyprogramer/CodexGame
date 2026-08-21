from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qcb.patching import apply_unified_diff, extract_unified_diff, initialize_git


class PatchingTest(unittest.TestCase):
    def test_extracts_fenced_diff(self) -> None:
        text = """Explanation\n```diff\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n```\n"""
        patch = extract_unified_diff(text)
        self.assertIsNotNone(patch)
        self.assertIn("+new", patch or "")

    def test_applies_patch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.txt").write_text("old\n", encoding="utf-8")
            initialize_git(root)
            patch = "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
            ok, output = apply_unified_diff(root, patch)
            self.assertTrue(ok, output)
            self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "new\n")


if __name__ == "__main__":
    unittest.main()
