from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .patching import apply_unified_diff
from .util import run_process, safe_relative


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in the repository. Hidden tests are not available.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "default": "."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 source file from the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "default": 1},
                    "end_line": {"type": "integer", "default": 400},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search literal text recursively in repository files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "max_results": {"type": "integer", "default": 80},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": "Apply one unified diff to the repository.",
            "parameters": {
                "type": "object",
                "properties": {"patch": {"type": "string"}},
                "required": ["patch"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run the task's public test command. It never runs hidden tests.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

READ_ONLY_TOOL_DEFINITIONS = [
    tool for tool in TOOL_DEFINITIONS
    if tool.get("function", {}).get("name") in {"list_files", "read_file", "search"}
]


class AgentWorkspace:
    def __init__(self, root: str | Path, public_test_command: list[str] | None = None):
        self.root = Path(root).resolve()
        self.public_test_command = public_test_command

    def _path(self, value: str) -> Path:
        target = (self.root / safe_relative(value)).resolve()
        if self.root not in target.parents and target != self.root:
            raise ValueError("Path escapes workspace")
        return target

    def list_files(self, path: str = ".") -> dict[str, Any]:
        target = self._path(path)
        files: list[str] = []
        if target.is_file():
            files = [str(target.relative_to(self.root))]
        elif target.exists():
            for item in sorted(target.rglob("*")):
                if item.is_file() and ".git" not in item.parts:
                    files.append(str(item.relative_to(self.root)))
                    if len(files) >= 1000:
                        break
        return {"invocation_valid": True, "ok": target.exists(), "files": files}

    def read_file(self, path: str, start_line: int = 1, end_line: int = 400) -> dict[str, Any]:
        target = self._path(path)
        if not target.is_file():
            return {"invocation_valid": True, "ok": False, "error": "file not found"}
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(1, int(start_line))
        end = max(start, min(int(end_line), start + 999))
        body = "\n".join(f"{idx}: {lines[idx-1]}" for idx in range(start, min(end, len(lines)) + 1))
        return {"invocation_valid": True, "ok": True, "path": path, "start_line": start, "end_line": min(end, len(lines)), "content": body}

    def search(self, query: str, path: str = ".", max_results: int = 80) -> dict[str, Any]:
        if not query:
            return {"invocation_valid": False, "ok": False, "error": "empty query"}
        target = self._path(path)
        result = run_process(
            ["grep", "-R", "-n", "-F", "--exclude-dir=.git", "--", query, str(target)],
            cwd=self.root,
            timeout=20,
        )
        lines = result.stdout.splitlines()[: max(1, min(int(max_results), 200))]
        normalized = [line.replace(str(self.root) + os.sep, "") for line in lines]
        return {"invocation_valid": True, "ok": result.returncode in {0, 1}, "matches": normalized, "truncated": len(result.stdout.splitlines()) > len(lines)}

    def apply_patch(self, patch: str) -> dict[str, Any]:
        ok, output = apply_unified_diff(self.root, patch)
        return {"invocation_valid": True, "ok": ok, "output": output}

    def run_tests(self) -> dict[str, Any]:
        if not self.public_test_command:
            return {"invocation_valid": False, "ok": False, "error": "This task has no public test command"}
        result = run_process(self.public_test_command, cwd=self.root, timeout=180)
        return {
            "invocation_valid": True,
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-12000:],
        }

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "list_files":
                return self.list_files(**arguments)
            if name == "read_file":
                return self.read_file(**arguments)
            if name == "search":
                return self.search(**arguments)
            if name == "apply_patch":
                return self.apply_patch(**arguments)
            if name == "run_tests":
                if arguments:
                    return {"invocation_valid": False, "ok": False, "error": "run_tests accepts no arguments"}
                return self.run_tests()
            return {"invocation_valid": False, "ok": False, "error": f"Unknown tool: {name}"}
        except (TypeError, ValueError) as exc:
            return {
                "invocation_valid": False,
                "ok": False,
                "error": f"Invalid tool arguments: {type(exc).__name__}: {exc}",
            }


def parse_tool_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if raw is None or raw == "":
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}
