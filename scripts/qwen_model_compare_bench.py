#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from model_compare_tasks import CompareTask, get_tasks


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def is_retriable_transport_status(status: int) -> bool:
    return status in (0, 502, 504)


def get_models(base_url: str, api_key: str, timeout_seconds: int) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/models",
        headers=build_headers(api_key),
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_existing_rows(csv_path: Path) -> list[dict[str, Any]]:
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(csv_path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def extract_result(
    task: CompareTask,
    repeat_index: int,
    http_status: int,
    response: dict[str, Any],
    elapsed_ms: float,
    request_payload: dict[str, Any],
    network_retry_count: int,
) -> dict[str, Any]:
    success = http_status == 200 and "choices" in response
    choice0 = response["choices"][0] if success else {}
    message = choice0.get("message") or {}
    usage = response.get("usage") or {}
    timings = response.get("timings") or {}

    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""

    error_message = ""
    if not success:
        error = response.get("error")
        if isinstance(error, dict):
            error_message = error.get("message") or json.dumps(error, ensure_ascii=False)
        else:
            error_message = (
                response.get("raw_error")
                or response.get("exception")
                or json.dumps(response, ensure_ascii=False)
            )

    return {
        "timestamp_utc": utc_now(),
        "task_id": task.task_id,
        "family": task.family,
        "description": task.description,
        "repeat_index": repeat_index,
        "http_status": http_status,
        "success": success,
        "max_tokens": task.max_tokens,
        "prompt_chars": len(json.dumps(request_payload["messages"], ensure_ascii=False)),
        "context_file_count": len(task.context_files),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "finish_reason": choice0.get("finish_reason") or "",
        "elapsed_ms": round(elapsed_ms, 3),
        "network_retry_count": network_retry_count,
        "prompt_ms": timings.get("prompt_ms"),
        "predicted_ms": timings.get("predicted_ms"),
        "predicted_per_second": timings.get("predicted_per_second"),
        "reasoning_content_length": len(reasoning),
        "content_length": len(content),
        "reasoning_preview": reasoning[:400].replace("\n", "\\n"),
        "content_preview": content[:400].replace("\n", "\\n"),
        "error_message": error_message,
    }


def select_tasks(
    tasks: list[CompareTask],
    task_ids: set[str],
    families: set[str],
) -> list[CompareTask]:
    selected = []
    for task in tasks:
        if task_ids and task.task_id not in task_ids:
            continue
        if families and task.family not in families:
            continue
        selected.append(task)
    return selected


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="Example: http://127.0.0.1:28343/v1")
    parser.add_argument("--api-key", default="sk-no-key-required")
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-key", required=True)
    parser.add_argument(
        "--instruction-role",
        choices=["developer", "system"],
        default="developer",
        help="Role used for the high-priority instruction message.",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--family", action="append", default=[])
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--benchmark-profile", default="64k-coding-v1")
    parser.add_argument("--server-args", default="")
    parser.add_argument("--network-retries", type=int, default=0)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    requests_dir = output_dir / "requests"
    responses_dir = output_dir / "responses"
    ensure_dir(output_dir)
    ensure_dir(requests_dir)
    ensure_dir(responses_dir)

    tasks = select_tasks(get_tasks(), set(args.task_id), set(args.family))
    if not tasks:
        raise SystemExit("No tasks selected")

    csv_path = output_dir / "results.csv"
    json_path = output_dir / "results.json"
    meta_path = output_dir / "meta.json"
    responses_path = output_dir / "responses.json"
    task_manifest_path = output_dir / "task_manifest.json"

    rows: list[dict[str, Any]] = read_existing_rows(csv_path) if args.append else []
    response_records: list[dict[str, Any]] = (
        json.loads(responses_path.read_text(encoding="utf-8")) if args.append and responses_path.exists() else []
    )

    meta = {
        "generated_at_utc": utc_now(),
        "base_url": args.base_url,
        "model": args.model,
        "model_key": args.model_key,
        "instruction_role": args.instruction_role,
        "benchmark_profile": args.benchmark_profile,
        "server_args": args.server_args,
        "timeout_seconds": args.timeout_seconds,
        "repeat": args.repeat,
        "selected_task_ids": [task.task_id for task in tasks],
    }
    try:
        meta["models_response"] = get_models(args.base_url, args.api_key, args.timeout_seconds)
    except Exception as exc:
        meta["models_error"] = repr(exc)

    save_json(task_manifest_path, [task.to_manifest_dict() for task in tasks])

    for task in tasks:
        user_message = task.render_user_message(repo_root)
        payload = {
            "model": args.model,
            "messages": [
                {"role": args.instruction_role, "content": task.developer_message},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": task.max_tokens,
            "stream": False,
        }

        for repeat_index in range(1, args.repeat + 1):
            network_retry_count = 0
            while True:
                status, response, elapsed_ms = send_chat_request(
                    args.base_url,
                    args.api_key,
                    payload,
                    args.timeout_seconds,
                )
                if not is_retriable_transport_status(status) or network_retry_count >= args.network_retries:
                    break
                network_retry_count += 1
                time.sleep(2 * network_retry_count)

            row = extract_result(
                task,
                repeat_index,
                status,
                response,
                elapsed_ms,
                payload,
                network_retry_count,
            )
            rows.append(row)

            request_record = {
                "task_id": task.task_id,
                "repeat_index": repeat_index,
                "payload": payload,
            }
            response_record = {
                "task_id": task.task_id,
                "repeat_index": repeat_index,
                "http_status": status,
                "elapsed_ms": elapsed_ms,
                "response": response,
            }

            request_file = requests_dir / f"{task.task_id}__r{repeat_index}.json"
            response_file = responses_dir / f"{task.task_id}__r{repeat_index}.json"
            save_json(request_file, request_record)
            save_json(response_file, response_record)
            response_records.append({
                "task_id": task.task_id,
                "repeat_index": repeat_index,
                "request_file": str(request_file),
                "response_file": str(response_file),
                "http_status": status,
                "success": row["success"],
            })

            print(
                f"[{args.model_key}] task={task.task_id} repeat={repeat_index} "
                f"status={row['http_status']} success={row['success']} "
                f"prompt_tokens={row['prompt_tokens']} total_ms={row['elapsed_ms']}",
                flush=True,
            )

    write_rows(csv_path, rows)
    save_json(json_path, rows)
    save_json(meta_path, meta)
    save_json(responses_path, response_records)

    print(f"Wrote CSV: {csv_path}")
    print(f"Wrote JSON: {json_path}")
    print(f"Wrote META: {meta_path}")
    print(f"Wrote RESPONSES: {responses_path}")
    print(f"Wrote TASK MANIFEST: {task_manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
