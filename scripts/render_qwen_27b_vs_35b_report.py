#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def to_float(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except Exception:
        return None


def mean(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def fmt(value: float | int | str | None, digits: int = 2) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def pct(num: int, den: int) -> str:
    if den == 0:
        return "0.0%"
    return f"{(num / den) * 100:.1f}%"


def select_best_attempts(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    selected: dict[str, dict[str, str]] = {}
    for task_id, task_rows in grouped.items():
        task_rows.sort(key=lambda row: int(row["repeat_index"]))
        successful = [row for row in task_rows if row.get("success", "").lower() == "true"]
        selected[task_id] = successful[0] if successful else task_rows[0]
    return selected


def load_gpu_stats(path: Path) -> dict[str, float | int | None]:
    if not path.exists():
        return {
            "avg_memory_used_mib": None,
            "max_memory_used_mib": None,
            "avg_gpu_util_pct": None,
            "max_gpu_util_pct": None,
        }
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)

    def parse_int(field: str) -> list[int]:
        values: list[int] = []
        for row in rows:
            raw = row.get(field, "").strip().split()[0]
            if not raw:
                continue
            try:
                values.append(int(float(raw)))
            except Exception:
                continue
        return values

    mem = parse_int(" memory.used [MiB]")
    util = parse_int(" utilization.gpu [%]")
    return {
        "avg_memory_used_mib": mean(mem),
        "max_memory_used_mib": max(mem) if mem else None,
        "avg_gpu_util_pct": mean(util),
        "max_gpu_util_pct": max(util) if util else None,
    }


def score_summary(scores: list[dict[str, Any]], model_key: str) -> dict[str, Any]:
    filtered = [item for item in scores if item["model_key"] == model_key]
    return {
        "count": len(filtered),
        "pass_count": sum(bool(item["pass"]) for item in filtered),
        "total_score": sum(int(item["score_total"]) for item in filtered),
        "avg_score": mean([to_float(item["score_total"]) for item in filtered]),
    }


def task_wins(scores: list[dict[str, Any]], baseline_key: str, candidate_key: str) -> dict[str, int]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for item in scores:
        grouped[item["task_id"]][item["model_key"]] = item

    baseline_wins = 0
    candidate_wins = 0
    ties = 0
    for entries in grouped.values():
        baseline = entries[baseline_key]
        candidate = entries[candidate_key]
        baseline_score = int(baseline["score_total"])
        candidate_score = int(candidate["score_total"])
        if baseline_score > candidate_score:
            baseline_wins += 1
        elif candidate_score > baseline_score:
            candidate_wins += 1
        else:
            ties += 1
    return {
        "baseline_wins": baseline_wins,
        "candidate_wins": candidate_wins,
        "ties": ties,
    }


def recommendation(
    agentic_summary: dict[str, Any],
    scores: list[dict[str, Any]],
    baseline_key: str,
    candidate_key: str,
    baseline_coding_rows: list[dict[str, str]],
    candidate_coding_rows: list[dict[str, str]],
) -> str:
    baseline_agentic_best = agentic_summary["baseline"]["best"]["validation_success"]
    candidate_agentic_best = agentic_summary["candidate"]["best"]["validation_success"]
    if candidate_agentic_best < baseline_agentic_best:
        return "不建议替换当前 executor 默认模型；35B-A3B 更适合作为 reviewer / analyst。"

    baseline_score = score_summary(scores, baseline_key)
    candidate_score = score_summary(scores, candidate_key)
    baseline_success = sum(row["success"].lower() == "true" for row in select_best_attempts(baseline_coding_rows).values())
    candidate_success = sum(row["success"].lower() == "true" for row in select_best_attempts(candidate_coding_rows).values())
    if (
        candidate_score["total_score"] > baseline_score["total_score"]
        and candidate_score["pass_count"] >= baseline_score["pass_count"]
        and candidate_success >= baseline_success
    ):
        return "建议替换当前 executor 默认模型；35B-A3B 在 agentic gate 不落后，同时 coding 质量更强。"
    return "不建议直接替换；35B-A3B 没有在 executor 关键指标上形成足够优势。"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-key", required=True)
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--baseline-name", required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--coding-baseline-results", required=True)
    parser.add_argument("--coding-candidate-results", required=True)
    parser.add_argument("--agentic-summary-json", required=True)
    parser.add_argument("--scores-json", required=True)
    parser.add_argument("--startup-metrics-json", required=True)
    parser.add_argument("--coding-baseline-gpu", required=True)
    parser.add_argument("--coding-candidate-gpu", required=True)
    parser.add_argument("--agentic-baseline-gpu", required=True)
    parser.add_argument("--agentic-candidate-gpu", required=True)
    parser.add_argument("--server-args", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    baseline_coding_rows = load_csv(Path(args.coding_baseline_results))
    candidate_coding_rows = load_csv(Path(args.coding_candidate_results))
    agentic_summary = load_json(Path(args.agentic_summary_json))
    scores = load_json(Path(args.scores_json))
    startup_metrics = load_json(Path(args.startup_metrics_json))

    baseline_coding_best = list(select_best_attempts(baseline_coding_rows).values())
    candidate_coding_best = list(select_best_attempts(candidate_coding_rows).values())

    payload = {
        "generated_at_utc": utc_now(),
        "baseline_key": args.baseline_key,
        "candidate_key": args.candidate_key,
        "baseline_name": args.baseline_name,
        "candidate_name": args.candidate_name,
        "coding": {
            "baseline_success": sum(row["success"].lower() == "true" for row in baseline_coding_best),
            "candidate_success": sum(row["success"].lower() == "true" for row in candidate_coding_best),
            "total_tasks": len(baseline_coding_best),
            "baseline_avg_elapsed_ms": mean([to_float(row["elapsed_ms"]) for row in baseline_coding_best]),
            "candidate_avg_elapsed_ms": mean([to_float(row["elapsed_ms"]) for row in candidate_coding_best]),
            "baseline_avg_predicted_per_second": mean([to_float(row["predicted_per_second"]) for row in baseline_coding_best]),
            "candidate_avg_predicted_per_second": mean([to_float(row["predicted_per_second"]) for row in candidate_coding_best]),
        },
        "agentic_summary": agentic_summary,
        "score_summary": {
            args.baseline_key: score_summary(scores, args.baseline_key),
            args.candidate_key: score_summary(scores, args.candidate_key),
            "wins": task_wins(scores, args.baseline_key, args.candidate_key),
        },
        "startup_metrics": startup_metrics,
        "gpu_stats": {
            "coding": {
                args.baseline_key: load_gpu_stats(Path(args.coding_baseline_gpu)),
                args.candidate_key: load_gpu_stats(Path(args.coding_candidate_gpu)),
            },
            "agentic": {
                args.baseline_key: load_gpu_stats(Path(args.agentic_baseline_gpu)),
                args.candidate_key: load_gpu_stats(Path(args.agentic_candidate_gpu)),
            },
        },
    }
    payload["recommendation"] = recommendation(
        agentic_summary,
        scores,
        args.baseline_key,
        args.candidate_key,
        baseline_coding_rows,
        candidate_coding_rows,
    )

    report = f"""# Qwen 27B vs 35B Executor Compare Report

- Generated at (UTC): `{payload['generated_at_utc']}`
- Baseline: `{args.baseline_name}`
- Candidate: `{args.candidate_name}`

## Shared Service Args

```text
{args.server_args}
```

## Coding Round

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| success / total | {payload['coding']['baseline_success']} / {payload['coding']['total_tasks']} | {payload['coding']['candidate_success']} / {payload['coding']['total_tasks']} |
| success rate | {pct(payload['coding']['baseline_success'], payload['coding']['total_tasks'])} | {pct(payload['coding']['candidate_success'], payload['coding']['total_tasks'])} |
| avg elapsed_ms | {fmt(payload['coding']['baseline_avg_elapsed_ms'])} | {fmt(payload['coding']['candidate_avg_elapsed_ms'])} |
| avg predicted_per_second | {fmt(payload['coding']['baseline_avg_predicted_per_second'])} | {fmt(payload['coding']['candidate_avg_predicted_per_second'])} |
| rubric total score | {payload['score_summary'][args.baseline_key]['total_score']} | {payload['score_summary'][args.candidate_key]['total_score']} |
| rubric avg score | {fmt(payload['score_summary'][args.baseline_key]['avg_score'])} | {fmt(payload['score_summary'][args.candidate_key]['avg_score'])} |
| rubric pass count | {payload['score_summary'][args.baseline_key]['pass_count']} | {payload['score_summary'][args.candidate_key]['pass_count']} |

## Agentic Round

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| first request success | {payload['agentic_summary']['baseline']['first']['request_success']} / {payload['agentic_summary']['baseline']['first']['task_count']} | {payload['agentic_summary']['candidate']['first']['request_success']} / {payload['agentic_summary']['candidate']['first']['task_count']} |
| first JSON parse success | {payload['agentic_summary']['baseline']['first']['json_parse_success']} / {payload['agentic_summary']['baseline']['first']['task_count']} | {payload['agentic_summary']['candidate']['first']['json_parse_success']} / {payload['agentic_summary']['candidate']['first']['task_count']} |
| first validation success | {payload['agentic_summary']['baseline']['first']['validation_success']} / {payload['agentic_summary']['baseline']['first']['task_count']} | {payload['agentic_summary']['candidate']['first']['validation_success']} / {payload['agentic_summary']['candidate']['first']['task_count']} |
| best-of-2 validation success | {payload['agentic_summary']['baseline']['best']['validation_success']} / {payload['agentic_summary']['baseline']['best']['task_count']} | {payload['agentic_summary']['candidate']['best']['validation_success']} / {payload['agentic_summary']['candidate']['best']['task_count']} |

## Resource Snapshot

| Round / Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| coding avg memory.used MiB | {fmt(payload['gpu_stats']['coding'][args.baseline_key]['avg_memory_used_mib'])} | {fmt(payload['gpu_stats']['coding'][args.candidate_key]['avg_memory_used_mib'])} |
| coding max memory.used MiB | {fmt(payload['gpu_stats']['coding'][args.baseline_key]['max_memory_used_mib'])} | {fmt(payload['gpu_stats']['coding'][args.candidate_key]['max_memory_used_mib'])} |
| coding avg gpu util % | {fmt(payload['gpu_stats']['coding'][args.baseline_key]['avg_gpu_util_pct'])} | {fmt(payload['gpu_stats']['coding'][args.candidate_key]['avg_gpu_util_pct'])} |
| agentic avg memory.used MiB | {fmt(payload['gpu_stats']['agentic'][args.baseline_key]['avg_memory_used_mib'])} | {fmt(payload['gpu_stats']['agentic'][args.candidate_key]['avg_memory_used_mib'])} |
| agentic max memory.used MiB | {fmt(payload['gpu_stats']['agentic'][args.baseline_key]['max_memory_used_mib'])} | {fmt(payload['gpu_stats']['agentic'][args.candidate_key]['max_memory_used_mib'])} |
| agentic avg gpu util % | {fmt(payload['gpu_stats']['agentic'][args.baseline_key]['avg_gpu_util_pct'])} | {fmt(payload['gpu_stats']['agentic'][args.candidate_key]['avg_gpu_util_pct'])} |

## Task Wins

- {args.baseline_key} wins: `{payload['score_summary']['wins']['baseline_wins']}`
- {args.candidate_key} wins: `{payload['score_summary']['wins']['candidate_wins']}`
- ties: `{payload['score_summary']['wins']['ties']}`

## Recommendation

{payload['recommendation']}
"""

    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
