from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .catalog import load_suite
from .util import read_jsonl, utc_now


def audit_result_file(
    benchmark_root: str | Path,
    result_file: str | Path,
    *,
    check_artifacts: bool = False,
) -> dict[str, Any]:
    root = Path(benchmark_root).resolve()
    rows = read_jsonl(result_file)
    errors: list[str] = []
    warnings: list[str] = []
    if not rows:
        return {"passed": False, "errors": ["Result file is empty"], "warnings": [], "rows": 0}

    model_ids = {str(row.get("model", {}).get("id")) for row in rows}
    lanes = {str(row.get("lane")) for row in rows}
    suites = {str(row.get("suite")) for row in rows}
    config_hashes = {str(row.get("config", {}).get("sha256")) for row in rows}
    inference_signatures = {
        (
            row.get("inference", {}).get("temperature"),
            row.get("inference", {}).get("top_p"),
            row.get("inference", {}).get("top_k"),
            row.get("inference", {}).get("min_p"),
            row.get("inference", {}).get("max_tokens"),
            row.get("inference", {}).get("context_size"),
            row.get("inference", {}).get("reasoning_effort"),
            row.get("inference", {}).get("mtp_enabled"),
            row.get("inference", {}).get("system_prompt_sha256"),
        )
        for row in rows
    }

    if len(model_ids) != 1:
        errors.append(f"Mixed model IDs: {sorted(model_ids)}")
    if len(lanes) != 1:
        errors.append(f"Mixed lanes: {sorted(lanes)}")
    if len(suites) != 1:
        errors.append(f"Mixed suites: {sorted(suites)}")
    if len(config_hashes) != 1:
        errors.append("Mixed config SHA-256 values")
    if len(inference_signatures) != 1:
        errors.append("Mixed controlled inference parameters")

    suite_name = next(iter(suites)) if len(suites) == 1 else None
    expected_tasks: set[str] = set()
    if suite_name:
        try:
            expected_tasks = {task.id for task in load_suite(root, suite_name)}
        except Exception as exc:
            errors.append(f"Cannot load suite {suite_name}: {exc}")

    seeds = sorted({int(row.get("seed", 0)) for row in rows})
    keys = [(str(row.get("task", {}).get("id")), int(row.get("seed", 0))) for row in rows]
    counts = Counter(keys)
    duplicates = sorted([{"task_id": task_id, "seed": seed, "count": count} for (task_id, seed), count in counts.items() if count > 1], key=lambda x: (x["task_id"], x["seed"]))
    if duplicates:
        errors.append(f"Duplicate task/seed pairs: {len(duplicates)}")

    expected_keys = {(task_id, seed) for task_id in expected_tasks for seed in seeds}
    actual_keys = set(keys)
    missing = sorted(expected_keys - actual_keys)
    unexpected = sorted(actual_keys - expected_keys) if expected_tasks else []
    if missing:
        errors.append(f"Missing task/seed pairs: {len(missing)}")
    if unexpected:
        errors.append(f"Unexpected task/seed pairs: {len(unexpected)}")

    hash_statuses = Counter(str(row.get("model", {}).get("hash_status", "missing")) for row in rows)
    if "mismatch" in hash_statuses:
        errors.append("At least one row records model hash mismatch")
    if hash_statuses.get("not_configured", 0):
        warnings.append("Model file hash was not configured for some rows")

    artifact_missing: list[str] = []
    if check_artifacts:
        for row in rows:
            artifact = Path(str(row.get("artifacts", "")))
            required = ["final-response.txt", "final.patch", "raw-responses.json", "tool-trace.json", "verification.json"]
            if not artifact.is_dir() or any(not (artifact / name).is_file() for name in required):
                artifact_missing.append(str(row.get("run_id")))
        if artifact_missing:
            errors.append(f"Missing artifact directories/files: {len(artifact_missing)}")

    infrastructure = [row.get("run_id") for row in rows if row.get("outcome") == "endpoint_error"]
    if infrastructure:
        warnings.append(f"Infrastructure-error rows present: {len(infrastructure)}")

    return {
        "generated_at": utc_now(),
        "passed": not errors,
        "result_file": str(Path(result_file).resolve()),
        "rows": len(rows),
        "model_ids": sorted(model_ids),
        "lanes": sorted(lanes),
        "suites": sorted(suites),
        "seeds": seeds,
        "expected_tasks": len(expected_tasks),
        "expected_pairs": len(expected_keys),
        "actual_unique_pairs": len(actual_keys),
        "duplicates": duplicates,
        "missing": [{"task_id": task_id, "seed": seed} for task_id, seed in missing],
        "unexpected": [{"task_id": task_id, "seed": seed} for task_id, seed in unexpected],
        "hash_statuses": dict(hash_statuses),
        "artifact_missing_run_ids": artifact_missing,
        "infrastructure_error_run_ids": infrastructure,
        "errors": errors,
        "warnings": warnings,
    }
