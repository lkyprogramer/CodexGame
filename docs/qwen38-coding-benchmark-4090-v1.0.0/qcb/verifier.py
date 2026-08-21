from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .catalog import Task
from .util import run_process


def verify_task(task: Task, workspace: str | Path, answer_file: str | Path | None = None, timeout: float = 240) -> dict[str, Any]:
    command = [sys.executable, str(task.verifier_path), str(Path(workspace).resolve())]
    if answer_file:
        command.append(str(Path(answer_file).resolve()))
    benchmark_root = task.task_dir.parent.parent.resolve()
    env = {"PYTHONPATH": str(benchmark_root) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    try:
        result = run_process(command, cwd=benchmark_root, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        return {
            "passed": False,
            "tests_passed": 0,
            "tests_total": 1,
            "score": 0.0,
            "error": f"Verifier timeout after {timeout} seconds",
            "verifier_exit_code": 124,
            "verifier_stdout": (exc.stdout or "")[-16000:] if isinstance(exc.stdout, str) else "",
            "verifier_stderr": (exc.stderr or "")[-16000:] if isinstance(exc.stderr, str) else "",
        }
    payload: dict[str, Any] | None = None
    for line in reversed(result.stdout.splitlines()):
        try:
            candidate = json.loads(line)
            if isinstance(candidate, dict):
                payload = candidate
                break
        except json.JSONDecodeError:
            continue
    if payload is None:
        payload = {
            "passed": False,
            "tests_passed": 0,
            "tests_total": 1,
            "score": 0.0,
            "error": "Verifier did not emit JSON",
        }
    payload.setdefault("passed", False)
    payload.setdefault("tests_passed", int(bool(payload["passed"])))
    payload.setdefault("tests_total", 1)
    payload.setdefault("score", payload["tests_passed"] / max(1, payload["tests_total"]))
    payload["verifier_exit_code"] = result.returncode
    payload["verifier_stdout"] = result.stdout[-16000:]
    payload["verifier_stderr"] = result.stderr[-16000:]
    return payload
