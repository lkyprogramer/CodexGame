#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def summary(rows: list[dict[str, str]]) -> dict[str, object]:
    success_count = sum(1 for row in rows if row["success"].lower() == "true")
    by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)
    family_summary = {
        family: {
            "success": sum(1 for item in items if item["success"].lower() == "true"),
            "total": len(items),
            "avg_elapsed_ms": mean([to_float(item["elapsed_ms"]) for item in items]),
            "avg_predicted_per_second": mean([to_float(item["predicted_per_second"]) for item in items]),
            "avg_content_length": mean([to_float(item["content_length"]) for item in items]),
        }
        for family, items in sorted(by_family.items())
    }
    return {
        "rows": rows,
        "success": success_count,
        "total": len(rows),
        "avg_elapsed_ms": mean([to_float(row["elapsed_ms"]) for row in rows]),
        "avg_predicted_per_second": mean([to_float(row["predicted_per_second"]) for row in rows]),
        "avg_content_length": mean([to_float(row["content_length"]) for row in rows]),
        "family_summary": family_summary,
    }


def render_family_table(name: str, data: dict[str, object]) -> str:
    lines = [f"### {name}", "", "| Family | success | avg ms | avg tok/s | avg content len |", "| --- | ---: | ---: | ---: | ---: |"]
    family_summary = data["family_summary"]
    for family, row in family_summary.items():
        lines.append(
            "| {family} | {success}/{total} | {ms} | {tps} | {content} |".format(
                family=family,
                success=row["success"],
                total=row["total"],
                ms=fmt(row["avg_elapsed_ms"]),
                tps=fmt(row["avg_predicted_per_second"]),
                content=fmt(row["avg_content_length"]),
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-results", required=True)
    parser.add_argument("--candidate-results", required=True)
    parser.add_argument("--baseline-name", required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    baseline = summary(load_csv(Path(args.baseline_results)))
    candidate = summary(load_csv(Path(args.candidate_results)))
    baseline_rows = {row["task_id"]: row for row in baseline["rows"]}
    candidate_rows = {row["task_id"]: row for row in candidate["rows"]}
    ordered_task_ids = sorted(set(baseline_rows) | set(candidate_rows))

    task_lines = []
    for task_id in ordered_task_ids:
        b = baseline_rows.get(task_id, {})
        c = candidate_rows.get(task_id, {})
        family = b.get("family") or c.get("family") or "-"
        task_lines.append(
            "| {task_id} | {family} | {b_ms} | {b_tps} | {b_len} | {c_ms} | {c_tps} | {c_len} |".format(
                task_id=task_id,
                family=family,
                b_ms=fmt(to_float(b.get("elapsed_ms"))),
                b_tps=fmt(to_float(b.get("predicted_per_second"))),
                b_len=fmt(to_float(b.get("content_length"))),
                c_ms=fmt(to_float(c.get("elapsed_ms"))),
                c_tps=fmt(to_float(c.get("predicted_per_second"))),
                c_len=fmt(to_float(c.get("content_length"))),
            )
        )

    report = f"""# Nemotron Thinking Specialized Report

- Generated at (UTC): `{utc_now()}`
- Baseline: `{args.baseline_name}`
- Candidate: `{args.candidate_name}`

## Aggregate

| Metric | {args.baseline_name} | {args.candidate_name} |
| --- | ---: | ---: |
| success / total | {baseline['success']} / {baseline['total']} | {candidate['success']} / {candidate['total']} |
| avg elapsed_ms | {fmt(baseline['avg_elapsed_ms'])} | {fmt(candidate['avg_elapsed_ms'])} |
| avg predicted_per_second | {fmt(baseline['avg_predicted_per_second'])} | {fmt(candidate['avg_predicted_per_second'])} |
| avg content_length | {fmt(baseline['avg_content_length'])} | {fmt(candidate['avg_content_length'])} |

## Family Aggregate

{render_family_table(args.baseline_name, baseline)}

{render_family_table(args.candidate_name, candidate)}

## Per Task Snapshot

| Task | Family | {args.baseline_name} ms | {args.baseline_name} tok/s | {args.baseline_name} content | {args.candidate_name} ms | {args.candidate_name} tok/s | {args.candidate_name} content |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(task_lines)}
"""
    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
