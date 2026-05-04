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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def pct(num: int, den: int) -> str:
    return "0.0%" if den == 0 else f"{(num / den) * 100:.1f}%"


def load_gpu_stats(path: Path) -> dict[str, float | int | None]:
    if not path.exists():
        return {
            "avg_memory_used_mib": None,
            "max_memory_used_mib": None,
            "avg_gpu_util_pct": None,
            "max_gpu_util_pct": None,
        }
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    def parse_int(field: str) -> list[int]:
        values: list[int] = []
        for row in rows:
            raw = (row.get(field) or "").strip().split()[0]
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


def summarise_manual_scores(scores: dict[str, Any], baseline_key: str, candidate_key: str) -> dict[str, Any]:
    summary = scores.get("summary", {})
    baseline_total = summary.get(f"{baseline_key}_total")
    candidate_total = summary.get(f"{candidate_key}_total")
    if baseline_total is not None and candidate_total is not None:
        return {
            "baseline_total": baseline_total,
            "candidate_total": candidate_total,
            "wins": summary.get("task_wins", {}),
            "family_totals": summary.get("family_totals", {}),
            "conclusion": summary.get("conclusion", ""),
        }

    baseline_total = 0
    candidate_total = 0
    baseline_wins = 0
    candidate_wins = 0
    ties = 0
    family_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for task in scores["tasks"]:
        b = task[baseline_key]
        c = task[candidate_key]
        baseline_total += int(b["total"])
        candidate_total += int(c["total"])
        family = task["family"]
        family_totals[family][baseline_key] += int(b["total"])
        family_totals[family][candidate_key] += int(c["total"])
        if int(b["total"]) > int(c["total"]):
            baseline_wins += 1
        elif int(c["total"]) > int(b["total"]):
            candidate_wins += 1
        else:
            ties += 1
    return {
        "baseline_total": baseline_total,
        "candidate_total": candidate_total,
        "wins": {baseline_key: baseline_wins, candidate_key: candidate_wins, "tie": ties},
        "family_totals": family_totals,
        "conclusion": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-key", required=True)
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--baseline-name", required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--executor-baseline-results", required=True)
    parser.add_argument("--executor-candidate-results", required=True)
    parser.add_argument("--agentic-summary-json", required=True)
    parser.add_argument("--coding-manual-scores-json", required=True)
    parser.add_argument("--analyst-manual-scores-json", required=True)
    parser.add_argument("--startup-metrics-json", required=True)
    parser.add_argument("--transfer-gcp-json", required=True)
    parser.add_argument("--transfer-modelscope-json", required=True)
    parser.add_argument("--transfer-remote-json", required=True)
    parser.add_argument("--transfer-checksums-json", required=True)
    parser.add_argument("--executor-baseline-gpu", required=True)
    parser.add_argument("--executor-candidate-gpu", required=True)
    parser.add_argument("--agentic-baseline-gpu", required=True)
    parser.add_argument("--agentic-candidate-gpu", required=True)
    parser.add_argument("--analyst-baseline-gpu", required=True)
    parser.add_argument("--analyst-candidate-gpu", required=True)
    parser.add_argument("--server-args-executor", required=True)
    parser.add_argument("--server-args-analyst", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    baseline_rows = list(select_best_attempts(load_csv(Path(args.executor_baseline_results))).values())
    candidate_rows = list(select_best_attempts(load_csv(Path(args.executor_candidate_results))).values())
    agentic_summary = load_json(Path(args.agentic_summary_json))
    coding_scores = load_json(Path(args.coding_manual_scores_json))
    analyst_scores = load_json(Path(args.analyst_manual_scores_json))
    startup_metrics = load_json(Path(args.startup_metrics_json))

    coding_summary = summarise_manual_scores(coding_scores, args.baseline_key, args.candidate_key)
    analyst_summary = summarise_manual_scores(analyst_scores, args.baseline_key, args.candidate_key)

    payload = {
        "generated_at_utc": utc_now(),
        "baseline_name": args.baseline_name,
        "candidate_name": args.candidate_name,
        "transfer": {
            "gcp": load_json(Path(args.transfer_gcp_json)),
            "modelscope": load_json(Path(args.transfer_modelscope_json)),
            "remote": load_json(Path(args.transfer_remote_json)),
            "checksums": load_json(Path(args.transfer_checksums_json)),
        },
        "startup_metrics": startup_metrics,
        "executor": {
            "baseline_success": sum(row["success"].lower() == "true" for row in baseline_rows),
            "candidate_success": sum(row["success"].lower() == "true" for row in candidate_rows),
            "total_tasks": len(baseline_rows),
            "baseline_avg_elapsed_ms": mean([to_float(row["elapsed_ms"]) for row in baseline_rows]),
            "candidate_avg_elapsed_ms": mean([to_float(row["elapsed_ms"]) for row in candidate_rows]),
            "baseline_avg_tps": mean([to_float(row["predicted_per_second"]) for row in baseline_rows]),
            "candidate_avg_tps": mean([to_float(row["predicted_per_second"]) for row in candidate_rows]),
            "agentic": agentic_summary,
            "coding_manual": coding_summary,
        },
        "analyst_manual": analyst_summary,
        "gpu_stats": {
            "executor": {
                args.baseline_key: load_gpu_stats(Path(args.executor_baseline_gpu)),
                args.candidate_key: load_gpu_stats(Path(args.executor_candidate_gpu)),
            },
            "agentic": {
                args.baseline_key: load_gpu_stats(Path(args.agentic_baseline_gpu)),
                args.candidate_key: load_gpu_stats(Path(args.agentic_candidate_gpu)),
            },
            "analyst": {
                args.baseline_key: load_gpu_stats(Path(args.analyst_baseline_gpu)),
                args.candidate_key: load_gpu_stats(Path(args.analyst_candidate_gpu)),
            },
        },
    }

    baseline_agentic_best = agentic_summary["baseline"]["best"]["validation_success"]
    candidate_agentic_best = agentic_summary["candidate"]["best"]["validation_success"]
    if candidate_agentic_best < baseline_agentic_best:
        executor_conclusion = (
            f"{args.candidate_name} 不建议替换 {args.baseline_name} 作为默认 executor；"
            "它如果有优势，也更偏单轮分析速度，不在机器可交付稳定性。"
        )
    elif coding_summary["candidate_total"] > coding_summary["baseline_total"]:
        executor_conclusion = (
            f"{args.candidate_name} 可以考虑替换 {args.baseline_name} 作为默认 executor；"
            "agentic 没落后，同时 coding 人工总分更高。"
        )
    else:
        executor_conclusion = (
            f"{args.baseline_name} 更适合作为默认 executor；"
            f"{args.candidate_name} 即使更快，也没在关键稳定性/质量指标上形成足够优势。"
        )

    analyst_conclusion = analyst_summary.get("conclusion") or (
        f"Analyst 口径下优先看人工 rubric，当前总分："
        f"{args.baseline_name}={analyst_summary['baseline_total']}，"
        f"{args.candidate_name}={analyst_summary['candidate_total']}。"
    )
    payload["executor_conclusion"] = executor_conclusion
    payload["analyst_conclusion"] = analyst_conclusion

    report = f"""# Gemma4 vs Qwen35 UD Final Evaluation Report

- Generated at (UTC): `{payload['generated_at_utc']}`
- Baseline: `{args.baseline_name}`
- Candidate: `{args.candidate_name}`

## Transfer

| Item | Value |
| --- | --- |
| HF file | `{payload['transfer']['gcp']['path']}` |
| GCP size bytes | `{payload['transfer']['gcp']['size']}` |
| GCP sha256 | `{payload['transfer']['gcp']['sha256']}` |
| ModelScope repo | `{payload['transfer']['modelscope']['repo_id']}` |
| Remote path | `{payload['transfer']['remote']['path']}` |
| Remote size bytes | `{payload['transfer']['remote']['size']}` |
| Remote sha256 | `{payload['transfer']['remote']['sha256']}` |
| End-to-end checksum match | `{payload['transfer']['checksums']['match']}` |

## Shared Service Args

### Executor

```text
{args.server_args_executor}
```

### Analyst

```text
{args.server_args_analyst}
```

## Executor

| Metric | {args.baseline_name} | {args.candidate_name} |
| --- | ---: | ---: |
| coding success / total | {payload['executor']['baseline_success']} / {payload['executor']['total_tasks']} | {payload['executor']['candidate_success']} / {payload['executor']['total_tasks']} |
| coding success rate | {pct(payload['executor']['baseline_success'], payload['executor']['total_tasks'])} | {pct(payload['executor']['candidate_success'], payload['executor']['total_tasks'])} |
| coding avg elapsed_ms | {fmt(payload['executor']['baseline_avg_elapsed_ms'])} | {fmt(payload['executor']['candidate_avg_elapsed_ms'])} |
| coding avg predicted_per_second | {fmt(payload['executor']['baseline_avg_tps'])} | {fmt(payload['executor']['candidate_avg_tps'])} |
| coding manual total | {payload['executor']['coding_manual']['baseline_total']} | {payload['executor']['coding_manual']['candidate_total']} |

### Agentic

| Metric | {args.baseline_name} | {args.candidate_name} |
| --- | ---: | ---: |
| first validation success | {agentic_summary['baseline']['first']['validation_success']} / {agentic_summary['baseline']['first']['total']} | {agentic_summary['candidate']['first']['validation_success']} / {agentic_summary['candidate']['first']['total']} |
| best validation success | {agentic_summary['baseline']['best']['validation_success']} / {agentic_summary['baseline']['best']['total']} | {agentic_summary['candidate']['best']['validation_success']} / {agentic_summary['candidate']['best']['total']} |
| first avg elapsed_ms | {fmt(agentic_summary['baseline']['first']['avg_elapsed_ms'])} | {fmt(agentic_summary['candidate']['first']['avg_elapsed_ms'])} |
| first avg predicted_per_second | {fmt(agentic_summary['baseline']['first']['avg_predicted_per_second'])} | {fmt(agentic_summary['candidate']['first']['avg_predicted_per_second'])} |

结论：

- {executor_conclusion}

## Analyst

| Metric | {args.baseline_name} | {args.candidate_name} |
| --- | ---: | ---: |
| manual total | {analyst_summary['baseline_total']} | {analyst_summary['candidate_total']} |
| task wins | {analyst_summary['wins'].get(args.baseline_key, 0)} | {analyst_summary['wins'].get(args.candidate_key, 0)} |

结论：

- {analyst_conclusion}

## GPU Snapshot

### Executor coding

| Metric | {args.baseline_name} | {args.candidate_name} |
| --- | ---: | ---: |
| avg memory used MiB | {fmt(payload['gpu_stats']['executor'][args.baseline_key]['avg_memory_used_mib'])} | {fmt(payload['gpu_stats']['executor'][args.candidate_key]['avg_memory_used_mib'])} |
| max memory used MiB | {fmt(payload['gpu_stats']['executor'][args.baseline_key]['max_memory_used_mib'])} | {fmt(payload['gpu_stats']['executor'][args.candidate_key]['max_memory_used_mib'])} |
| avg gpu util % | {fmt(payload['gpu_stats']['executor'][args.baseline_key]['avg_gpu_util_pct'])} | {fmt(payload['gpu_stats']['executor'][args.candidate_key]['avg_gpu_util_pct'])} |
| max gpu util % | {fmt(payload['gpu_stats']['executor'][args.baseline_key]['max_gpu_util_pct'])} | {fmt(payload['gpu_stats']['executor'][args.candidate_key]['max_gpu_util_pct'])} |
"""

    Path(args.output_md).write_text(report, encoding="utf-8")
    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
