from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from .util import percentile


CATEGORY_ORDER = ["single_file", "bug_fix", "repo_engineering", "agent_tool", "long_context", "code_review"]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _median(values: list[float]) -> float | None:
    return percentile(values, 0.5)


def _numbers(rows: list[dict[str, Any]], getter) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = getter(row)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def aggregate_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("No result rows")
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_category[row["task"]["category"]].append(row)

    categories: dict[str, Any] = {}
    category_indices: list[float] = []
    for category in CATEGORY_ORDER:
        group = by_category.get(category, [])
        if not group:
            continue
        hard = [1.0 if r.get("verification", {}).get("passed") else 0.0 for r in group]
        partial = [float(r.get("verification", {}).get("score", 0.0)) for r in group]
        category_index = 0.8 * (_mean(hard) or 0.0) + 0.2 * (_mean(partial) or 0.0)
        category_indices.append(category_index)
        categories[category] = {
            "runs": len(group),
            "unique_tasks": len({r["task"]["id"] for r in group}),
            "hard_success_rate": _mean(hard),
            "partial_pass_rate": _mean(partial),
            "category_index": category_index,
            "median_wall_seconds": _median(_numbers(group, lambda r: r.get("timing", {}).get("wall_seconds"))),
            "median_success_wall_seconds": _median(
                _numbers([r for r in group if r.get("verification", {}).get("passed")], lambda r: r.get("timing", {}).get("wall_seconds"))
            ),
            "median_generated_tokens": _median(_numbers(group, lambda r: r.get("usage", {}).get("completion_tokens"))),
        }

    successful = [r for r in rows if r.get("verification", {}).get("passed")]
    generated = _numbers(rows, lambda r: r.get("usage", {}).get("completion_tokens"))
    generated_success = _numbers(successful, lambda r: r.get("usage", {}).get("completion_tokens"))
    reasoning = _numbers(rows, lambda r: r.get("usage", {}).get("reasoning_tokens"))
    wall = _numbers(rows, lambda r: r.get("timing", {}).get("wall_seconds"))
    success_wall = _numbers(successful, lambda r: r.get("timing", {}).get("wall_seconds"))
    invalid_outcomes = {"invalid_output", "patch_failed"}
    infrastructure_outcomes = {"endpoint_error"}
    invalid = [r for r in rows if r.get("outcome") in invalid_outcomes]
    infrastructure = [r for r in rows if r.get("outcome") in infrastructure_outcomes]

    tool_calls = sum(int(r.get("agent", {}).get("tool_calls", 0)) for r in rows)
    invalid_tool_calls = sum(int(r.get("agent", {}).get("invalid_tool_calls", 0)) for r in rows)
    failed_tool_operations = sum(int(r.get("agent", {}).get("failed_tool_operations", 0)) for r in rows)
    valid_tool_calls = max(0, tool_calls - invalid_tool_calls)
    public_test_runs = sum(int(r.get("agent", {}).get("public_test_runs", 0)) for r in rows)
    recovery_candidates = [r for r in rows if int(r.get("agent", {}).get("public_test_failures", 0)) > 0]
    recoveries = [r for r in recovery_candidates if r.get("agent", {}).get("recovered_after_public_test_failure")]

    peak_vram = _numbers(rows, lambda r: r.get("gpu", {}).get("peak_memory_used_mb"))
    avg_gpu = _numbers(rows, lambda r: r.get("gpu", {}).get("average_gpu_utilization_pct"))
    peak_power = _numbers(rows, lambda r: r.get("gpu", {}).get("peak_power_w"))
    peak_temp = _numbers(rows, lambda r: r.get("gpu", {}).get("peak_temperature_c"))
    prompt_tps = _numbers(rows, lambda r: r.get("endpoint_metrics", {}).get("prompt_tokens_per_second_median"))
    decode_tps = _numbers(rows, lambda r: r.get("endpoint_metrics", {}).get("decode_tokens_per_second_median"))
    drafted = sum(_numbers(rows, lambda r: r.get("endpoint_metrics", {}).get("draft_tokens")))
    accepted = sum(_numbers(rows, lambda r: r.get("endpoint_metrics", {}).get("accepted_draft_tokens")))

    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[str(row["task"]["id"])].append(row)
    task_pass_rates = [
        sum(1.0 if r.get("verification", {}).get("passed") else 0.0 for r in group) / len(group)
        for group in by_task.values()
    ]
    task_seed_std = [math.sqrt(rate * (1.0 - rate)) for rate in task_pass_rates]
    unstable_tasks = sum(1 for rate in task_pass_rates if 0.0 < rate < 1.0)

    pair_keys = [(str(r["task"]["id"]), int(r.get("seed", 0))) for r in rows]
    outcome_counts = dict(Counter(str(r.get("outcome", "unknown")) for r in rows))
    total_wall = sum(wall)

    return {
        "runs": len(rows),
        "unique_tasks": len(by_task),
        "seeds": sorted({int(r.get("seed", 0)) for r in rows}),
        "duplicate_task_seed_pairs": len(pair_keys) - len(set(pair_keys)),
        "hard_task_success_rate": len(successful) / len(rows),
        "partial_test_pass_rate": _mean([float(r.get("verification", {}).get("score", 0.0)) for r in rows]),
        "category_balanced_index": _mean(category_indices),
        "worst_category_index": min(category_indices) if category_indices else None,
        "invalid_output_rate": len(invalid) / len(rows),
        "infrastructure_error_rate": len(infrastructure) / len(rows),
        "outcome_counts": outcome_counts,
        "median_wall_seconds": _median(wall),
        "p90_wall_seconds": percentile(wall, 0.9),
        "median_success_wall_seconds": _median(success_wall),
        "p90_success_wall_seconds": percentile(success_wall, 0.9),
        "successful_tasks_per_wall_hour": (len(successful) / (total_wall / 3600.0)) if total_wall > 0 else None,
        "median_generated_tokens": _median(generated),
        "median_success_generated_tokens": _median(generated_success),
        "total_generated_tokens": sum(generated) if generated else None,
        "median_reasoning_tokens": _median(reasoning),
        "total_reasoning_tokens": sum(reasoning) if reasoning else None,
        "reasoning_token_coverage_rate": len(reasoning) / len(rows),
        "tool_calls": tool_calls,
        "invalid_tool_calls": invalid_tool_calls,
        "failed_tool_operations": failed_tool_operations,
        "valid_tool_call_rate": valid_tool_calls / tool_calls if tool_calls else None,
        "tool_operation_success_rate": (valid_tool_calls - failed_tool_operations) / valid_tool_calls if valid_tool_calls else None,
        "public_test_runs": public_test_runs,
        "public_test_recovery_candidates": len(recovery_candidates),
        "public_test_recoveries": len(recoveries),
        "public_test_recovery_rate": len(recoveries) / len(recovery_candidates) if recovery_candidates else None,
        "peak_vram_mb": max(peak_vram) if peak_vram else None,
        "median_average_gpu_utilization_pct": _median(avg_gpu),
        "peak_power_w": max(peak_power) if peak_power else None,
        "peak_temperature_c": max(peak_temp) if peak_temp else None,
        "gpu_coverage_rate": len(peak_vram) / len(rows),
        "median_prompt_tokens_per_second": _median(prompt_tps),
        "median_decode_tokens_per_second": _median(decode_tps),
        "endpoint_timing_coverage_rate": max(len(prompt_tps), len(decode_tps)) / len(rows),
        "mtp_draft_tokens": drafted if drafted > 0 else None,
        "mtp_accepted_tokens": accepted if drafted > 0 else None,
        "mtp_acceptance_rate": accepted / drafted if drafted > 0 else None,
        "unstable_task_count": unstable_tasks,
        "unstable_task_rate": unstable_tasks / len(by_task) if by_task else None,
        "mean_task_seed_std": _mean(task_seed_std),
        "categories": categories,
    }
