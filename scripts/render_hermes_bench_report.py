#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
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


def to_bool(value: str | bool | None) -> bool:
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


def strip_ansi(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
    text = text.replace("\r", "\n")
    return text


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
        values = []
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


def response_index(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["task_id"]: item for item in items}


def resolve_bundle_path(raw_path: str | None, fallback_dir: Path) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.exists():
        return path
    candidate = fallback_dir / path.name
    return candidate if candidate.exists() else None


def load_session_final_content(session_path: Path | None) -> str:
    if not session_path or not session_path.exists():
        return ""
    try:
        data = load_json(session_path)
    except Exception:
        return ""
    messages = data.get("messages")
    if not isinstance(messages, list):
        return ""
    for item in reversed(messages):
        if not isinstance(item, dict):
            continue
        if item.get("role") != "assistant":
            continue
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def session_used_tool(session_path: Path | None) -> bool:
    if not session_path or not session_path.exists():
        return False
    try:
        data = load_json(session_path)
    except Exception:
        return False
    messages = data.get("messages")
    if not isinstance(messages, list):
        return False
    return any(isinstance(item, dict) and item.get("role") == "tool" for item in messages)


def extract_json_tail(text: str) -> str:
    stripped = text.strip()
    for open_char, close_char in [("{", "}"), ("[", "]")]:
        end = stripped.rfind(close_char)
        if end == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for idx in range(end, -1, -1):
            ch = stripped[idx]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == close_char:
                depth += 1
            elif ch == open_char:
                depth -= 1
                if depth == 0:
                    candidate = stripped[idx : end + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except Exception:
                        break
    return ""


def normalize_stdout(stdout_path: Path | None) -> str:
    if not stdout_path or not stdout_path.exists():
        return ""
    cleaned = strip_ansi(stdout_path.read_text(encoding="utf-8", errors="replace"))
    json_tail = extract_json_tail(cleaned)
    if json_tail:
        return json_tail
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    filtered = []
    for line in lines:
        if line.startswith("session_id:"):
            continue
        if line.startswith("WARNING:"):
            continue
        if line.startswith("⠋") or line.startswith("⠙") or line.startswith("⠹") or line.startswith("⠸"):
            continue
        if line.startswith("⠼") or line.startswith("⠴") or line.startswith("⠦") or line.startswith("⠧"):
            continue
        if line.startswith("⠇") or line.startswith("⠏"):
            continue
        if line.startswith("┊ 🔎") or line.startswith("┊ 💻") or line.startswith("┊ 📖") or line.startswith("┊ 🔧"):
            continue
        filtered.append(line)
    return "\n".join(filtered).strip()


def normalize_final_output(record: dict[str, Any], outputs_dir: Path, sessions_dir: Path) -> str:
    session_path = resolve_bundle_path(record.get("session_file"), sessions_dir)
    session_content = load_session_final_content(session_path)
    if session_content:
        json_tail = extract_json_tail(session_content)
        return json_tail or session_content
    stdout_path = resolve_bundle_path(record.get("stdout_file"), outputs_dir)
    stdout_content = normalize_stdout(stdout_path)
    if stdout_content:
        return stdout_content
    return str(record.get("final_output") or "").strip()


def filtered_changed_files(record: dict[str, Any]) -> list[str]:
    raw = record.get("changed_files") or []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = []
    ignored_parts = (
        "/__pycache__/",
        ".pytest_cache/",
        ".pyc",
        "CACHEDIR.TAG",
        "README.md",
        ".gitignore",
        "v/cache/",
    )
    filtered = []
    for item in raw:
        if any(part in item for part in ignored_parts):
            continue
        filtered.append(item)
    return filtered


def validate_contract(task: dict[str, Any], final_output: str) -> tuple[bool, bool]:
    kind = task["output_contract"]["kind"]
    spec = task["output_contract"]["spec"]
    json_parse_success = False
    parsed: Any = None
    if kind.startswith("json"):
        try:
            parsed = json.loads(final_output)
            json_parse_success = True
        except Exception:
            return False, False

    if kind == "exact_text":
        return final_output.strip() == spec["text"], json_parse_success
    if kind == "line_prefixes":
        lines = [line.strip() for line in final_output.splitlines() if line.strip()]
        if "required_prefixes" in spec:
            prefixes = spec["required_prefixes"]
            return len(lines) == spec.get("exact_count", len(prefixes)) and all(
                line.startswith(prefix) for line, prefix in zip(lines, prefixes)
            ), json_parse_success
        expected = spec.get("lines", [])
        return lines == expected, json_parse_success
    if kind == "bullet_count":
        bullets = [line for line in final_output.splitlines() if line.strip().startswith("-")]
        return len(bullets) == spec["count"], json_parse_success
    if kind == "sections":
        lines = [line.strip() for line in final_output.splitlines() if line.strip()]
        return all(any(line.startswith(prefix) for line in lines) for prefix in spec["required_prefixes"]), json_parse_success
    if kind == "json_keys":
        if not isinstance(parsed, dict):
            return False, json_parse_success
        if any(key not in parsed for key in spec.get("required_keys", [])):
            return False, json_parse_success
        for key, expected in spec.get("exact_values", {}).items():
            if parsed.get(key) != expected:
                return False, json_parse_success
        return True, json_parse_success
    if kind == "json_array_length":
        if not isinstance(parsed, dict):
            return False, json_parse_success
        value = parsed.get(spec["root_key"])
        return isinstance(value, list) and len(value) == spec["length"], json_parse_success
    raise ValueError(f"Unknown contract kind: {kind}")


def keyword_hits(task: dict[str, Any], final_output: str) -> list[str]:
    lowered = final_output.lower()
    return [item for item in task.get("expected_snippets", []) if item.lower() in lowered]


def enrich_rows(
    rows: list[dict[str, str]],
    manifest: dict[str, Any],
    responses: dict[str, dict[str, Any]],
    outputs_dir: Path,
    sessions_dir: Path,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        task = manifest[row["task_id"]]
        response = responses.get(row["task_id"], {})
        final_output = normalize_final_output(response, outputs_dir, sessions_dir)
        contract_ok, json_ok = validate_contract(task, final_output)
        changed = filtered_changed_files(response)
        session_path = resolve_bundle_path(response.get("session_file"), sessions_dir)
        stdout_path = resolve_bundle_path(response.get("stdout_file"), outputs_dir)
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path else ""
        enriched.append(
            {
                **row,
                "normalized_output": final_output,
                "contract_success_eval": contract_ok,
                "json_parse_success_eval": json_ok,
                "terminal_tool_used_eval": to_bool(row.get("terminal_tool_used"))
                or ("💻" in stdout_text)
                or session_used_tool(session_path),
                "changed_files_eval": changed,
                "changed_files_count_eval": len(changed),
                "keyword_hits_eval": keyword_hits(task, final_output),
                "keyword_hit_count_eval": len(keyword_hits(task, final_output)),
            }
        )
    return enriched


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    return {
        "task_count": total,
        "process_success": sum(int(str(row["hermes_exit_code"]) == "0") for row in rows),
        "contract_success": sum(bool(row["contract_success_eval"]) for row in rows),
        "json_parse_success": sum(bool(row["json_parse_success_eval"]) for row in rows),
        "validation_success": sum(bool(to_bool(row["validation_success"])) for row in rows),
        "terminal_tool_used": sum(bool(row["terminal_tool_used_eval"]) for row in rows),
        "avg_elapsed_ms": mean([to_float(row["elapsed_ms"]) for row in rows]),
        "avg_keyword_hits": mean([to_float(row["keyword_hit_count_eval"]) for row in rows]),
        "avg_changed_files": mean([to_float(row["changed_files_count_eval"]) for row in rows]),
    }


def score_row(row: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    task = manifest[row["task_id"]]
    readonly = to_bool(row["readonly"])
    sandbox = to_bool(row["sandbox_write"])
    contract_ok = bool(row["contract_success_eval"])
    json_ok = bool(row["json_parse_success_eval"])
    validation_ok = to_bool(row["validation_success"])
    terminal_ok = bool(row["terminal_tool_used_eval"])
    keyword_hits_count = int(row["keyword_hit_count_eval"])
    expected_count = max(len(task.get("expected_snippets", [])), 1)
    changed_count = int(row["changed_files_count_eval"])
    max_expected = task.get("max_expected_changed_files")

    completion = 0
    if sandbox:
        completion = 4 if validation_ok else (2 if contract_ok else 0)
    elif row["task_family"] == "basic":
        completion = 4 if contract_ok else 0
    else:
        completion = 4 if contract_ok and (keyword_hits_count / expected_count) >= 0.5 else (2 if contract_ok else 0)

    evidence = min(4, round((keyword_hits_count / expected_count) * 4))
    if row["task_family"] == "basic":
        evidence = 4 if contract_ok else 0
    if row["task_family"] == "terminal":
        evidence = 4 if terminal_ok and contract_ok else (2 if contract_ok else 0)

    constraints = 4
    if readonly and changed_count > 0:
        constraints = 0
    elif sandbox and max_expected is not None and changed_count > max_expected:
        constraints = 1
    elif sandbox and validation_ok:
        constraints = 4
    elif contract_ok:
        constraints = 3

    contract_score = 4 if contract_ok else (2 if json_ok else 0)
    penalty = 0
    if not contract_ok and not validation_ok:
        penalty -= 2
    if readonly and changed_count > 0:
        penalty -= 3
    if row.get("error_message"):
        penalty -= 1

    total = completion + evidence + constraints + contract_score + penalty
    passed = False
    if sandbox:
        passed = validation_ok
    elif row["task_family"] == "terminal":
        passed = contract_ok and terminal_ok
    else:
        passed = contract_ok

    return {
        "task_id": row["task_id"],
        "family": row["task_family"],
        "description": row["description"],
        "score_completion": completion,
        "score_evidence": evidence,
        "score_constraints": constraints,
        "score_contract": contract_score,
        "score_penalty": penalty,
        "score_total": total,
        "pass": passed,
        "notes": "",
    }


def family_summary(rows: list[dict[str, Any]], scores: list[dict[str, Any]]) -> dict[str, Any]:
    grouped_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_rows[row["task_family"]].append(row)
    score_by_task = {item["task_id"]: item for item in scores}
    payload: dict[str, Any] = {}
    for family, family_rows in grouped_rows.items():
        family_scores = [score_by_task[row["task_id"]] for row in family_rows]
        payload[family] = {
            "count": len(family_rows),
            "pass_count": sum(bool(item["pass"]) for item in family_scores),
            "avg_score": mean([to_float(item["score_total"]) for item in family_scores]),
            "contract_success": sum(bool(row["contract_success_eval"]) for row in family_rows),
            "validation_success": sum(bool(to_bool(row["validation_success"])) for row in family_rows),
            "terminal_tool_used": sum(bool(row["terminal_tool_used_eval"]) for row in family_rows),
        }
    return payload


def recommendation(rows: list[dict[str, Any]], scores: list[dict[str, Any]]) -> str:
    families = family_summary(rows, scores)
    total = len(rows)
    pass_count = sum(bool(item["pass"]) for item in scores)
    contract_success = sum(bool(row["contract_success_eval"]) for row in rows)
    sandbox = families.get("sandbox", {})
    repo_readonly = families.get("repo_readonly", {})
    terminal = families.get("terminal", {})
    if (
        total > 0
        and pass_count / total >= 0.85
        and sandbox.get("pass_count", 0) >= 4
        and repo_readonly.get("pass_count", 0) >= 5
        and terminal.get("pass_count", 0) >= 3
    ):
        return "推荐作为日常主力：Hermes 在当前模型下的稳定性、结构化输出和沙箱执行能力都达到可用阈值。"
    if (
        contract_success / total >= 0.45
        and repo_readonly.get("pass_count", 0) >= 2
        and terminal.get("pass_count", 0) >= 1
        and sandbox.get("pass_count", 0) >= 4
    ):
        return "可用，但必须加 guardrail：Hermes 的工具与沙箱交付能力可用，但结构化输出和 CLI 稳定性仍需要包装层、重试和输出清洗。"
    return "不建议作为主力 agent：当前结构化输出、工具调用或沙箱交付稳定性仍不足。"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-csv", required=True)
    parser.add_argument("--task-manifest", required=True)
    parser.add_argument("--responses-json", required=True)
    parser.add_argument("--gpu-samples", required=True)
    parser.add_argument("--service-health-pre", required=True)
    parser.add_argument("--service-health-post", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-score-json", required=True)
    args = parser.parse_args()

    rows = load_csv(Path(args.results_csv))
    manifest = {item["task_id"]: item for item in load_json(Path(args.task_manifest))}
    responses_path = Path(args.responses_json)
    responses = response_index(load_json(responses_path))
    raw_dir = responses_path.parent
    outputs_dir = raw_dir / "outputs"
    sessions_dir = raw_dir / "sessions"
    enriched = enrich_rows(rows, manifest, responses, outputs_dir, sessions_dir)
    scores = [score_row(row, manifest) for row in enriched]

    payload = {
        "generated_at_utc": utc_now(),
        "aggregate": aggregate(enriched),
        "family_summary": family_summary(enriched, scores),
        "gpu_stats": load_gpu_stats(Path(args.gpu_samples)),
        "service_health_pre": load_json(Path(args.service_health_pre)),
        "service_health_post": load_json(Path(args.service_health_post)),
        "recommendation": recommendation(enriched, scores),
    }

    Path(args.output_score_json).write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report_lines = [
        "# Hermes Benchmark Report",
        "",
        f"- Generated at (UTC): `{payload['generated_at_utc']}`",
        f"- Overall pass: `{sum(bool(item['pass']) for item in scores)} / {len(scores)}`",
        f"- Process success: `{payload['aggregate']['process_success']} / {payload['aggregate']['task_count']}`",
        f"- Contract success: `{payload['aggregate']['contract_success']} / {payload['aggregate']['task_count']}`",
        f"- JSON parse success: `{payload['aggregate']['json_parse_success']} / {payload['aggregate']['task_count']}`",
        f"- Validation success: `{payload['aggregate']['validation_success']} / {payload['aggregate']['task_count']}`",
        f"- Terminal tool used: `{payload['aggregate']['terminal_tool_used']} / {payload['aggregate']['task_count']}`",
        f"- Avg elapsed_ms: `{fmt(payload['aggregate']['avg_elapsed_ms'])}`",
        "",
        "## GPU Stats",
        "",
        f"- avg_memory_used_mib: `{fmt(payload['gpu_stats']['avg_memory_used_mib'])}`",
        f"- max_memory_used_mib: `{fmt(payload['gpu_stats']['max_memory_used_mib'])}`",
        f"- avg_gpu_util_pct: `{fmt(payload['gpu_stats']['avg_gpu_util_pct'])}`",
        f"- max_gpu_util_pct: `{fmt(payload['gpu_stats']['max_gpu_util_pct'])}`",
        "",
        "## Family Summary",
        "",
        "| Family | Pass | Contract | Validation | Terminal Used | Avg Score |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for family, summary in payload["family_summary"].items():
        report_lines.append(
            f"| {family} | {summary['pass_count']} / {summary['count']} | "
            f"{summary['contract_success']} / {summary['count']} | "
            f"{summary['validation_success']} / {summary['count']} | "
            f"{summary['terminal_tool_used']} / {summary['count']} | "
            f"{fmt(summary['avg_score'])} |"
        )

    report_lines.extend(
        [
            "",
            "## Recommendation",
            "",
            payload["recommendation"],
            "",
            "## Per Task Scores",
            "",
            "| Task | Family | Pass | Total | Completion | Evidence | Constraints | Contract | Penalty |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for score in scores:
        report_lines.append(
            f"| {score['task_id']} | {score['family']} | {score['pass']} | {score['score_total']} | "
            f"{score['score_completion']} | {score['score_evidence']} | {score['score_constraints']} | "
            f"{score['score_contract']} | {score['score_penalty']} |"
        )

    Path(args.output_md).write_text("\n".join(report_lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
