from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path

from qcb.catalog import discover_tasks, load_suite


class CatalogTest(unittest.TestCase):
    def test_catalog_has_frozen_shape(self) -> None:
        root = Path(__file__).resolve().parents[1]
        tasks = discover_tasks(root)
        self.assertEqual(len(tasks), 48)
        self.assertEqual(
            Counter(task.category for task in tasks),
            Counter({
                "single_file": 12,
                "bug_fix": 10,
                "repo_engineering": 12,
                "agent_tool": 6,
                "long_context": 4,
                "code_review": 4,
            }),
        )
        self.assertEqual(len(load_suite(root, "smoke")), 12)
        self.assertEqual(len(load_suite(root, "core")), 32)
        self.assertEqual(len(load_suite(root, "full")), 48)
        self.assertEqual(len(load_suite(root, "finalists")), 27)


if __name__ == "__main__":
    unittest.main()
