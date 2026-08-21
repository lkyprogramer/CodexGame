#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qcb.catalog import discover_tasks
from qcb.util import dump_json, load_json

EXPECTED_COUNTS = {
    "single_file": 12,
    "bug_fix": 10,
    "repo_engineering": 12,
    "agent_tool": 6,
    "long_context": 4,
    "code_review": 4,
}
EXPECTED_SUITES = {"smoke": 12, "core": 32, "full": 48, "finalists": 27}
REQUIRED_FIELDS = {"id", "title", "category", "language", "difficulty", "task_type"}


def validate(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    tasks = discover_tasks(root)
    ids = [task.id for task in tasks]
    counts = Counter(task.category for task in tasks)

    if len(ids) != len(set(ids)):
        errors.append("Duplicate task IDs")
    if len(tasks) != 48:
        errors.append(f"Expected 48 tasks, found {len(tasks)}")
    if dict(counts) != EXPECTED_COUNTS:
        errors.append(f"Category counts differ: expected={EXPECTED_COUNTS}, actual={dict(counts)}")

    for task in tasks:
        metadata_path = task.task_dir / "task.json"
        metadata = load_json(metadata_path)
        missing = REQUIRED_FIELDS - set(metadata)
        if missing:
            errors.append(f"{task.id}: missing fields {sorted(missing)}")
        if task.task_dir.name != task.id or metadata.get("id") != task.id:
            errors.append(f"{task.id}: directory/metadata ID mismatch")
        if not (task.task_dir / metadata.get("prompt_file", "prompt.md")).is_file():
            errors.append(f"{task.id}: prompt missing")
        if not task.workspace_dir.is_dir():
            errors.append(f"{task.id}: workspace missing")
        if not task.verifier_path.is_file():
            errors.append(f"{task.id}: verifier missing")
        reference = task.task_dir / "reference"
        if not reference.is_dir():
            errors.append(f"{task.id}: reference directory missing")
        elif task.task_type == "review" and not (reference / "answer.json").is_file():
            errors.append(f"{task.id}: review reference answer.json missing")
        if not 1 <= task.difficulty <= 5:
            errors.append(f"{task.id}: difficulty must be 1..5")
        if task.task_type not in {"patch", "agent", "review"}:
            errors.append(f"{task.id}: unsupported task_type={task.task_type}")
        for path in task.workspace_dir.rglob("*") if task.workspace_dir.exists() else []:
            lowered = {part.lower() for part in path.relative_to(task.workspace_dir).parts}
            if "hidden_tests" in lowered or "reference" in lowered:
                errors.append(f"{task.id}: leakage path inside workspace: {path.relative_to(task.workspace_dir)}")
        public = metadata.get("public_test_command")
        if public is not None and (not isinstance(public, list) or not all(isinstance(x, str) for x in public)):
            errors.append(f"{task.id}: public_test_command must be a string array")

    task_set = set(ids)
    suite_summary: dict[str, Any] = {}
    for name, expected_size in EXPECTED_SUITES.items():
        path = root / "suites" / f"{name}.json"
        if not path.is_file():
            errors.append(f"Missing suite: {name}")
            continue
        data = load_json(path)
        suite_ids = data.get("task_ids")
        if not isinstance(suite_ids, list):
            errors.append(f"{name}: task_ids is not a list")
            continue
        if len(suite_ids) != expected_size:
            errors.append(f"{name}: expected {expected_size} tasks, found {len(suite_ids)}")
        if len(suite_ids) != len(set(suite_ids)):
            errors.append(f"{name}: duplicate task IDs")
        unknown = sorted(set(suite_ids) - task_set)
        if unknown:
            errors.append(f"{name}: unknown tasks {unknown}")
        suite_summary[name] = {
            "size": len(suite_ids),
            "categories": dict(Counter(next(task.category for task in tasks if task.id == task_id) for task_id in suite_ids if task_id in task_set)),
        }

    full_ids = set(load_json(root / "suites" / "full.json").get("task_ids", [])) if (root / "suites" / "full.json").is_file() else set()
    if full_ids != task_set:
        errors.append("full suite must contain every task exactly once")

    for schema in sorted((root / "schemas").glob("*.json")):
        try:
            json.loads(schema.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON schema {schema.name}: {exc}")

    return {
        "passed": not errors,
        "task_count": len(tasks),
        "category_counts": dict(counts),
        "suites": suite_summary,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate QCB task catalog, suites, and leakage boundaries")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json")
    args = parser.parse_args()
    result = validate(Path(args.root).resolve())
    if args.json:
        dump_json(args.json, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
