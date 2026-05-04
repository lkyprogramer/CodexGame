#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nemotron_thinking_specialized_tasks import SpecializedTask, get_specialized_tasks


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


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def select_tasks(tasks: list[SpecializedTask], task_ids: set[str], families: set[str]) -> list[SpecializedTask]:
    selected: list[SpecializedTask] = []
    for task in tasks:
        if task_ids and task.task_id not in task_ids:
            continue
        if families and task.family not in families:
            continue
        selected.append(task)
    return selected


def build_round_user_message(task: SpecializedTask, round_index: int, repo_root: Path) -> str:
    total_rounds = len(task.round_prompts)
    header = [
        f"Task ID: {task.task_id}",
        f"Scenario: {task.description}",
        f"Round: {round_index} / {total_rounds}",
        "",
        "Instructions:",
        task.round_prompts[round_index - 1].strip(),
        "",
        "Project snapshot:",
        task.render_context(repo_root).rstrip(),
    ]
    return "\n".join(header).strip() + "\n"


def append_assistant_message(messages: list[dict[str, str]], response: dict[str, Any]) -> tuple[str, str]:
    choices = response.get("choices") or []
    message = (choices[0] if choices else {}).get("message") or {}
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""
    messages.append({"role": "assistant", "content": content})
    return content, reasoning


def extract_error(response: dict[str, Any]) -> str:
    error = response.get("error")
    if isinstance(error, dict):
        return error.get("message") or json.dumps(error, ensure_ascii=False)
    return response.get("raw_error") or response.get("exception") or json.dumps(response, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", default="sk-no-key-required")
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-key", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--timeout-seconds", type=int, default=2400)
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--family", action="append", default=[])
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    ensure_dir(output_dir)
    ensure_dir(output_dir / "requests")
    ensure_dir(output_dir / "responses")

    tasks = select_tasks(get_specialized_tasks(), set(args.task_id), set(args.family))
    if not tasks:
        raise SystemExit("No tasks selected")

    rows: list[dict[str, Any]] = []
    response_records: list[dict[str, Any]] = []

    for task in tasks:
        messages: list[dict[str, str]] = [{"role": "system", "content": task.system_message}]
        rounds_payloads: list[dict[str, Any]] = []
        rounds_responses: list[dict[str, Any]] = []
        total_elapsed_ms = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        total_prompt_ms = 0.0
        total_predicted_ms = 0.0
        total_reasoning_len = 0
        final_content = ""
        final_reasoning = ""
        success = True
        final_http_status = 200
        error_message = ""

        for round_index in range(1, len(task.round_prompts) + 1):
            user_message = build_round_user_message(task, round_index, repo_root)
            messages.append({"role": "user", "content": user_message})
            payload = {
                "model": args.model,
                "messages": messages,
                "max_tokens": task.max_tokens,
                "stream": False,
            }
            rounds_payloads.append(payload)

            http_status, response, elapsed_ms = send_chat_request(
                args.base_url,
                args.api_key,
                payload,
                args.timeout_seconds,
            )
            total_elapsed_ms += elapsed_ms
            final_http_status = http_status
            rounds_responses.append(
                {
                    "round_index": round_index,
                    "http_status": http_status,
                    "elapsed_ms": elapsed_ms,
                    "response": response,
                }
            )

            if http_status != 200 or "choices" not in response:
                success = False
                error_message = extract_error(response)
                break

            usage = response.get("usage") or {}
            timings = response.get("timings") or {}
            total_prompt_tokens += int(usage.get("prompt_tokens") or 0)
            total_completion_tokens += int(usage.get("completion_tokens") or 0)
            total_tokens += int(usage.get("total_tokens") or 0)
            total_prompt_ms += float(timings.get("prompt_ms") or 0.0)
            total_predicted_ms += float(timings.get("predicted_ms") or 0.0)
            final_content, final_reasoning = append_assistant_message(messages, response)
            total_reasoning_len += len(final_reasoning)

        request_file = output_dir / "requests" / f"{task.task_id}.json"
        response_file = output_dir / "responses" / f"{task.task_id}.json"
        save_json(
            request_file,
            {
                "task_id": task.task_id,
                "model": args.model,
                "rounds": rounds_payloads,
            },
        )
        save_json(
            response_file,
            {
                "task_id": task.task_id,
                "model": args.model,
                "responses": rounds_responses,
                "final_content": final_content,
                "final_reasoning": final_reasoning,
            },
        )

        effective_predicted_per_second = None
        if total_predicted_ms > 0 and total_completion_tokens > 0:
            effective_predicted_per_second = (total_completion_tokens / total_predicted_ms) * 1000.0

        row = {
            "timestamp_utc": utc_now(),
            "task_id": task.task_id,
            "family": task.family,
            "description": task.description,
            "round_count": len(task.round_prompts),
            "http_status": final_http_status,
            "success": success,
            "max_tokens": task.max_tokens,
            "elapsed_ms": round(total_elapsed_ms, 3),
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "prompt_ms": round(total_prompt_ms, 3),
            "predicted_ms": round(total_predicted_ms, 3),
            "predicted_per_second": effective_predicted_per_second,
            "reasoning_content_length": total_reasoning_len,
            "content_length": len(final_content),
            "content_preview": final_content[:400].replace("\n", "\\n"),
            "reasoning_preview": final_reasoning[:400].replace("\n", "\\n"),
            "error_message": error_message,
            "request_file": str(request_file),
            "response_file": str(response_file),
        }
        rows.append(row)
        response_records.append(
            {
                "task_id": task.task_id,
                "request_file": str(request_file),
                "response_file": str(response_file),
            }
        )
        print(
            "[{model_key}] task={task_id} family={family} rounds={rounds} status={status} success={success} total_ms={ms}".format(
                model_key=args.model_key,
                task_id=task.task_id,
                family=task.family,
                rounds=len(task.round_prompts),
                status=final_http_status,
                success=success,
                ms=round(total_elapsed_ms, 3),
            ),
            flush=True,
        )

    csv_path = output_dir / "results.csv"
    json_path = output_dir / "results.json"
    meta_path = output_dir / "meta.json"
    responses_path = output_dir / "responses.json"
    task_manifest_path = output_dir / "task_manifest.json"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    save_json(json_path, rows)
    save_json(responses_path, response_records)
    save_json(meta_path, {"generated_at_utc": utc_now(), "model": args.model, "model_key": args.model_key})
    save_json(task_manifest_path, [task.manifest() for task in tasks])

    print(f"Wrote CSV: {csv_path}")
    print(f"Wrote JSON: {json_path}")
    print(f"Wrote META: {meta_path}")
    print(f"Wrote RESPONSES: {responses_path}")
    print(f"Wrote TASK MANIFEST: {task_manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
