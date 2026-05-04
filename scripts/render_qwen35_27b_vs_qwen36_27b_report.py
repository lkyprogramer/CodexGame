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
    if not path.exists():
        return None
    return load_json(path)


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


def select_best_attempts(rows: list[dict[str, str]]) -> list[dict[str, str]]:
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
    rows = select_best_attempts(load_csv(path))
    return {
        "exists": path.exists(),
        "total": len(rows),
        "success": sum(to_bool(row.get("success")) for row in rows),
        "avg_elapsed_ms": mean([to_float(row.get("elapsed_ms")) for row in rows]),
        "avg_predicted_per_second": mean([to_float(row.get("predicted_per_second")) for row in rows]),
        "avg_prompt_tokens": mean([to_float(row.get("prompt_tokens")) for row in rows]),
        "avg_content_length": mean([to_float(row.get("content_length")) for row in rows]),
        "avg_reasoning_length": mean([to_float(row.get("reasoning_content_length")) for row in rows]),
        "http_status_counts": status_counts(rows),
    }


def summarize_agentic(path: Path) -> dict[str, Any]:
    rows = load_csv(path)
    if not rows:
        return {
            "exists": path.exists(),
            "total": 0,
            "first_validation_success": 0,
            "best_validation_success": 0,
            "first_json_parse_success": 0,
            "best_json_parse_success": 0,
            "avg_elapsed_ms": None,
            "avg_predicted_per_second": None,
            "http_status_counts": {},
        }
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    for task_rows in grouped.values():
        task_rows.sort(key=lambda row: int(row["repeat_index"]))

    first = [task_rows[0] for task_rows in grouped.values()]
    best = []
    for task_rows in grouped.values():
        validation = [row for row in task_rows if to_bool(row.get("validation_success"))]
        parse = [row for row in task_rows if to_bool(row.get("json_parse_success"))]
        request = [row for row in task_rows if to_bool(row.get("request_success"))]
        best.append((validation or parse or request or task_rows)[0])

    return {
        "exists": path.exists(),
        "total": len(first),
        "first_validation_success": sum(to_bool(row.get("validation_success")) for row in first),
        "best_validation_success": sum(to_bool(row.get("validation_success")) for row in best),
        "first_json_parse_success": sum(to_bool(row.get("json_parse_success")) for row in first),
        "best_json_parse_success": sum(to_bool(row.get("json_parse_success")) for row in best),
        "avg_elapsed_ms": mean([to_float(row.get("elapsed_ms")) for row in first]),
        "avg_predicted_per_second": mean([to_float(row.get("predicted_per_second")) for row in first]),
        "http_status_counts": status_counts(first, status_field="http_status"),
    }


def status_counts(rows: list[dict[str, str]], *, status_field: str = "http_status") -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get(status_field, "-"))] += 1
    return dict(sorted(counts.items()))


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


def load_failure(output_root: Path, phase: str, model_key: str) -> dict[str, Any] | None:
    path = output_root / phase / model_key / "phase_failure.json"
    return load_optional_json(path)


def smoke_summary(smoke_results: list[dict[str, Any]] | None, model_key: str) -> list[dict[str, Any]]:
    if not smoke_results:
        return []
    return [item for item in smoke_results if item.get("model_key") == model_key]


def render_smoke_rows(items: list[dict[str, Any]]) -> str:
    if not items:
        return "| - | - | - | - | - |\n"
    lines = []
    for item in items:
        lines.append(
            "| {phase} | {status} | {success} | {content} | {reasoning} |".format(
                phase=item.get("phase", "-"),
                status=item.get("http_status", "-"),
                success=item.get("success", False),
                content=item.get("content_length", "-"),
                reasoning=item.get("reasoning_content_length", "-"),
            )
        )
    return "\n".join(lines)


