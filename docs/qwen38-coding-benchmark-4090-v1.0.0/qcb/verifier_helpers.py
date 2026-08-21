from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def emit(passed: int, total: int, details: list[str] | None = None, error: str | None = None) -> None:
    payload = {
        "passed": passed == total and total > 0,
        "tests_passed": passed,
        "tests_total": total,
        "score": passed / total if total else 0.0,
        "details": details or [],
    }
    if error:
        payload["error"] = error
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(0 if payload["passed"] else 1)


def run_python_unittest(workspace: str | Path, test_file: str | Path, timeout: int = 60) -> tuple[int, int, list[str]]:
    workspace = Path(workspace).resolve()
    test_file = Path(test_file).resolve()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(workspace) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, str(test_file), "-v"],
        cwd=workspace,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    output = result.stdout
    import re
    match = re.search(r"Ran (\d+) tests?", output)
    total = int(match.group(1)) if match else 1
    failures = len(re.findall(r"^(?:FAIL|ERROR):", output, flags=re.MULTILINE))
    passed = total - failures if result.returncode != 0 else total
    return max(0, passed), total, output.splitlines()[-80:]


def run_java_test(workspace: str | Path, test_main: str | Path, timeout: int = 90) -> tuple[int, int, list[str]]:
    workspace = Path(workspace).resolve()
    test_main = Path(test_main).resolve()
    with tempfile.TemporaryDirectory(prefix="qcb-java-") as build_dir:
        build = Path(build_dir)
        sources = [str(p) for p in workspace.rglob("*.java")]
        if not sources:
            return 0, 1, ["No Java source files found"]
        compile_result = subprocess.run(
            ["javac", "-encoding", "UTF-8", "-d", str(build), *sources, str(test_main)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        if compile_result.returncode != 0:
            return 0, 1, ["Compilation failed", *compile_result.stdout.splitlines()[-80:]]
        run_result = subprocess.run(
            ["java", "-ea", "-cp", str(build), "TestMain"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        output = run_result.stdout.splitlines()
        passed = 1 if run_result.returncode == 0 else 0
        return passed, 1, output[-80:]
