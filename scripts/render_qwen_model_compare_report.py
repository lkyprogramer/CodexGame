#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_optional_json(path: Path | None) -> dict[tuple[str, str], dict]:
    if path is None or not path.exists():
        return {}
    items = json.loads(path.read_text(encoding="utf-8"))
    result: dict[tuple[str, str], dict] = {}
    for item in items:
        result[(item["model_key"], item["task_id"])] = item
    return result


def to_float(value: str) -> float | None:
    if value in ("", "-", None):
        return None
    try:
        return float(value)
    except Exception:
        return None


def mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def fmt(value: float | int | str | None, digits: int = 2) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def pct(success: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{(success / total) * 100:.1f}%"


def select_best_attempts(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)

    selected = []
    for task_id, task_rows in grouped.items():
        task_rows.sort(key=lambda row: int(row["repeat_index"]))
        successful = [row for row in task_rows if row["success"].lower() == "true"]
        selected.append(successful[0] if successful else task_rows[0])
    selected.sort(key=lambda row: row["task_id"])
    return selected


def model_summary(rows: list[dict[str, str]]) -> dict[str, object]:
    selected = select_best_attempts(rows)
    success_count = sum(1 for row in selected if row["success"].lower() == "true")
    return {
        "selected": selected,
        "total": len(selected),
        "success": success_count,
        "success_rate": pct(success_count, len(selected)),
        "avg_elapsed_ms": mean([to_float(row["elapsed_ms"]) for row in selected]),
        "avg_prompt_ms": mean([to_float(row["prompt_ms"]) for row in selected]),
        "avg_predicted_per_second": mean([to_float(row["predicted_per_second"]) for row in selected]),
        "avg_prompt_tokens": mean([to_float(row["prompt_tokens"]) for row in selected]),
        "avg_reasoning_len": mean([to_float(row["reasoning_content_length"]) for row in selected]),
        "avg_content_len": mean([to_float(row["content_length"]) for row in selected]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-results", required=True)
    parser.add_argument("--candidate-results", required=True)
    parser.add_argument("--baseline-key", required=True)
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--baseline-name", required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--scores-json")
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    baseline_rows = load_csv(Path(args.baseline_results))
    candidate_rows = load_csv(Path(args.candidate_results))
    scores = load_optional_json(Path(args.scores_json) if args.scores_json else None)

    baseline = model_summary(baseline_rows)
    candidate = model_summary(candidate_rows)

    baseline_by_task = {row["task_id"]: row for row in baseline["selected"]}
    candidate_by_task = {row["task_id"]: row for row in candidate["selected"]}
    ordered_task_ids = sorted(set(baseline_by_task) | set(candidate_by_task))

    task_lines = []
    for task_id in ordered_task_ids:
        baseline_row = baseline_by_task.get(task_id, {})
        candidate_row = candidate_by_task.get(task_id, {})
        baseline_score = scores.get((args.baseline_key, task_id), {})
        candidate_score = scores.get((args.candidate_key, task_id), {})
        task_lines.append(
            "| {task_id} | {b_http} | {b_ms} | {b_tps} | {b_score} | {c_http} | {c_ms} | {c_tps} | {c_score} |".format(
                task_id=task_id,
                b_http=baseline_row.get("http_status", "-"),
                b_ms=fmt(to_float(baseline_row.get("elapsed_ms"))),
                b_tps=fmt(to_float(baseline_row.get("predicted_per_second"))),
                b_score=fmt(baseline_score.get("score_total")),
                c_http=candidate_row.get("http_status", "-"),
                c_ms=fmt(to_float(candidate_row.get("elapsed_ms"))),
                c_tps=fmt(to_float(candidate_row.get("predicted_per_second"))),
                c_score=fmt(candidate_score.get("score_total")),
            )
        )

    report = f"""# Qwen Coding Compare Report

- Generated at (UTC): `{utc_now()}`
- Baseline: `{args.baseline_name}`
- Candidate: `{args.candidate_name}`

## Aggregate Metrics

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| success / total | {baseline['success']} / {baseline['total']} | {candidate['success']} / {candidate['total']} |
| success rate | {baseline['success_rate']} | {candidate['success_rate']} |
| avg elapsed_ms | {fmt(baseline['avg_elapsed_ms'])} | {fmt(candidate['avg_elapsed_ms'])} |
| avg prompt_ms | {fmt(baseline['avg_prompt_ms'])} | {fmt(candidate['avg_prompt_ms'])} |
| avg predicted_per_second | {fmt(baseline['avg_predicted_per_second'])} | {fmt(candidate['avg_predicted_per_second'])} |
| avg prompt_tokens | {fmt(baseline['avg_prompt_tokens'])} | {fmt(candidate['avg_prompt_tokens'])} |
| avg reasoning_content_length | {fmt(baseline['avg_reasoning_len'])} | {fmt(candidate['avg_reasoning_len'])} |
| avg content_length | {fmt(baseline['avg_content_len'])} | {fmt(candidate['avg_content_len'])} |

## Per Task Snapshot

| Task | {args.baseline_key} http | {args.baseline_key} ms | {args.baseline_key} tok/s | {args.baseline_key} score | {args.candidate_key} http | {args.candidate_key} ms | {args.candidate_key} tok/s | {args.candidate_key} score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(task_lines)}
"""

    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
