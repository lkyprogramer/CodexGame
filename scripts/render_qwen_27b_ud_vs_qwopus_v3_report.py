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
    clean = [item for item in values if item is not None]
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
    if not den:
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


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    best = list(select_best_attempts(rows).values())
    return {
        "success": sum(row["success"].lower() == "true" for row in best),
        "total": len(best),
        "avg_elapsed_ms": mean([to_float(row["elapsed_ms"]) for row in best]),
        "avg_predicted_per_second": mean([to_float(row["predicted_per_second"]) for row in best]),
        "avg_prompt_tokens": mean([to_float(row["prompt_tokens"]) for row in best]),
        "avg_content_length": mean([to_float(row["content_length"]) for row in best]),
        "avg_reasoning_length": mean([to_float(row["reasoning_content_length"]) for row in best]),
    }


def recommendation(payload: dict[str, Any]) -> str:
    baseline_64k = payload["fresh"]["64k"][payload["baseline_key"]]
    candidate_64k = payload["fresh"]["64k"][payload["candidate_key"]]
    baseline_262k = payload["fresh"]["262k"][payload["baseline_key"]]
    candidate_262k = payload["fresh"]["262k"][payload["candidate_key"]]
    agentic = payload["fresh"]["agentic"]

    base_best = agentic["baseline"]["best"]["validation_success"]
    cand_best = agentic["candidate"]["best"]["validation_success"]
    if cand_best < base_best:
        return "不建议替换默认 27B coding / executor 基线；Qwopus v3 在 agentic gate 上落后于 27B UD。"
    if (
        candidate_64k["success"] >= baseline_64k["success"]
        and (candidate_262k["success"] or 0) >= (baseline_262k["success"] or 0)
    ):
        return "可以进入默认 27B coding 候选；Qwopus v3 在 agentic 不落后，同时 64K/262K 也没有明显短板。"
    if candidate_262k["success"] > baseline_262k["success"]:
        return "可作为长上下文 sidecar 候选，但不建议直接替换默认 27B 基线。"
    return "不建议直接替换默认 27B 基线；Qwopus v3 没有在关键维度形成足够优势。"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-key", required=True)
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--baseline-name", required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--64k-baseline-results", required=True)
    parser.add_argument("--64k-candidate-results", required=True)
    parser.add_argument("--262k-baseline-results", required=True)
    parser.add_argument("--262k-candidate-results", required=True)
    parser.add_argument("--agentic-summary-json", required=True)
    parser.add_argument("--startup-metrics-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    payload = {
        "generated_at_utc": utc_now(),
        "baseline_key": args.baseline_key,
        "candidate_key": args.candidate_key,
        "baseline_name": args.baseline_name,
        "candidate_name": args.candidate_name,
        "fresh": {
            "64k": {
                args.baseline_key: summarize_rows(load_csv(Path(args.__dict__["64k_baseline_results"]))),
                args.candidate_key: summarize_rows(load_csv(Path(args.__dict__["64k_candidate_results"]))),
            },
            "262k": {
                args.baseline_key: summarize_rows(load_csv(Path(args.__dict__["262k_baseline_results"]))),
                args.candidate_key: summarize_rows(load_csv(Path(args.__dict__["262k_candidate_results"]))),
            },
            "agentic": load_json(Path(args.agentic_summary_json)),
            "startup_metrics": load_json(Path(args.startup_metrics_json)),
        },
    }

    baseline_64k = payload["fresh"]["64k"][args.baseline_key]
    candidate_64k = payload["fresh"]["64k"][args.candidate_key]
    baseline_262k = payload["fresh"]["262k"][args.baseline_key]
    candidate_262k = payload["fresh"]["262k"][args.candidate_key]
    agentic = payload["fresh"]["agentic"]

    report = f"""# Qwopus v3 vs Qwen27 UD Compare Report

- Generated at (UTC): `{payload['generated_at_utc']}`
- Baseline: `{args.baseline_name}`
- Candidate: `{args.candidate_name}`

## Fresh 64K Coding

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| success / total | {baseline_64k['success']} / {baseline_64k['total']} | {candidate_64k['success']} / {candidate_64k['total']} |
| success rate | {pct(baseline_64k['success'], baseline_64k['total'])} | {pct(candidate_64k['success'], candidate_64k['total'])} |
| avg elapsed_ms | {fmt(baseline_64k['avg_elapsed_ms'])} | {fmt(candidate_64k['avg_elapsed_ms'])} |
| avg tok/s | {fmt(baseline_64k['avg_predicted_per_second'])} | {fmt(candidate_64k['avg_predicted_per_second'])} |
| avg prompt_tokens | {fmt(baseline_64k['avg_prompt_tokens'])} | {fmt(candidate_64k['avg_prompt_tokens'])} |
| avg content_length | {fmt(baseline_64k['avg_content_length'])} | {fmt(candidate_64k['avg_content_length'])} |
| avg reasoning_length | {fmt(baseline_64k['avg_reasoning_length'])} | {fmt(candidate_64k['avg_reasoning_length'])} |

## Fresh 262K Extreme

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| success / total | {baseline_262k['success']} / {baseline_262k['total']} | {candidate_262k['success']} / {candidate_262k['total']} |
| success rate | {pct(baseline_262k['success'], baseline_262k['total'])} | {pct(candidate_262k['success'], candidate_262k['total'])} |
| avg elapsed_ms | {fmt(baseline_262k['avg_elapsed_ms'])} | {fmt(candidate_262k['avg_elapsed_ms'])} |
| avg tok/s | {fmt(baseline_262k['avg_predicted_per_second'])} | {fmt(candidate_262k['avg_predicted_per_second'])} |
| avg prompt_tokens | {fmt(baseline_262k['avg_prompt_tokens'])} | {fmt(candidate_262k['avg_prompt_tokens'])} |
| avg content_length | {fmt(baseline_262k['avg_content_length'])} | {fmt(candidate_262k['avg_content_length'])} |
| avg reasoning_length | {fmt(baseline_262k['avg_reasoning_length'])} | {fmt(candidate_262k['avg_reasoning_length'])} |

## Fresh Agentic

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| first request success | {agentic['baseline']['first']['request_success']} / {agentic['baseline']['first']['task_count']} | {agentic['candidate']['first']['request_success']} / {agentic['candidate']['first']['task_count']} |
| first JSON parse success | {agentic['baseline']['first']['json_parse_success']} / {agentic['baseline']['first']['task_count']} | {agentic['candidate']['first']['json_parse_success']} / {agentic['candidate']['first']['task_count']} |
| first validation success | {agentic['baseline']['first']['validation_success']} / {agentic['baseline']['first']['task_count']} | {agentic['candidate']['first']['validation_success']} / {agentic['candidate']['first']['task_count']} |
| best-of-2 validation success | {agentic['baseline']['best']['validation_success']} / {agentic['baseline']['best']['task_count']} | {agentic['candidate']['best']['validation_success']} / {agentic['candidate']['best']['task_count']} |

## Recommendation

{recommendation(payload)}
"""

    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
