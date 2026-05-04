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


def select_best_attempts(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)

    selected: list[dict[str, str]] = []
    for task_rows in grouped.values():
        task_rows.sort(key=lambda row: int(row["repeat_index"]))
        successful = [row for row in task_rows if to_bool(row.get("success"))]
        selected.append(successful[0] if successful else task_rows[0])
    selected.sort(key=lambda row: row["task_id"])
    return selected


def summarize_coding(rows: list[dict[str, str]]) -> dict[str, Any]:
    selected = select_best_attempts(rows)
    return {
        "task_count": len(selected),
        "success": sum(to_bool(row.get("success")) for row in selected),
        "avg_elapsed_ms": mean([to_float(row.get("elapsed_ms")) for row in selected]),
        "avg_prompt_ms": mean([to_float(row.get("prompt_ms")) for row in selected]),
        "avg_predicted_per_second": mean([to_float(row.get("predicted_per_second")) for row in selected]),
        "avg_prompt_tokens": mean([to_float(row.get("prompt_tokens")) for row in selected]),
        "avg_reasoning_len": mean([to_float(row.get("reasoning_content_length")) for row in selected]),
        "avg_content_len": mean([to_float(row.get("content_length")) for row in selected]),
        "per_task": {row["task_id"]: row for row in selected},
    }


