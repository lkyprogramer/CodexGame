#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qcb.catalog import Task, discover_tasks
from qcb.util import dump_json
from qcb.verifier import verify_task


def _copy_with_reference(task: Task, destination: Path) -> Path | None:
    shutil.copytree(task.workspace_dir, destination)
    if task.task_type == "review":
        return task.task_dir / "reference" / "answer.json"
    shutil.copytree(task.task_dir / "reference", destination, dirs_exist_ok=True)
    return None


def _baseline_answer(task: Task, workspace: Path) -> Path | None:
    if task.task_type != "review":
        return None
    answer = workspace / "answer.json"
    answer.write_text('{"issues": [], "summary": ""}\n', encoding="utf-8")
    return answer


def _verify_one(task: Task, include_baseline: bool, baseline_timeout: float) -> tuple[dict[str, Any], dict[str, Any] | None]:
    with tempfile.TemporaryDirectory(prefix=f"qcb-ref-{task.id}-") as temp:
        workspace = Path(temp) / "workspace"
        answer = _copy_with_reference(task, workspace)
        reference = {"task_id": task.id, **verify_task(task, workspace, answer_file=answer, timeout=240)}

    baseline: dict[str, Any] | None = None
    if include_baseline:
        with tempfile.TemporaryDirectory(prefix=f"qcb-base-{task.id}-") as temp:
            workspace = Path(temp) / "workspace"
            shutil.copytree(task.workspace_dir, workspace)
            answer = _baseline_answer(task, workspace)
            baseline = {"task_id": task.id, **verify_task(task, workspace, answer_file=answer, timeout=baseline_timeout)}
    return reference, baseline


def verify_all(
    root: Path,
    *,
    include_baselines: bool = True,
    workers: int = 6,
    baseline_timeout: float = 25.0,
    task_ids: set[str] | None = None,
    prefixes: tuple[str, ...] = (),
) -> dict[str, Any]:
    tasks = discover_tasks(root)
    if task_ids:
        tasks = [task for task in tasks if task.id in task_ids]
    if prefixes:
        tasks = [task for task in tasks if task.id.startswith(prefixes)]
    if not tasks:
        raise ValueError("No tasks selected")
    reference_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(_verify_one, task, include_baselines, baseline_timeout): task
            for task in tasks
        }
        for future in concurrent.futures.as_completed(futures):
            task = futures[future]
            try:
                reference, baseline = future.result()
            except Exception as exc:
                reference = {
                    "task_id": task.id,
                    "passed": False,
                    "tests_passed": 0,
                    "tests_total": 1,
                    "score": 0.0,
                    "error": f"validation harness error: {type(exc).__name__}: {exc}",
                }
                baseline = None
            reference_rows.append(reference)
            print(f"[{'PASS' if reference['passed'] else 'FAIL'}] reference {task.id}", flush=True)
            if include_baselines:
                if baseline is None:
                    baseline = {
                        "task_id": task.id,
                        "passed": True,
                        "tests_passed": 1,
                        "tests_total": 1,
                        "score": 1.0,
                        "error": "baseline validation missing",
                    }
                baseline_rows.append(baseline)
                print(f"[{'EXPECTED-FAIL' if not baseline['passed'] else 'UNEXPECTED-PASS'}] baseline {task.id}", flush=True)

    reference_rows.sort(key=lambda row: row["task_id"])
    baseline_rows.sort(key=lambda row: row["task_id"])
    reference_failures = [row["task_id"] for row in reference_rows if not row["passed"]]
    baseline_passes = [row["task_id"] for row in baseline_rows if row["passed"]]
    passed = not reference_failures and (not include_baselines or not baseline_passes)
    return {
        "passed": passed,
        "reference_total": len(reference_rows),
        "reference_passed": len(reference_rows) - len(reference_failures),
        "reference_failures": reference_failures,
        "baseline_total": len(baseline_rows),
        "baseline_failed_as_expected": len(baseline_rows) - len(baseline_passes),
        "baseline_unexpected_passes": baseline_passes,
        "baseline_timeout_seconds": baseline_timeout,
        "workers": workers,
        "references": reference_rows,
        "baselines": baseline_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify all reference solutions and intentionally failing baselines")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--reference-only", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--baseline-timeout", type=float, default=25.0)
    parser.add_argument("--task", action="append", help="Restrict to exact task ID; repeatable")
    parser.add_argument("--prefix", action="append", help="Restrict to task ID prefix, e.g. SF; repeatable")
    parser.add_argument("--json")
    args = parser.parse_args()
    result = verify_all(
        Path(args.root).resolve(),
        include_baselines=not args.reference_only,
        workers=args.workers,
        baseline_timeout=args.baseline_timeout,
        task_ids=set(args.task or []),
        prefixes=tuple(args.prefix or []),
    )
    if args.json:
        dump_json(args.json, result)
    summary = {key: value for key, value in result.items() if key not in {"references", "baselines"}}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
