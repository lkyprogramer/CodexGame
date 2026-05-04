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


def select_best_attempts(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)

    selected: dict[str, dict[str, str]] = {}
    for task_id, task_rows in grouped.items():
        task_rows.sort(key=lambda row: int(row["repeat_index"]))
        successful = [row for row in task_rows if row["success"].lower() == "true"]
        selected[task_id] = successful[0] if successful else task_rows[0]
    return selected


def response_index(items: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    return {
        (item["task_id"], int(item["repeat_index"])): item
        for item in items
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-results", required=True)
    parser.add_argument("--candidate-results", required=True)
    parser.add_argument("--baseline-key", required=True)
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--task-manifest", required=True)
    parser.add_argument("--baseline-responses", required=True)
    parser.add_argument("--candidate-responses", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-template-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    baseline_rows = select_best_attempts(load_csv(Path(args.baseline_results)))
    candidate_rows = select_best_attempts(load_csv(Path(args.candidate_results)))
    manifest = {
        item["task_id"]: item
        for item in load_json(Path(args.task_manifest))
    }
    baseline_response_idx = response_index(load_json(Path(args.baseline_responses)))
    candidate_response_idx = response_index(load_json(Path(args.candidate_responses)))

    packet: list[dict[str, Any]] = []
    template: list[dict[str, Any]] = []
    md_sections: list[str] = ["# Qwen Compare Score Packet", ""]

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

        for model_key, rows, response_idx in [
            (args.baseline_key, baseline_rows, baseline_response_idx),
            (args.candidate_key, candidate_rows, candidate_response_idx),
        ]:
            row = rows[task_id]
            repeat_index = int(row["repeat_index"])
            response_info = response_idx.get((task_id, repeat_index), {})
            response_file = response_info.get("response_file", "")
            request_file = response_info.get("request_file", "")
            packet.append(
                {
                    "model_key": model_key,
                    "task_id": task_id,
                    "description": task["description"],
                    "hidden_checklist": task["hidden_checklist"],
                    "http_status": row["http_status"],
                    "success": row["success"].lower() == "true",
                    "elapsed_ms": row["elapsed_ms"],
                    "predicted_per_second": row["predicted_per_second"],
                    "content_preview": row["content_preview"],
                    "reasoning_preview": row["reasoning_preview"],
                    "request_file": request_file,
                    "response_file": response_file,
                }
            )
            template.append(
                {
                    "model_key": model_key,
                    "task_id": task_id,
                    "score_total": None,
                    "score_accuracy": None,
                    "score_root_cause": None,
                    "score_minimality": None,
                    "score_constraints": None,
                    "score_penalty": 0,
                    "pass": row["success"].lower() == "true",
                    "notes": "",
                }
            )

            md_sections.extend(
                [
                    f"### {model_key}",
                    "",
                    f"- http_status: `{row['http_status']}`",
                    f"- success: `{row['success']}`",
                    f"- elapsed_ms: `{row['elapsed_ms']}`",
                    f"- predicted_per_second: `{row['predicted_per_second']}`",
                    f"- request_file: `{request_file}`",
                    f"- response_file: `{response_file}`",
                    "",
                    "Content preview:",
                    "",
                    "```text",
                    row["content_preview"],
                    "```",
                    "",
                    "Reasoning preview:",
                    "",
                    "```text",
                    row["reasoning_preview"],
                    "```",
                    "",
                ]
            )

    Path(args.output_json).write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.output_template_json).write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.output_md).write_text("\n".join(md_sections).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote score packet: {args.output_json}")
    print(f"Wrote score template: {args.output_template_json}")
    print(f"Wrote score markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
