#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic_model_compare_tasks import AgenticTask, get_agentic_tasks


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def send_chat_request(
    base_url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout_seconds: int,
) -> tuple[int, dict[str, Any], float]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers=build_headers(api_key),
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return response.status, json.loads(raw.decode("utf-8")), elapsed_ms
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {"raw_error": raw.decode("utf-8", errors="replace")}
        return exc.code, payload, elapsed_ms
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return 0, {"exception": repr(exc)}, elapsed_ms


def extract_json_payload(text: str) -> dict[str, Any]:
    candidate = text.strip()
    return json.loads(candidate)


def materialize_workspace(task: AgenticTask, workspace_dir: Path) -> None:
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    for file in task.workspace_files:
        path = workspace_dir / file.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file.content, encoding="utf-8")


def apply_generated_files(workspace_dir: Path, files: list[dict[str, Any]]) -> list[str]:
    written: list[str] = []
    for file in files:
        path = workspace_dir / file["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file["content"], encoding="utf-8")
        written.append(file["path"])
    return written


def run_validations(task: AgenticTask, workspace_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in task.validation_commands:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=workspace_dir,
            capture_output=True,
            text=True,
        )
        results.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "success": completed.returncode == 0,
            }
        )
    return results


def select_tasks(tasks: list[AgenticTask], task_ids: set[str]) -> list[AgenticTask]:
    if not task_ids:
        return tasks
    return [task for task in tasks if task.task_id in task_ids]


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", default="sk-no-key-required")
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-key", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=2400)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--instruction-role", choices=["system", "developer"], default="system")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    workspace_root = Path(args.workspace_root).resolve()
    ensure_dir(output_dir)
    ensure_dir(workspace_root)
    ensure_dir(output_dir / "responses")
    ensure_dir(output_dir / "requests")

    tasks = select_tasks(get_agentic_tasks(), set(args.task_id))
    if not tasks:
        raise SystemExit("No tasks selected")

    rows: list[dict[str, Any]] = []
    response_records: list[dict[str, Any]] = []

    for task in tasks:
        payload = {
            "model": args.model,
            "messages": [
                {"role": args.instruction_role, "content": task.system_message},
                {"role": "user", "content": task.render_user_message()},
            ],
            "max_tokens": task.max_tokens,
            "stream": False,
        }

        for repeat_index in range(1, args.repeat + 1):
            workspace_dir = workspace_root / task.task_id / args.model_key / f"repeat-{repeat_index}"
            materialize_workspace(task, workspace_dir)

            request_file = output_dir / "requests" / f"{task.task_id}.repeat-{repeat_index}.json"
            save_json(request_file, payload)

            http_status, response, elapsed_ms = send_chat_request(
                args.base_url,
                args.api_key,
                payload,
                args.timeout_seconds,
            )

            success = http_status == 200 and "choices" in response
            message = (response.get("choices") or [{}])[0].get("message") or {}
            content = message.get("content") or ""
            reasoning = message.get("reasoning_content") or ""
            usage = response.get("usage") or {}
            timings = response.get("timings") or {}

            parse_ok = False
            json_error = ""
            files_written: list[str] = []
            validation_results: list[dict[str, Any]] = []
            summary_text = ""

            if success:
                try:
                    parsed = extract_json_payload(content)
                    parse_ok = True
                    summary_text = parsed.get("summary") or ""
                    files_written = apply_generated_files(workspace_dir, parsed.get("files") or [])
                    validation_results = run_validations(task, workspace_dir)
                except Exception as exc:
                    json_error = repr(exc)

            response_file = output_dir / "responses" / f"{task.task_id}.repeat-{repeat_index}.json"
            save_json(
                response_file,
                {
                    "task_id": task.task_id,
                    "repeat_index": repeat_index,
                    "http_status": http_status,
                    "elapsed_ms": elapsed_ms,
                    "response": response,
                    "validation_results": validation_results,
                    "files_written": files_written,
                    "json_error": json_error,
                },
            )

            validation_success = all(item["success"] for item in validation_results) if validation_results else False
            rows.append(
                {
                    "timestamp_utc": utc_now(),
                    "task_id": task.task_id,
                    "description": task.description,
                    "repeat_index": repeat_index,
                    "http_status": http_status,
                    "request_success": success,
                    "json_parse_success": parse_ok,
                    "validation_success": validation_success,
                    "files_written_count": len(files_written),
                    "files_written": json.dumps(files_written, ensure_ascii=False),
                    "summary_preview": summary_text[:300].replace("\n", "\\n"),
                    "content_length": len(content),
                    "reasoning_content_length": len(reasoning),
                    "elapsed_ms": round(elapsed_ms, 3),
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                    "prompt_ms": timings.get("prompt_ms"),
                    "predicted_ms": timings.get("predicted_ms"),
                    "predicted_per_second": timings.get("predicted_per_second"),
                    "error_message": json_error or (
                        (response.get("error") or {}).get("message")
                        if isinstance(response.get("error"), dict)
                        else response.get("raw_error") or response.get("exception") or ""
                    ),
                }
            )
            response_records.append(
                {
                    "task_id": task.task_id,
                    "repeat_index": repeat_index,
                    "request_file": str(request_file),
                    "response_file": str(response_file),
                    "http_status": http_status,
                    "request_success": success,
                    "json_parse_success": parse_ok,
                    "validation_success": validation_success,
                }
            )
            print(
                f"[{args.model_key}] task={task.task_id} repeat={repeat_index} http={http_status} "
                f"request_ok={success} parse_ok={parse_ok} validate_ok={validation_success}"
            )
            sys.stdout.flush()

    csv_path = output_dir / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    save_json(output_dir / "results.json", rows)
    save_json(output_dir / "responses.json", response_records)
    save_json(output_dir / "task_manifest.json", [task.to_manifest_dict() for task in tasks])
    save_json(
        output_dir / "meta.json",
        {
            "generated_at_utc": utc_now(),
            "base_url": args.base_url,
            "model": args.model,
            "model_key": args.model_key,
            "instruction_role": args.instruction_role,
            "workspace_root": str(workspace_root),
            "repeat": args.repeat,
            "selected_task_ids": [task.task_id for task in tasks],
        },
    )

    print(f"Wrote CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
