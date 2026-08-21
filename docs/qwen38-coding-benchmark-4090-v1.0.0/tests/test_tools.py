from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qcb.tools import AgentWorkspace, READ_ONLY_TOOL_DEFINITIONS, parse_tool_arguments


class ToolsTest(unittest.TestCase):
    def test_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = AgentWorkspace(temp)
            with self.assertRaises(ValueError):
                workspace.read_file("../secret.txt")

    def test_read_file_is_line_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.txt").write_text("a\nb\nc\n", encoding="utf-8")
            result = AgentWorkspace(root).read_file("a.txt", 2, 3)
            self.assertTrue(result["ok"])
            self.assertEqual(result["content"], "2: b\n3: c")

    def test_invalid_tool_json_becomes_empty_arguments(self) -> None:
        self.assertEqual(parse_tool_arguments("not-json"), {})

    def test_review_tool_set_is_read_only(self) -> None:
        names = {tool["function"]["name"] for tool in READ_ONLY_TOOL_DEFINITIONS}
        self.assertEqual(names, {"list_files", "read_file", "search"})

    def test_public_test_failure_is_valid_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = AgentWorkspace(temp, ["python3", "-c", "raise SystemExit(1)"])
            result = workspace.run_tests()
            self.assertTrue(result["invocation_valid"])
            self.assertFalse(result["ok"])

    def test_execute_converts_path_escape_to_invalid_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = AgentWorkspace(temp).execute("read_file", {"path": "../secret"})
            self.assertFalse(result["invocation_valid"])
            self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
