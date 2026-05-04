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


def score_summary(scores: list[dict[str, Any]], model_key: str) -> dict[str, Any]:
    filtered = [item for item in scores if item["model_key"] == model_key]
    return {
        "count": len(filtered),
        "pass_count": sum(bool(item["pass"]) for item in filtered),
        "total_score": sum(int(item["score_total"]) for item in filtered),
        "avg_score": mean([to_float(item["score_total"]) for item in filtered]),
    }


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
    parser.add_argument("--scores-json", required=True)
    parser.add_argument("--historical-64k-report", required=True)
    parser.add_argument("--historical-262k-report", required=True)
    parser.add_argument("--historical-agentic-report", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    scores = load_json(Path(args.scores_json))
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
            "score_summary": {
                args.baseline_key: score_summary(scores, args.baseline_key),
                args.candidate_key: score_summary(scores, args.candidate_key),
            },
        },
        "historical_reports": {
            "64k": args.historical_64k_report,
            "262k": args.historical_262k_report,
            "agentic": args.historical_agentic_report,
        },
    }

    baseline_64k = payload["fresh"]["64k"][args.baseline_key]
    candidate_64k = payload["fresh"]["64k"][args.candidate_key]
    baseline_262k = payload["fresh"]["262k"][args.baseline_key]
    candidate_262k = payload["fresh"]["262k"][args.candidate_key]
    agentic = payload["fresh"]["agentic"]
    score_base = payload["fresh"]["score_summary"][args.baseline_key]
    score_cand = payload["fresh"]["score_summary"][args.candidate_key]

    if (
        agentic["candidate"]["best"]["validation_success"] >= agentic["baseline"]["best"]["validation_success"]
        and score_cand["total_score"] >= score_base["total_score"]
        and candidate_64k["success"] >= baseline_64k["success"]
    ):
        recommendation = "v2 值得进入默认 27B coding 候选；它至少没有在 agentic gate 上退步，同时 64K coding 质量不低于基线。"
    else:
        recommendation = "不建议仅凭这轮结果直接替换默认 27B coding 基线；需要把 fresh v2 结果与旧版 v1 历史报告一起看。"

    report = f"""# Qwen3.5-27B Distilled v2 Compare Report

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
| rubric total score | {score_base['total_score']} | {score_cand['total_score']} |
| rubric avg score | {fmt(score_base['avg_score'])} | {fmt(score_cand['avg_score'])} |
| rubric pass count | {score_base['pass_count']} | {score_cand['pass_count']} |

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

## Historical Reference

- old v1 64K report: `{args.historical_64k_report}`
- old v1 262K report: `{args.historical_262k_report}`
- old v1 agentic report: `{args.historical_agentic_report}`

## Recommendation

{recommendation}
"""

    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