def summarize_startup_round(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_model: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[item["model_key"]].append(item)

    for model_key, rows in grouped.items():
        by_model[model_key] = {
            "count": len(rows),
            "avg_startup_elapsed_ms": mean([to_float(row.get("startup_elapsed_ms")) for row in rows]),
            "avg_idle_gpu_memory_mib": mean([to_float((row.get("idle_gpu") or {}).get("memory_used_mib")) for row in rows]),
            "avg_idle_gpu_util_pct": mean([to_float((row.get("idle_gpu") or {}).get("utilization_gpu_pct")) for row in rows]),
        }
    return by_model


def build_coding_table(
    baseline_key: str,
    candidate_key: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> str:
    task_ids = sorted(set(baseline["per_task"]) | set(candidate["per_task"]))
    lines: list[str] = []
    for task_id in task_ids:
        b = baseline["per_task"].get(task_id, {})
        c = candidate["per_task"].get(task_id, {})
        lines.append(
            "| {task_id} | {b_http} | {b_ok} | {b_ms} | {b_tps} | {c_http} | {c_ok} | {c_ms} | {c_tps} |".format(
                task_id=task_id,
                b_http=b.get("http_status", "-"),
                b_ok="ok" if to_bool(b.get("success")) else "fail",
                b_ms=fmt(to_float(b.get("elapsed_ms"))),
                b_tps=fmt(to_float(b.get("predicted_per_second"))),
                c_http=c.get("http_status", "-"),
                c_ok="ok" if to_bool(c.get("success")) else "fail",
                c_ms=fmt(to_float(c.get("elapsed_ms"))),
                c_tps=fmt(to_float(c.get("predicted_per_second"))),
            )
        )
    return "\n".join(lines)


def build_agentic_delta(
    baseline_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "baseline_first_validation": baseline_summary["baseline"]["first"]["validation_success"],
        "candidate_first_validation": candidate_summary["candidate"]["first"]["validation_success"],
        "baseline_best_validation": baseline_summary["baseline"]["best"]["validation_success"],
        "candidate_best_validation": candidate_summary["candidate"]["best"]["validation_success"],
    }


def recommendation(
    fair_agentic: dict[str, Any],
    fair_extension_artifact: dict[str, Any],
    coding_64k: dict[str, dict[str, Any]],
    coding_262k: dict[str, dict[str, Any]],
    tuned_agentic: dict[str, Any],
    tuned_extension_artifact: dict[str, Any],
) -> tuple[str, list[str]]:
    notes: list[str] = []
    fair_agentic_best_baseline = fair_agentic["baseline"]["best"]["validation_success"]
    fair_agentic_best_candidate = fair_agentic["candidate"]["best"]["validation_success"]
    fair_artifact_best_baseline = fair_extension_artifact["baseline"]["best"]["validation_success"]
    fair_artifact_best_candidate = fair_extension_artifact["candidate"]["best"]["validation_success"]

    same_param_agentic_gate_failed = (
        fair_agentic_best_candidate < fair_agentic_best_baseline
        or fair_artifact_best_candidate < fair_artifact_best_baseline
    )
    if same_param_agentic_gate_failed:
        notes.append("same-param agentic gate 未过：OmniCoder 在主 agentic 或 artifact delivery 上落后于 27B dense。")

    baseline_64k = coding_64k["baseline"]
    candidate_64k = coding_64k["candidate"]
    if candidate_64k["success"] < baseline_64k["success"]:
        notes.append("64K coding 成功数落后于 27B dense。")

    baseline_262k = coding_262k["baseline"]
    candidate_262k = coding_262k["candidate"]
    if candidate_262k["success"] > baseline_262k["success"]:
        notes.append("262K extreme 稳定性优于 27B dense。")
    elif candidate_262k["success"] < baseline_262k["success"]:
        notes.append("262K extreme 稳定性落后于 27B dense。")

    tuned_best = tuned_agentic["candidate"]["best"]["validation_success"]
    fair_best = fair_agentic["candidate"]["best"]["validation_success"]
    tuned_artifact_best = tuned_extension_artifact["candidate"]["best"]["validation_success"]
    fair_artifact_best = fair_extension_artifact["candidate"]["best"]["validation_success"]
    tuned_helps = tuned_best > fair_best or tuned_artifact_best > fair_artifact_best
    if tuned_helps:
        notes.append("OmniCoder tuned appendix 对 strict agentic 交付有增益，说明它更像需要专门 profile 的 sidecar。")

    if same_param_agentic_gate_failed:
        if tuned_helps and candidate_262k["success"] >= baseline_262k["success"]:
            return (
                "不建议替换 27B dense 为默认 coding / executor 基线；OmniCoder 更适合作为 agentic/coding reasoning 专项 sidecar。",
                notes,
            )
        return (
            "不建议替换 27B dense 为默认 coding / executor 基线；OmniCoder 在 same-param agentic gate 上没有形成优势。",
            notes,
        )

    if (
        candidate_64k["success"] >= baseline_64k["success"]
        and candidate_262k["success"] >= baseline_262k["success"]
    ):
        return (
            "可以考虑替换 27B dense；OmniCoder 在 same-param agentic gate 不落后，同时 64K/262K 结果没有明显短板。",
            notes,
        )
    return (
        "不建议直接替换；OmniCoder 虽然局部场景有潜力，但 same-param 主结论不足以支持取代 27B dense。",
        notes,
    )


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
    parser.add_argument("--extension-repo-baseline-results", required=True)
    parser.add_argument("--extension-repo-candidate-results", required=True)
    parser.add_argument("--extension-artifact-summary-json", required=True)
    parser.add_argument("--tuned-agentic-summary-json", required=True)
    parser.add_argument("--tuned-extension-repo-baseline-results", required=True)
    parser.add_argument("--tuned-extension-repo-candidate-results", required=True)
    parser.add_argument("--tuned-extension-artifact-summary-json", required=True)
    parser.add_argument("--startup-metrics-json", required=True)
    parser.add_argument("--download-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    coding_64k = {
        "baseline": summarize_coding(load_csv(Path(args.__dict__["64k_baseline_results"]))),
        "candidate": summarize_coding(load_csv(Path(args.__dict__["64k_candidate_results"]))),
    }
    coding_262k = {
        "baseline": summarize_coding(load_csv(Path(args.__dict__["262k_baseline_results"]))),
        "candidate": summarize_coding(load_csv(Path(args.__dict__["262k_candidate_results"]))),
    }
    extension_repo = {
        "baseline": summarize_coding(load_csv(Path(args.extension_repo_baseline_results))),
        "candidate": summarize_coding(load_csv(Path(args.extension_repo_candidate_results))),
    }
    tuned_extension_repo = {
        "baseline": summarize_coding(load_csv(Path(args.tuned_extension_repo_baseline_results))),
        "candidate": summarize_coding(load_csv(Path(args.tuned_extension_repo_candidate_results))),
    }

    fair_agentic = load_json(Path(args.agentic_summary_json))
    fair_extension_artifact = load_json(Path(args.extension_artifact_summary_json))
    tuned_agentic = load_json(Path(args.tuned_agentic_summary_json))
    tuned_extension_artifact = load_json(Path(args.tuned_extension_artifact_summary_json))
    startup_metrics = load_json(Path(args.startup_metrics_json))
    download_meta = load_json(Path(args.download_json))

    startup_summary = {round_key: summarize_startup_round(items) for round_key, items in startup_metrics.items()}
    final_recommendation, recommendation_notes = recommendation(
        fair_agentic,
        fair_extension_artifact,
        coding_64k,
        coding_262k,
        tuned_agentic,
        tuned_extension_artifact,
    )

    payload = {
        "generated_at_utc": utc_now(),
        "baseline_key": args.baseline_key,
        "candidate_key": args.candidate_key,
        "baseline_name": args.baseline_name,
        "candidate_name": args.candidate_name,
        "download": download_meta,
        "coding_64k": coding_64k,
        "coding_262k": coding_262k,
        "fair_agentic": fair_agentic,
        "fair_extension_repo": extension_repo,
        "fair_extension_artifact": fair_extension_artifact,
        "tuned_agentic": tuned_agentic,
        "tuned_extension_repo": tuned_extension_repo,
        "tuned_extension_artifact": tuned_extension_artifact,
        "startup_summary": startup_summary,
        "recommendation": final_recommendation,
        "recommendation_notes": recommendation_notes,
    }
    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    notes_block = "".join(f"- {note}\n" for note in recommendation_notes) if recommendation_notes else "- 无额外备注。\n"

    report = f"""# OmniCoder-9B Q8_0 vs 27B Dense Report

- Generated at (UTC): `{payload['generated_at_utc']}`
- Baseline: `{args.baseline_name}`
- Candidate: `{args.candidate_name}`

## Download

- ModelScope repo: `{download_meta['source']['repo']}`
- file: `{download_meta['source']['name']}`
- size: `{download_meta['remote']['size']}`
- sha256: `{download_meta['remote']['sha256']}`
- downloaded this run: `{download_meta['downloaded']}`

## Fair Profile: 64K Coding

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| success / total | {coding_64k['baseline']['success']} / {coding_64k['baseline']['task_count']} | {coding_64k['candidate']['success']} / {coding_64k['candidate']['task_count']} |
| success rate | {pct(coding_64k['baseline']['success'], coding_64k['baseline']['task_count'])} | {pct(coding_64k['candidate']['success'], coding_64k['candidate']['task_count'])} |
| avg elapsed_ms | {fmt(coding_64k['baseline']['avg_elapsed_ms'])} | {fmt(coding_64k['candidate']['avg_elapsed_ms'])} |
| avg predicted_per_second | {fmt(coding_64k['baseline']['avg_predicted_per_second'])} | {fmt(coding_64k['candidate']['avg_predicted_per_second'])} |
| avg reasoning_content_length | {fmt(coding_64k['baseline']['avg_reasoning_len'])} | {fmt(coding_64k['candidate']['avg_reasoning_len'])} |
| avg content_length | {fmt(coding_64k['baseline']['avg_content_len'])} | {fmt(coding_64k['candidate']['avg_content_len'])} |

## Fair Profile: 262K Extreme

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| success / total | {coding_262k['baseline']['success']} / {coding_262k['baseline']['task_count']} | {coding_262k['candidate']['success']} / {coding_262k['candidate']['task_count']} |
| success rate | {pct(coding_262k['baseline']['success'], coding_262k['baseline']['task_count'])} | {pct(coding_262k['candidate']['success'], coding_262k['candidate']['task_count'])} |
| avg elapsed_ms | {fmt(coding_262k['baseline']['avg_elapsed_ms'])} | {fmt(coding_262k['candidate']['avg_elapsed_ms'])} |
| avg predicted_per_second | {fmt(coding_262k['baseline']['avg_predicted_per_second'])} | {fmt(coding_262k['candidate']['avg_predicted_per_second'])} |

## Fair Profile: Agentic Main

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| first validation success | {fair_agentic['baseline']['first']['validation_success']} / {fair_agentic['baseline']['first']['task_count']} | {fair_agentic['candidate']['first']['validation_success']} / {fair_agentic['candidate']['first']['task_count']} |
| best-of-2 validation success | {fair_agentic['baseline']['best']['validation_success']} / {fair_agentic['baseline']['best']['task_count']} | {fair_agentic['candidate']['best']['validation_success']} / {fair_agentic['candidate']['best']['task_count']} |
| best-of-2 json parse success | {fair_agentic['baseline']['best']['json_parse_success']} / {fair_agentic['baseline']['best']['task_count']} | {fair_agentic['candidate']['best']['json_parse_success']} / {fair_agentic['candidate']['best']['task_count']} |
| best-of-2 avg elapsed_ms | {fmt(fair_agentic['baseline']['best']['avg_elapsed_ms'])} | {fmt(fair_agentic['candidate']['best']['avg_elapsed_ms'])} |

## Fair Profile: Agentic Extension

### Repo reasoning subset

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| success / total | {extension_repo['baseline']['success']} / {extension_repo['baseline']['task_count']} | {extension_repo['candidate']['success']} / {extension_repo['candidate']['task_count']} |
| success rate | {pct(extension_repo['baseline']['success'], extension_repo['baseline']['task_count'])} | {pct(extension_repo['candidate']['success'], extension_repo['candidate']['task_count'])} |
| avg elapsed_ms | {fmt(extension_repo['baseline']['avg_elapsed_ms'])} | {fmt(extension_repo['candidate']['avg_elapsed_ms'])} |
| avg predicted_per_second | {fmt(extension_repo['baseline']['avg_predicted_per_second'])} | {fmt(extension_repo['candidate']['avg_predicted_per_second'])} |

### Artifact delivery subset

| Metric | {args.baseline_key} | {args.candidate_key} |
| --- | ---: | ---: |
| first validation success | {fair_extension_artifact['baseline']['first']['validation_success']} / {fair_extension_artifact['baseline']['first']['task_count']} | {fair_extension_artifact['candidate']['first']['validation_success']} / {fair_extension_artifact['candidate']['first']['task_count']} |
| best validation success | {fair_extension_artifact['baseline']['best']['validation_success']} / {fair_extension_artifact['baseline']['best']['task_count']} | {fair_extension_artifact['candidate']['best']['validation_success']} / {fair_extension_artifact['candidate']['best']['task_count']} |
| best json parse success | {fair_extension_artifact['baseline']['best']['json_parse_success']} / {fair_extension_artifact['baseline']['best']['task_count']} | {fair_extension_artifact['candidate']['best']['json_parse_success']} / {fair_extension_artifact['candidate']['best']['task_count']} |
| best avg elapsed_ms | {fmt(fair_extension_artifact['baseline']['best']['avg_elapsed_ms'])} | {fmt(fair_extension_artifact['candidate']['best']['avg_elapsed_ms'])} |

## OmniCoder Tuned Appendix

### Main agentic

| Metric | fair OmniCoder | tuned OmniCoder |
| --- | ---: | ---: |
| first validation success | {fair_agentic['candidate']['first']['validation_success']} / {fair_agentic['candidate']['first']['task_count']} | {tuned_agentic['candidate']['first']['validation_success']} / {tuned_agentic['candidate']['first']['task_count']} |
| best validation success | {fair_agentic['candidate']['best']['validation_success']} / {fair_agentic['candidate']['best']['task_count']} | {tuned_agentic['candidate']['best']['validation_success']} / {tuned_agentic['candidate']['best']['task_count']} |
| best avg elapsed_ms | {fmt(fair_agentic['candidate']['best']['avg_elapsed_ms'])} | {fmt(tuned_agentic['candidate']['best']['avg_elapsed_ms'])} |

### Repo reasoning subset

| Metric | fair OmniCoder | tuned OmniCoder |
| --- | ---: | ---: |
| success / total | {tuned_extension_repo['baseline']['success']} / {tuned_extension_repo['baseline']['task_count']} | {tuned_extension_repo['candidate']['success']} / {tuned_extension_repo['candidate']['task_count']} |
| avg elapsed_ms | {fmt(tuned_extension_repo['baseline']['avg_elapsed_ms'])} | {fmt(tuned_extension_repo['candidate']['avg_elapsed_ms'])} |
| avg predicted_per_second | {fmt(tuned_extension_repo['baseline']['avg_predicted_per_second'])} | {fmt(tuned_extension_repo['candidate']['avg_predicted_per_second'])} |

### Artifact delivery subset

| Metric | fair OmniCoder | tuned OmniCoder |
| --- | ---: | ---: |
| first validation success | {fair_extension_artifact['candidate']['first']['validation_success']} / {fair_extension_artifact['candidate']['first']['task_count']} | {tuned_extension_artifact['candidate']['first']['validation_success']} / {tuned_extension_artifact['candidate']['first']['task_count']} |
| best validation success | {fair_extension_artifact['candidate']['best']['validation_success']} / {fair_extension_artifact['candidate']['best']['task_count']} | {tuned_extension_artifact['candidate']['best']['validation_success']} / {tuned_extension_artifact['candidate']['best']['task_count']} |
| best avg elapsed_ms | {fmt(fair_extension_artifact['candidate']['best']['avg_elapsed_ms'])} | {fmt(tuned_extension_artifact['candidate']['best']['avg_elapsed_ms'])} |

## Startup Summary

| Round | Model | avg startup ms | avg idle GPU MiB | avg idle GPU util % |
| --- | --- | ---: | ---: | ---: |
| 64k | {args.baseline_key} | {fmt(startup_summary.get('64k', {}).get(args.baseline_key, {}).get('avg_startup_elapsed_ms'))} | {fmt(startup_summary.get('64k', {}).get(args.baseline_key, {}).get('avg_idle_gpu_memory_mib'))} | {fmt(startup_summary.get('64k', {}).get(args.baseline_key, {}).get('avg_idle_gpu_util_pct'))} |
| 64k | {args.candidate_key} | {fmt(startup_summary.get('64k', {}).get(args.candidate_key, {}).get('avg_startup_elapsed_ms'))} | {fmt(startup_summary.get('64k', {}).get(args.candidate_key, {}).get('avg_idle_gpu_memory_mib'))} | {fmt(startup_summary.get('64k', {}).get(args.candidate_key, {}).get('avg_idle_gpu_util_pct'))} |
| 262k | {args.baseline_key} | {fmt(startup_summary.get('262k', {}).get(args.baseline_key, {}).get('avg_startup_elapsed_ms'))} | {fmt(startup_summary.get('262k', {}).get(args.baseline_key, {}).get('avg_idle_gpu_memory_mib'))} | {fmt(startup_summary.get('262k', {}).get(args.baseline_key, {}).get('avg_idle_gpu_util_pct'))} |
| 262k | {args.candidate_key} | {fmt(startup_summary.get('262k', {}).get(args.candidate_key, {}).get('avg_startup_elapsed_ms'))} | {fmt(startup_summary.get('262k', {}).get(args.candidate_key, {}).get('avg_idle_gpu_memory_mib'))} | {fmt(startup_summary.get('262k', {}).get(args.candidate_key, {}).get('avg_idle_gpu_util_pct'))} |

## Recommendation

{final_recommendation}

### Notes

{notes_block}

## 64K Coding Per Task Snapshot

| Task | {args.baseline_key} http | {args.baseline_key} status | {args.baseline_key} ms | {args.baseline_key} tok/s | {args.candidate_key} http | {args.candidate_key} status | {args.candidate_key} ms | {args.candidate_key} tok/s |
| --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: |
{build_coding_table(args.baseline_key, args.candidate_key, coding_64k['baseline'], coding_64k['candidate'])}
"""
    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