def recommendation(payload: dict[str, Any], baseline_key: str, candidate_key: str) -> str:
    base_64 = payload["phases"]["64k"][baseline_key]
    cand_64 = payload["phases"]["64k"][candidate_key]
    base_agentic = payload["phases"]["agentic"][baseline_key]
    cand_agentic = payload["phases"]["agentic"][candidate_key]
    cand_262_failure = payload["failures"]["262k"].get(candidate_key)

    if cand_262_failure:
        return (
            "Qwen3.6-27B Q5 XL should not replace the current default until the 262K capacity failure is resolved. "
            "Use the 64K and agentic results only as short-context quality evidence."
        )
    if cand_agentic["best_validation_success"] < base_agentic["best_validation_success"]:
        return (
            "Qwen3.6-27B Q5 XL is not recommended as the default executor because it trails the Qwen3.5-27B baseline on agentic validation."
        )
    if cand_64["success"] >= base_64["success"]:
        return (
            "Qwen3.6-27B Q5 XL can enter candidate status for executor replacement, pending manual rubric review and long-context stability confirmation."
        )
    return (
        "Keep Qwen3.5-27B UD-Q4_K_XL as the default executor; the candidate did not form a clear automatic benchmark advantage."
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
    model_keys = [args.baseline_key, args.candidate_key]

    phases: dict[str, dict[str, Any]] = {
        "64k": {},
        "262k": {},
        "agentic": {},
    }
    failures: dict[str, dict[str, Any]] = {"64k": {}, "262k": {}, "agentic": {}}
    gpu_stats: dict[str, dict[str, Any]] = {"64k": {}, "262k": {}, "agentic": {}}

    for key in model_keys:
        phases["64k"][key] = summarize_coding(output_root / "64k" / key / "results.csv")
        phases["262k"][key] = summarize_coding(output_root / "262k" / key / "results.csv")
        phases["agentic"][key] = summarize_agentic(output_root / "agentic" / key / "results.csv")
        for phase in phases:
            failure = load_failure(output_root, phase, key)
            if failure:
                failures[phase][key] = failure
            gpu_stats[phase][key] = load_gpu_stats(output_root / phase / key / "gpu_samples.csv")

    smoke_results = load_optional_json(summary_dir / "smoke_results.json")
    startup_metrics = load_optional_json(summary_dir / "startup_metrics.json")
    download_meta = load_optional_json(summary_dir / "download_meta.json")
    preflight_models = load_optional_json(summary_dir / "preflight_models.json")
    checksums = load_optional_json(output_root / "transfer" / "checksums.json")

    payload = {
        "generated_at_utc": utc_now(),
        "baseline_key": args.baseline_key,
        "candidate_key": args.candidate_key,
        "baseline_name": args.baseline_name,
        "candidate_name": args.candidate_name,
        "download_meta": download_meta,
        "checksums": checksums,
        "preflight_models": preflight_models,
        "startup_metrics": startup_metrics,
        "smoke_results": smoke_results,
        "phases": phases,
        "failures": failures,
        "gpu_stats": gpu_stats,
    }
    payload["recommendation"] = recommendation(payload, args.baseline_key, args.candidate_key)

    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    base_64 = phases["64k"][args.baseline_key]
    cand_64 = phases["64k"][args.candidate_key]
    base_262 = phases["262k"][args.baseline_key]
    cand_262 = phases["262k"][args.candidate_key]
    base_agentic = phases["agentic"][args.baseline_key]
    cand_agentic = phases["agentic"][args.candidate_key]

    report = f"""# Qwen3.5-27B vs Qwen3.6-27B Evaluation Report

- Generated at (UTC): `{payload['generated_at_utc']}`
- Baseline: `{args.baseline_name}`
- Candidate: `{args.candidate_name}`
- Output root: `{output_root}`

## Download And Integrity

| Item | Value |
| --- | --- |
| ModelScope repo | `{(download_meta or {}).get('repo_id', '-')}` |
| Candidate file | `{(download_meta or {}).get('file', '-')}` |
| Remote path | `{(download_meta or {}).get('path', '-')}` |
| Remote size bytes | `{(download_meta or {}).get('size', '-')}` |
| Remote sha256 | `{(download_meta or {}).get('sha256', '-')}` |
| Checksum match | `{(checksums or {}).get('match', '-')}` |

## Smoke

### {args.baseline_name}

| Phase | HTTP | Success | Content chars | Reasoning chars |
| --- | ---: | --- | ---: | ---: |
{render_smoke_rows(smoke_summary(smoke_results, args.baseline_key))}

### {args.candidate_name}

| Phase | HTTP | Success | Content chars | Reasoning chars |
| --- | ---: | --- | ---: | ---: |
{render_smoke_rows(smoke_summary(smoke_results, args.candidate_key))}

## 64K Coding

| Metric | {args.baseline_name} | {args.candidate_name} |
| --- | ---: | ---: |
| success / total | {base_64['success']} / {base_64['total']} | {cand_64['success']} / {cand_64['total']} |
| success rate | {pct(base_64['success'], base_64['total'])} | {pct(cand_64['success'], cand_64['total'])} |
| avg elapsed_ms | {fmt(base_64['avg_elapsed_ms'])} | {fmt(cand_64['avg_elapsed_ms'])} |
| avg tok/s | {fmt(base_64['avg_predicted_per_second'])} | {fmt(cand_64['avg_predicted_per_second'])} |
| avg prompt_tokens | {fmt(base_64['avg_prompt_tokens'])} | {fmt(cand_64['avg_prompt_tokens'])} |
| avg content chars | {fmt(base_64['avg_content_length'])} | {fmt(cand_64['avg_content_length'])} |
| avg reasoning chars | {fmt(base_64['avg_reasoning_length'])} | {fmt(cand_64['avg_reasoning_length'])} |

## 262K Extreme

| Metric | {args.baseline_name} | {args.candidate_name} |
| --- | ---: | ---: |
| success / total | {base_262['success']} / {base_262['total']} | {cand_262['success']} / {cand_262['total']} |
| success rate | {pct(base_262['success'], base_262['total'])} | {pct(cand_262['success'], cand_262['total'])} |
| avg elapsed_ms | {fmt(base_262['avg_elapsed_ms'])} | {fmt(cand_262['avg_elapsed_ms'])} |
| avg tok/s | {fmt(base_262['avg_predicted_per_second'])} | {fmt(cand_262['avg_predicted_per_second'])} |
| startup/capacity failure | `{(failures['262k'].get(args.baseline_key) or {}).get('error', '-')}` | `{(failures['262k'].get(args.candidate_key) or {}).get('error', '-')}` |

## Agentic

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
| 64k | {args.baseline_name} | {fmt(gpu_stats['64k'][args.baseline_key]['avg_memory_used_mib'])} | {fmt(gpu_stats['64k'][args.baseline_key]['max_memory_used_mib'])} | {fmt(gpu_stats['64k'][args.baseline_key]['avg_gpu_util_pct'])} | {fmt(gpu_stats['64k'][args.baseline_key]['max_gpu_util_pct'])} |
| 64k | {args.candidate_name} | {fmt(gpu_stats['64k'][args.candidate_key]['avg_memory_used_mib'])} | {fmt(gpu_stats['64k'][args.candidate_key]['max_memory_used_mib'])} | {fmt(gpu_stats['64k'][args.candidate_key]['avg_gpu_util_pct'])} | {fmt(gpu_stats['64k'][args.candidate_key]['max_gpu_util_pct'])} |
| 262k | {args.baseline_name} | {fmt(gpu_stats['262k'][args.baseline_key]['avg_memory_used_mib'])} | {fmt(gpu_stats['262k'][args.baseline_key]['max_memory_used_mib'])} | {fmt(gpu_stats['262k'][args.baseline_key]['avg_gpu_util_pct'])} | {fmt(gpu_stats['262k'][args.baseline_key]['max_gpu_util_pct'])} |
| 262k | {args.candidate_name} | {fmt(gpu_stats['262k'][args.candidate_key]['avg_memory_used_mib'])} | {fmt(gpu_stats['262k'][args.candidate_key]['max_memory_used_mib'])} | {fmt(gpu_stats['262k'][args.candidate_key]['avg_gpu_util_pct'])} | {fmt(gpu_stats['262k'][args.candidate_key]['max_gpu_util_pct'])} |
| agentic | {args.baseline_name} | {fmt(gpu_stats['agentic'][args.baseline_key]['avg_memory_used_mib'])} | {fmt(gpu_stats['agentic'][args.baseline_key]['max_memory_used_mib'])} | {fmt(gpu_stats['agentic'][args.baseline_key]['avg_gpu_util_pct'])} | {fmt(gpu_stats['agentic'][args.baseline_key]['max_gpu_util_pct'])} |
| agentic | {args.candidate_name} | {fmt(gpu_stats['agentic'][args.candidate_key]['avg_memory_used_mib'])} | {fmt(gpu_stats['agentic'][args.candidate_key]['max_memory_used_mib'])} | {fmt(gpu_stats['agentic'][args.candidate_key]['avg_gpu_util_pct'])} | {fmt(gpu_stats['agentic'][args.candidate_key]['max_gpu_util_pct'])} |

## Recommendation

{payload['recommendation']}

## Manual Review Artifacts

- `summary/coding_score_packet.md`
- `summary/coding_score_packet.json`
- `summary/coding_manual_rubric_template.json`
"""

    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote final report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
