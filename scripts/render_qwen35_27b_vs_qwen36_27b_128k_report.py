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


def load_optional_json(path: Path) -> Any:
    return load_json(path) if path.exists() else None


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def to_float(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except Exception:
        return None


def mean(values: list[float | None]) -> float | None:
    clean = [item for item in values if item is not None]
    return None if not clean else sum(clean) / len(clean)


def fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def pct(num: int, den: int) -> str:
    return "0.0%" if den == 0 else f"{(num / den) * 100:.1f}%"


def status_counts(rows: list[dict[str, str]], field: str = "http_status") -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get(field, "-"))] += 1
    return dict(sorted(counts.items()))


def select_best_coding(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    selected: list[dict[str, str]] = []
    for task_rows in grouped.values():
        task_rows.sort(key=lambda row: int(row["repeat_index"]))
        successful = [row for row in task_rows if to_bool(row.get("success"))]
        selected.append(successful[0] if successful else task_rows[0])
    return selected


def summarize_coding(path: Path) -> dict[str, Any]:
    rows = select_best_coding(load_csv(path))
    return {
        "exists": path.exists(),
        "total": len(rows),
        "success": sum(to_bool(row.get("success")) for row in rows),
        "avg_elapsed_ms": mean([to_float(row.get("elapsed_ms")) for row in rows]),
        "avg_predicted_per_second": mean([to_float(row.get("predicted_per_second")) for row in rows]),
        "avg_prompt_tokens": mean([to_float(row.get("prompt_tokens")) for row in rows]),
        "avg_content_length": mean([to_float(row.get("content_length")) for row in rows]),
        "http_status_counts": status_counts(rows),
    }


def summarize_agentic(path: Path) -> dict[str, Any]:
    rows = load_csv(path)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    for task_rows in grouped.values():
        task_rows.sort(key=lambda row: int(row["repeat_index"]))
    first = [items[0] for items in grouped.values()]
    best = []
    for items in grouped.values():
        validation = [row for row in items if to_bool(row.get("validation_success"))]
        parse = [row for row in items if to_bool(row.get("json_parse_success"))]
        request = [row for row in items if to_bool(row.get("request_success"))]
        best.append((validation or parse or request or items)[0])
    return {
        "exists": path.exists(),
        "total": len(first),
        "first_validation_success": sum(to_bool(row.get("validation_success")) for row in first),
        "best_validation_success": sum(to_bool(row.get("validation_success")) for row in best),
        "first_json_parse_success": sum(to_bool(row.get("json_parse_success")) for row in first),
        "best_json_parse_success": sum(to_bool(row.get("json_parse_success")) for row in best),
        "avg_elapsed_ms": mean([to_float(row.get("elapsed_ms")) for row in first]),
        "avg_predicted_per_second": mean([to_float(row.get("predicted_per_second")) for row in first]),
        "http_status_counts": status_counts(first),
    }


def load_gpu_stats(path: Path) -> dict[str, float | int | None]:
    if not path.exists():
        return {
            "avg_memory_used_mib": None,
            "max_memory_used_mib": None,
            "avg_gpu_util_pct": None,
            "max_gpu_util_pct": None,
        }
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

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


def smoke_rows(smoke_results: list[dict[str, Any]] | None, model_key: str) -> str:
    items = [item for item in (smoke_results or []) if item.get("model_key") == model_key]
    if not items:
        return "| - | - | - | - | - |"
    return "\n".join(
        "| {phase} | {status} | {success} | {content} | {reasoning} |".format(
            phase=item.get("phase", "-"),
            status=item.get("http_status", "-"),
            success=item.get("success", False),
            content=item.get("content_length", "-"),
            reasoning=item.get("reasoning_content_length", "-"),
        )
        for item in items
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--baseline-key", required=True)
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--baseline-name", required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    output_root = Path(args.output_root).resolve()
    summary_dir = output_root / "summary"
    coding_root = output_root / "128k" / "coding"
    agentic_root = output_root / "128k" / "agentic"

    coding = {
        args.baseline_key: summarize_coding(coding_root / args.baseline_key / "results.csv"),
        args.candidate_key: summarize_coding(coding_root / args.candidate_key / "results.csv"),
    }
    agentic = {
        args.baseline_key: summarize_agentic(agentic_root / args.baseline_key / "results.csv"),
        args.candidate_key: summarize_agentic(agentic_root / args.candidate_key / "results.csv"),
    }
    gpu_stats = {
        "coding": {
            args.baseline_key: load_gpu_stats(coding_root / args.baseline_key / "gpu_samples.csv"),
            args.candidate_key: load_gpu_stats(coding_root / args.candidate_key / "gpu_samples.csv"),
        },
        "agentic": {
            args.baseline_key: load_gpu_stats(agentic_root / args.baseline_key / "gpu_samples.csv"),
            args.candidate_key: load_gpu_stats(agentic_root / args.candidate_key / "gpu_samples.csv"),
        },
    }
    smoke_results = load_optional_json(summary_dir / "smoke_results.json")
    payload = {
        "generated_at_utc": utc_now(),
        "baseline_key": args.baseline_key,
        "candidate_key": args.candidate_key,
        "baseline_name": args.baseline_name,
        "candidate_name": args.candidate_name,
        "coding": coding,
        "agentic": agentic,
        "gpu_stats": gpu_stats,
        "smoke_results": smoke_results,
        "download_meta": load_optional_json(summary_dir / "download_meta.json"),
        "preflight_models": load_optional_json(summary_dir / "preflight_models.json"),
    }
    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    base_coding = coding[args.baseline_key]
    cand_coding = coding[args.candidate_key]
    base_agentic = agentic[args.baseline_key]
    cand_agentic = agentic[args.candidate_key]

    report = f"""# Qwen3.5-27B vs Qwen3.6-27B 128K Coding/Agentic Evaluation

- Generated at (UTC): `{payload['generated_at_utc']}`
- Baseline: `{args.baseline_name}`
- Candidate: `{args.candidate_name}`
- Output root: `{output_root}`

## Smoke

### {args.baseline_name}

| Phase | HTTP | Success | Content chars | Reasoning chars |
| --- | ---: | --- | ---: | ---: |
{smoke_rows(smoke_results, args.baseline_key)}

### {args.candidate_name}

| Phase | HTTP | Success | Content chars | Reasoning chars |
| --- | ---: | --- | ---: | ---: |
{smoke_rows(smoke_results, args.candidate_key)}

## 128K Coding

| Metric | {args.baseline_name} | {args.candidate_name} |
| --- | ---: | ---: |
| success / total | {base_coding['success']} / {base_coding['total']} | {cand_coding['success']} / {cand_coding['total']} |
| success rate | {pct(base_coding['success'], base_coding['total'])} | {pct(cand_coding['success'], cand_coding['total'])} |
| avg elapsed_ms | {fmt(base_coding['avg_elapsed_ms'])} | {fmt(cand_coding['avg_elapsed_ms'])} |
| avg tok/s | {fmt(base_coding['avg_predicted_per_second'])} | {fmt(cand_coding['avg_predicted_per_second'])} |
| avg prompt_tokens | {fmt(base_coding['avg_prompt_tokens'])} | {fmt(cand_coding['avg_prompt_tokens'])} |
| avg content chars | {fmt(base_coding['avg_content_length'])} | {fmt(cand_coding['avg_content_length'])} |

## 128K Agentic

| Metric | {args.baseline_name} | {args.candidate_name} |
| --- | ---: | ---: |
| first validation success | {base_agentic['first_validation_success']} / {base_agentic['total']} | {cand_agentic['first_validation_success']} / {cand_agentic['total']} |
| best validation success | {base_agentic['best_validation_success']} / {base_agentic['total']} | {cand_agentic['best_validation_success']} / {cand_agentic['total']} |
| first JSON parse success | {base_agentic['first_json_parse_success']} / {base_agentic['total']} | {cand_agentic['first_json_parse_success']} / {cand_agentic['total']} |
| best JSON parse success | {base_agentic['best_json_parse_success']} / {base_agentic['total']} | {cand_agentic['best_json_parse_success']} / {cand_agentic['total']} |
| avg elapsed_ms | {fmt(base_agentic['avg_elapsed_ms'])} | {fmt(cand_agentic['avg_elapsed_ms'])} |
| avg tok/s | {fmt(base_agentic['avg_predicted_per_second'])} | {fmt(cand_agentic['avg_predicted_per_second'])} |

## GPU Snapshot

| Phase | Model | Avg mem MiB | Max mem MiB | Avg GPU % | Max GPU % |
| --- | --- | ---: | ---: | ---: | ---: |
| coding | {args.baseline_name} | {fmt(gpu_stats['coding'][args.baseline_key]['avg_memory_used_mib'])} | {fmt(gpu_stats['coding'][args.baseline_key]['max_memory_used_mib'])} | {fmt(gpu_stats['coding'][args.baseline_key]['avg_gpu_util_pct'])} | {fmt(gpu_stats['coding'][args.baseline_key]['max_gpu_util_pct'])} |
| coding | {args.candidate_name} | {fmt(gpu_stats['coding'][args.candidate_key]['avg_memory_used_mib'])} | {fmt(gpu_stats['coding'][args.candidate_key]['max_memory_used_mib'])} | {fmt(gpu_stats['coding'][args.candidate_key]['avg_gpu_util_pct'])} | {fmt(gpu_stats['coding'][args.candidate_key]['max_gpu_util_pct'])} |
| agentic | {args.baseline_name} | {fmt(gpu_stats['agentic'][args.baseline_key]['avg_memory_used_mib'])} | {fmt(gpu_stats['agentic'][args.baseline_key]['max_memory_used_mib'])} | {fmt(gpu_stats['agentic'][args.baseline_key]['avg_gpu_util_pct'])} | {fmt(gpu_stats['agentic'][args.baseline_key]['max_gpu_util_pct'])} |
| agentic | {args.candidate_name} | {fmt(gpu_stats['agentic'][args.candidate_key]['avg_memory_used_mib'])} | {fmt(gpu_stats['agentic'][args.candidate_key]['max_memory_used_mib'])} | {fmt(gpu_stats['agentic'][args.candidate_key]['avg_gpu_util_pct'])} | {fmt(gpu_stats['agentic'][args.candidate_key]['max_gpu_util_pct'])} |

## Manual Review Artifacts

- `summary/coding_score_packet.md`
- `summary/coding_score_packet.json`
- `summary/coding_manual_rubric_template.json`
- `summary/agentic_score_packet.md`
- `summary/agentic_score_packet.json`
- `summary/agentic_manual_rubric_template.json`
"""
    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote 128K report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
