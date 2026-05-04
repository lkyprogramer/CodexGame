#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def to_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def grouped_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    for task_rows in grouped.values():
        task_rows.sort(key=lambda row: int(row["repeat_index"]))
    return grouped


def best_attempt(task_rows: list[dict[str, str]]) -> dict[str, str]:
    validation = [row for row in task_rows if to_bool(row.get("validation_success"))]
    parse = [row for row in task_rows if to_bool(row.get("json_parse_success"))]
    request = [row for row in task_rows if to_bool(row.get("request_success"))]
    return (validation or parse or request or task_rows)[0]


def response_index(items: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    return {
        (item["task_id"], int(item["repeat_index"])): item
        for item in items
    }


def workspace_path(workspace_root: Path, task_id: str, model_key: str, repeat_index: int) -> Path:
    return workspace_root / task_id / model_key / f"repeat-{repeat_index}"


def read_validation_tail(workspace_dir: Path) -> str:
    candidates = sorted(workspace_dir.rglob("*.py"))[:0]
    del candidates
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-results", required=True)
    parser.add_argument("--candidate-results", required=True)
    parser.add_argument("--baseline-key", required=True)
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--task-manifest", required=True)
    parser.add_argument("--baseline-responses", required=True)
    parser.add_argument("--candidate-responses", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-template-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    baseline_grouped = grouped_rows(load_csv(Path(args.baseline_results)))
    candidate_grouped = grouped_rows(load_csv(Path(args.candidate_results)))
    manifest = {item["task_id"]: item for item in load_json(Path(args.task_manifest))}
    baseline_response_idx = response_index(load_json(Path(args.baseline_responses)))
    candidate_response_idx = response_index(load_json(Path(args.candidate_responses)))
    workspace_root = Path(args.workspace_root)

    packet: list[dict[str, Any]] = []
    template: list[dict[str, Any]] = []
    md_sections: list[str] = ["# Qwen Agentic Score Packet", ""]

    for task_id in sorted(manifest):
        task = manifest[task_id]
        md_sections.append(f"## {task_id}")
        md_sections.append("")
        md_sections.append(task["description"])
        md_sections.append("")
        md_sections.append("Hidden checklist:")
        for item in task["hidden_checklist"]:
            md_sections.append(f"- {item}")
        md_sections.append("")

        for model_key, grouped, response_idx in [
            (args.baseline_key, baseline_grouped, baseline_response_idx),
            (args.candidate_key, candidate_grouped, candidate_response_idx),
        ]:
            attempts = grouped.get(task_id, [])
            row = best_attempt(attempts)
            repeat_index = int(row["repeat_index"])
            response_info = response_idx.get((task_id, repeat_index), {})
            workspace_dir = workspace_path(workspace_root, task_id, model_key, repeat_index)
            files_written = json.loads(row.get("files_written") or "[]")
            patch_files = [
                str(workspace_dir / file_path)
                for file_path in files_written
            ]

            packet.append(
                {
                    "model_key": model_key,
                    "task_id": task_id,
                    "description": task["description"],
                    "hidden_checklist": task["hidden_checklist"],
                    "best_repeat_index": repeat_index,
                    "http_status": row["http_status"],
                    "request_success": to_bool(row.get("request_success")),
                    "json_parse_success": to_bool(row.get("json_parse_success")),
                    "validation_success": to_bool(row.get("validation_success")),
                    "files_written_count": row.get("files_written_count"),
                    "files_written": files_written,
                    "summary_preview": row.get("summary_preview", ""),
                    "elapsed_ms": row.get("elapsed_ms"),
                    "predicted_per_second": row.get("predicted_per_second"),
                    "response_file": response_info.get("response_file", ""),
                    "workspace_dir": str(workspace_dir),
                    "patch_files": patch_files,
                    "all_attempts": attempts,
                }
            )
            template.append(
                {
                    "model_key": model_key,
                    "task_id": task_id,
                    "score_total": None,
                    "score_validation": 4 if to_bool(row.get("validation_success")) else 0,
                    "score_patch_correctness": None,
                    "score_minimality": None,
                    "score_contract": 1 if to_bool(row.get("json_parse_success")) else 0,
                    "pass": to_bool(row.get("validation_success")),
                    "winner": "",
                    "notes": "",
                }
            )

            md_sections.extend(
                [
                    f"### {model_key}",
                    "",
                    f"- best_repeat_index: `{repeat_index}`",
                    f"- http_status: `{row['http_status']}`",
                    f"- request_success: `{row.get('request_success')}`",
                    f"- json_parse_success: `{row.get('json_parse_success')}`",
                    f"- validation_success: `{row.get('validation_success')}`",
                    f"- files_written: `{files_written}`",
                    f"- elapsed_ms: `{row.get('elapsed_ms')}`",
                    f"- predicted_per_second: `{row.get('predicted_per_second')}`",
                    f"- response_file: `{response_info.get('response_file', '')}`",
                    f"- workspace_dir: `{workspace_dir}`",
                    "",
                    "Summary preview:",
                    "",
                    "```text",
                    row.get("summary_preview", ""),
                    "```",
                    "",
                    "Patch files:",
                ]
            )
            for patch_file in patch_files:
                md_sections.append(f"- `{patch_file}`")
            md_sections.append("")

    Path(args.output_json).write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.output_template_json).write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.output_md).write_text("\n".join(md_sections).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote agentic score packet: {args.output_json}")
    print(f"Wrote agentic score template: {args.output_template_json}")
    print(f"Wrote agentic score markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
