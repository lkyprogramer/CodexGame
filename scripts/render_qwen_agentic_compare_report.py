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


def to_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def to_float(value: str | None) -> float | None:
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


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


def group_by_task(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    for task_rows in grouped.values():
        task_rows.sort(key=lambda row: int(row["repeat_index"]))
    return grouped


def best_attempt(task_rows: list[dict[str, str]]) -> dict[str, str]:
    validation_success = [row for row in task_rows if to_bool(row.get("validation_success"))]
    if validation_success:
        return validation_success[0]
    parse_success = [row for row in task_rows if to_bool(row.get("json_parse_success"))]
    if parse_success:
        return parse_success[0]
    request_success = [row for row in task_rows if to_bool(row.get("request_success"))]
    if request_success:
        return request_success[0]
    return task_rows[0]


def build_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    grouped = group_by_task(rows)
    first_attempts = [task_rows[0] for task_rows in grouped.values()]
    best_attempts = [best_attempt(task_rows) for task_rows in grouped.values()]

    def aggregate(selected_rows: list[dict[str, str]]) -> dict[str, Any]:
        return {
            "task_count": len(selected_rows),
            "request_success": sum(to_bool(row.get("request_success")) for row in selected_rows),
            "json_parse_success": sum(to_bool(row.get("json_parse_success")) for row in selected_rows),
            "validation_success": sum(to_bool(row.get("validation_success")) for row in selected_rows),
            "avg_elapsed_ms": mean([to_float(row.get("elapsed_ms")) for row in selected_rows]),
            "avg_prompt_tokens": mean([to_float(row.get("prompt_tokens")) for row in selected_rows]),
            "avg_completion_tokens": mean([to_float(row.get("completion_tokens")) for row in selected_rows]),
            "avg_total_tokens": mean([to_float(row.get("total_tokens")) for row in selected_rows]),
            "avg_predicted_per_second": mean([to_float(row.get("predicted_per_second")) for row in selected_rows]),
            "avg_files_written_count": mean([to_float(row.get("files_written_count")) for row in selected_rows]),
            "avg_reasoning_len": mean([to_float(row.get("reasoning_content_length")) for row in selected_rows]),
            "avg_content_len": mean([to_float(row.get("content_length")) for row in selected_rows]),
        }

    return {
        "first": aggregate(first_attempts),
        "best": aggregate(best_attempts),
        "first_attempts": {row["task_id"]: row for row in first_attempts},
        "best_attempts": {row["task_id"]: row for row in best_attempts},
    }


def compare_status(row: dict[str, str] | None) -> str:
    if not row:
        return "-"
    if to_bool(row.get("validation_success")):
        return "validate_ok"
    if to_bool(row.get("json_parse_success")):
        return "parse_ok"
    if to_bool(row.get("request_success")):
        return "request_ok"
    return f"http_{row.get('http_status', '-') }"


def build_per_task_table(
    baseline_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
) -> str:
    task_ids = sorted(
        set(baseline_summary["first_attempts"].keys())
        | set(candidate_summary["first_attempts"].keys())
    )
    lines: list[str] = []
    for task_id in task_ids:
        baseline_first = baseline_summary["first_attempts"].get(task_id)
        candidate_first = candidate_summary["first_attempts"].get(task_id)
        baseline_best = baseline_summary["best_attempts"].get(task_id)
        candidate_best = candidate_summary["best_attempts"].get(task_id)
        lines.append(
            "| {task_id} | {b_first} | {b_first_ms} | {b_best} | {b_best_ms} | {c_first} | {c_first_ms} | {c_best} | {c_best_ms} |".format(
                task_id=task_id,
                b_first=compare_status(baseline_first),
                b_first_ms=fmt(to_float((baseline_first or {}).get("elapsed_ms"))),
                b_best=compare_status(baseline_best),
                b_best_ms=fmt(to_float((baseline_best or {}).get("elapsed_ms"))),
                c_first=compare_status(candidate_first),
                c_first_ms=fmt(to_float((candidate_first or {}).get("elapsed_ms"))),
                c_best=compare_status(candidate_best),
                c_best_ms=fmt(to_float((candidate_best or {}).get("elapsed_ms"))),
            )
        )
    return "\n".join(lines)


def render_metrics_rows(label: str, summary: dict[str, Any]) -> str:
    metrics = summary[label]
    total = metrics["task_count"]
    return "\n".join(
        [
            f"| {label} request success | {metrics['request_success']} / {total} ({pct(metrics['request_success'], total)}) |",
            f"| {label} JSON parse success | {metrics['json_parse_success']} / {total} ({pct(metrics['json_parse_success'], total)}) |",
            f"| {label} validation success | {metrics['validation_success']} / {total} ({pct(metrics['validation_success'], total)}) |",
            f"| {label} avg elapsed_ms | {fmt(metrics['avg_elapsed_ms'])} |",
            f"| {label} avg prompt_tokens | {fmt(metrics['avg_prompt_tokens'])} |",
            f"| {label} avg completion_tokens | {fmt(metrics['avg_completion_tokens'])} |",
            f"| {label} avg total_tokens | {fmt(metrics['avg_total_tokens'])} |",
            f"| {label} avg predicted_per_second | {fmt(metrics['avg_predicted_per_second'])} |",
            f"| {label} avg files_written_count | {fmt(metrics['avg_files_written_count'])} |",
            f"| {label} avg reasoning_content_length | {fmt(metrics['avg_reasoning_len'])} |",
            f"| {label} avg content_length | {fmt(metrics['avg_content_len'])} |",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-results", required=True)
    parser.add_argument("--candidate-results", required=True)
    parser.add_argument("--baseline-key", required=True)
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--baseline-name", required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    baseline_rows = load_csv(Path(args.baseline_results))
    candidate_rows = load_csv(Path(args.candidate_results))

    baseline_summary = build_summary(baseline_rows)
    candidate_summary = build_summary(candidate_rows)

    payload = {
        "generated_at_utc": utc_now(),
        "baseline_key": args.baseline_key,
        "candidate_key": args.candidate_key,
        "baseline_name": args.baseline_name,
        "candidate_name": args.candidate_name,
        "baseline": baseline_summary,
        "candidate": candidate_summary,
    }

    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report = f"""# Qwen Agentic Coding Compare Report

- Generated at (UTC): `{payload['generated_at_utc']}`
- Baseline: `{args.baseline_name}`
- Candidate: `{args.candidate_name}`

## Baseline Aggregate

| Metric | Value |
| --- | ---: |
{render_metrics_rows('first', baseline_summary)}
{render_metrics_rows('best', baseline_summary)}

## Candidate Aggregate

| Metric | Value |
| --- | ---: |
{render_metrics_rows('first', candidate_summary)}
{render_metrics_rows('best', candidate_summary)}

## Per Task Snapshot

| Task | {args.baseline_key} first | {args.baseline_key} first ms | {args.baseline_key} best | {args.baseline_key} best ms | {args.candidate_key} first | {args.candidate_key} first ms | {args.candidate_key} best | {args.candidate_key} best ms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
{build_per_task_table(baseline_summary, candidate_summary)}
"""

    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
