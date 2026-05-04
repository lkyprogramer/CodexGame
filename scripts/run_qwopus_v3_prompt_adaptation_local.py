#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shlex
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic_model_compare_tasks import AgenticTask, get_agentic_tasks


REMOTE_PASSWORD = "hhtele"
BENCH_RUN_SCRIPT = "/opt/llama.cpp/run-openclaw-executor.sh"
BENCH_SERVICE = "openclaw-executor"
LIVE_SERVICE = "qwen35-35b-a3b-uncensored"
QWOPUS_ALIAS = "bench/qwopus35-27b-v3-q4_k_m"
QWOPUS_MODEL_PATH = "/data/models/qwen/Qwopus3.5-27B-v3-Q4_K_M.gguf"

SERVER_ARGS_64K = [
    "-ngl 99",
    "-c 65536",
    "-np 1",
    "-fa on",
    "-ctk q4_0",
    "-ctv q4_0",
    "--temp 0.2",
    "--top-p 0.90",
    "--top-k 20",
    "--min-p 0.0",
    "--reasoning-format none",
    """--chat-template-kwargs '{"enable_thinking": false}'""",
    "--host 0.0.0.0",
    "--port 18343",
]

STRICT_SUFFIX = """
Hard output contract:
- Return exactly one JSON object.
- The first character of the response must be `{`.
- The last character of the response must be `}`.
- Do not include any explanation, chain-of-thought, prose, markdown, or code fences.
- If you cannot complete the task, still return valid JSON with a short summary and an empty files array.
""".strip()

ENVELOPE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "files"],
    "additionalProperties": False,
}

SELECTED_TASK_IDS = [
    "agentic_python_reconcile_pkg",
    "agentic_python_metrics_contract",
    "agentic_bash_log_triage_gz",
    "agentic_ts_metrics_contract_patch",
]


@dataclass(frozen=True)
class Variant:
    key: str
    label: str
    instruction_role: str
    strict_prompt: bool
    response_format: dict[str, Any] | None = None


VARIANTS: tuple[Variant, ...] = (
    Variant(
        key="plain_system",
        label="system + current prompt",
        instruction_role="system",
        strict_prompt=False,
    ),
    Variant(
        key="strict_system",
        label="system + strict JSON wording",
        instruction_role="system",
        strict_prompt=True,
    ),
    Variant(
        key="strict_developer",
        label="developer + strict JSON wording",
        instruction_role="developer",
        strict_prompt=True,
    ),
    Variant(
        key="strict_json_schema_system",
        label="system + strict JSON wording + response_format json_schema",
        instruction_role="system",
        strict_prompt=True,
        response_format={"type": "json_schema", "json_schema": {"schema": ENVELOPE_SCHEMA}},
    ),
    Variant(
        key="strict_json_schema_developer",
        label="developer + strict JSON wording + response_format json_schema",
        instruction_role="developer",
        strict_prompt=True,
        response_format={"type": "json_schema", "json_schema": {"schema": ENVELOPE_SCHEMA}},
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(cmd: list[str], *, capture: bool = True, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(cmd, check=False, text=True, capture_output=capture)
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode,
            cmd,
            output=completed.stdout,
            stderr=completed.stderr,
        )
    return completed


def run_local(command: str, *, capture: bool = True) -> str:
    completed = run_command(["bash", "-lc", command], capture=capture, check=True)
    return completed.stdout if capture else ""


def sudo_local(command: str, *, capture: bool = True) -> str:
    wrapped = "printf '%s\\n' {password} | sudo -S -p '' bash -lc {command}".format(
        password=shlex.quote(REMOTE_PASSWORD),
        command=shlex.quote(command),
    )
    return run_local(wrapped, capture=capture)


def make_run_script(model_path: str, model_alias: str, server_args: list[str]) -> str:
    args = " \\\n  ".join(server_args)
    return f"""#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${{LD_LIBRARY_PATH:-}}
exec /opt/llama.cpp/build/bin/llama-server \\
  -m {shlex.quote(model_path)} \\
  --alias {shlex.quote(model_alias)} \\
  {args}
"""


def install_run_script(script_text: str, backup_path: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(script_text)
    try:
        sudo_local(
            "test -f {backup} || cp {current} {backup}; "
            "cp {temp} {current}; "
            "chmod +x {current}".format(
                backup=shlex.quote(backup_path),
                current=shlex.quote(BENCH_RUN_SCRIPT),
                temp=shlex.quote(str(temp_path)),
            ),
            capture=False,
        )
    finally:
        temp_path.unlink(missing_ok=True)


def restore_bench_run_script(backup_path: str) -> None:
    sudo_local(
        "if test -f {backup}; then cp {backup} {current}; chmod +x {current}; fi".format(
            backup=shlex.quote(backup_path),
            current=shlex.quote(BENCH_RUN_SCRIPT),
        ),
        capture=False,
    )


def wait_for_model(base_url: str, api_key: str, expected_alias: str, timeout_seconds: int) -> None:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{base_url.rstrip('/')}/models", headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            aliases = [item.get("id") for item in payload.get("data", [])]
            if expected_alias in aliases:
                return
        except Exception:
            pass
        time.sleep(3)
    raise TimeoutError(f"Timed out waiting for {expected_alias}")


def restart_bench_service(base_url: str, api_key: str, timeout_seconds: int) -> None:
    sudo_local(f"systemctl reset-failed {BENCH_SERVICE} || true", capture=False)
    sudo_local(f"systemctl restart {BENCH_SERVICE}", capture=False)
    wait_for_model(base_url, api_key, QWOPUS_ALIAS, timeout_seconds)


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
    return json.loads(text.strip())


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


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_system_message(task: AgenticTask, strict_prompt: bool) -> str:
    if not strict_prompt:
        return task.system_message
    return f"{task.system_message}\n\n{STRICT_SUFFIX}"


def select_tasks() -> list[AgenticTask]:
    wanted = set(SELECTED_TASK_IDS)
    tasks = [task for task in get_agentic_tasks() if task.task_id in wanted]
    if len(tasks) != len(wanted):
        missing = sorted(wanted - {task.task_id for task in tasks})
        raise RuntimeError(f"Missing task definitions: {missing}")
    return tasks


@contextmanager
def capture_experiment_artifacts(output_root: Path):
    gpu_log = output_root / "gpu_samples.csv"
    vmstat_log = output_root / "vmstat.log"
    gpu_proc = subprocess.Popen(
        ["bash", "-lc", f"nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw --format=csv -l 1 > {shlex.quote(str(gpu_log))}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    vmstat_proc = subprocess.Popen(
        ["bash", "-lc", f"vmstat 1 > {shlex.quote(str(vmstat_log))}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        yield
    finally:
        for proc in (gpu_proc, vmstat_proc):
            proc.terminate()


def summarize_variant(rows: list[dict[str, Any]]) -> dict[str, Any]:
    task_count = len({row["task_id"] for row in rows})
    return {
        "task_count": task_count,
        "request_success": sum(bool(row["request_success"]) for row in rows),
        "json_parse_success": sum(bool(row["json_parse_success"]) for row in rows),
        "validation_success": sum(bool(row["validation_success"]) for row in rows),
        "avg_elapsed_ms": sum(float(row["elapsed_ms"]) for row in rows) / len(rows) if rows else None,
        "avg_completion_tokens": sum(float(row.get("completion_tokens") or 0) for row in rows) / len(rows) if rows else None,
        "avg_content_length": sum(float(row.get("content_length") or 0) for row in rows) / len(rows) if rows else None,
        "sample_error": next((row["error_message"] for row in rows if row["error_message"]), ""),
        "sample_preview": next((row["content_preview"] for row in rows if row["content_preview"]), ""),
    }


def build_report(rows: list[dict[str, Any]], output_root: Path) -> tuple[dict[str, Any], str]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["variant_key"]].append(row)

    variants = {variant.key: summarize_variant(grouped[variant.key]) for variant in VARIANTS}
    best_variant_key = max(
        variants,
        key=lambda key: (
            variants[key]["validation_success"],
            variants[key]["json_parse_success"],
            variants[key]["request_success"],
        ),
    )
    payload = {
        "generated_at_utc": utc_now(),
        "model_alias": QWOPUS_ALIAS,
        "model_path": QWOPUS_MODEL_PATH,
        "selected_task_ids": SELECTED_TASK_IDS,
        "variants": variants,
        "best_variant_key": best_variant_key,
        "raw_rows": rows,
    }

    lines = [
        "# Qwopus v3 Prompt / 模板适配实验",
        "",
        f"- Generated at (UTC): `{payload['generated_at_utc']}`",
        f"- Model: `{QWOPUS_ALIAS}`",
        f"- Tasks: `{', '.join(SELECTED_TASK_IDS)}`",
        "",
        "## 结果总表",
        "",
        "| Variant | request_ok | json_parse_ok | validation_ok | avg elapsed_ms | avg completion_tokens | avg content_length |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant in VARIANTS:
        item = variants[variant.key]
        lines.append(
            "| {label} | {req}/{total} | {parse}/{total} | {valid}/{total} | {elapsed:.2f} | {tokens:.2f} | {content:.2f} |".format(
                label=variant.label,
                req=item["request_success"],
                parse=item["json_parse_success"],
                valid=item["validation_success"],
                total=item["task_count"],
                elapsed=item["avg_elapsed_ms"] or 0.0,
                tokens=item["avg_completion_tokens"] or 0.0,
                content=item["avg_content_length"] or 0.0,
            )
        )

    best = variants[best_variant_key]
    lines.extend(
        [
            "",
            "## 结论",
            "",
            f"- 最优变体：`{best_variant_key}`",
            f"- 该变体 `json_parse_success = {best['json_parse_success']} / {best['task_count']}`",
            f"- 该变体 `validation_success = {best['validation_success']} / {best['task_count']}`",
        ]
    )
    if best["json_parse_success"] == 0:
        lines.append("- 结论：仅靠 prompt / role / response_format 适配，仍无法把 Qwopus v3 拉进当前 JSON executor 契约。")
    elif best["validation_success"] == 0:
        lines.append("- 结论：可以改善 JSON 外壳，但还不足以通过实际 workspace 验证。")
    else:
        lines.append("- 结论：已经可以部分适配当前 executor 契约，后续应围绕最优变体继续做更大样本验证。")

    lines.extend(
        [
            "",
            "## 失败样本",
            "",
        ]
    )
    for variant in VARIANTS:
        item = variants[variant.key]
        preview = (item["sample_preview"] or "").replace("\n", "\\n")
        if len(preview) > 400:
            preview = preview[:400] + "..."
        lines.append(f"- `{variant.key}`: {preview or item['sample_error'] or '-'}")

    report = "\n".join(lines) + "\n"
    return payload, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18343/v1")
    parser.add_argument("--api-key", default="sk-no-key-required")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--wait-timeout-seconds", type=int, default=420)
    parser.add_argument("--timeout-seconds", type=int, default=2400)
    args = parser.parse_args()

    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    summary_dir = output_root / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    tasks = select_tasks()
    bench_backup_path = f"{BENCH_RUN_SCRIPT}.bench-{output_root.name}.bak"
    rows: list[dict[str, Any]] = []

    save_json(
        summary_dir / "download_meta.json",
        {
            "target": QWOPUS_MODEL_PATH,
            "size_bytes": Path(QWOPUS_MODEL_PATH).stat().st_size,
            "sha256": file_sha256(Path(QWOPUS_MODEL_PATH)),
        },
    )

    try:
        sudo_local(f"systemctl stop {LIVE_SERVICE}", capture=False)
        sudo_local(f"systemctl stop {BENCH_SERVICE}", capture=False)
        sudo_local(f"systemctl reset-failed {BENCH_SERVICE} || true", capture=False)
        install_run_script(make_run_script(QWOPUS_MODEL_PATH, QWOPUS_ALIAS, SERVER_ARGS_64K), bench_backup_path)

        with capture_experiment_artifacts(output_root):
            for variant in VARIANTS:
                variant_dir = raw_dir / variant.key
                (variant_dir / "requests").mkdir(parents=True, exist_ok=True)
                (variant_dir / "responses").mkdir(parents=True, exist_ok=True)

                for task in tasks:
                    restart_bench_service(args.base_url, args.api_key, args.wait_timeout_seconds)
                    workspace_dir = output_root / "workspaces" / variant.key / task.task_id
                    materialize_workspace(task, workspace_dir)
                    payload: dict[str, Any] = {
                        "model": QWOPUS_ALIAS,
                        "messages": [
                            {"role": variant.instruction_role, "content": build_system_message(task, variant.strict_prompt)},
                            {"role": "user", "content": task.render_user_message()},
                        ],
                        "max_tokens": task.max_tokens,
                        "stream": False,
                    }
                    if variant.response_format is not None:
                        payload["response_format"] = variant.response_format

                    save_json(variant_dir / "requests" / f"{task.task_id}.json", payload)
                    http_status, response, elapsed_ms = send_chat_request(
                        args.base_url,
                        args.api_key,
                        payload,
                        args.timeout_seconds,
                    )

                    success = http_status == 200 and "choices" in response
                    message = (response.get("choices") or [{}])[0].get("message") or {}
                    content = message.get("content") or ""
                    usage = response.get("usage") or {}

                    parse_ok = False
                    validation_success = False
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
                            validation_success = bool(validation_results) and all(item["success"] for item in validation_results)
                        except Exception as exc:
                            json_error = repr(exc)

                    save_json(
                        variant_dir / "responses" / f"{task.task_id}.json",
                        {
                            "variant": variant.key,
                            "task_id": task.task_id,
                            "http_status": http_status,
                            "elapsed_ms": elapsed_ms,
                            "response": response,
                            "json_error": json_error,
                            "files_written": files_written,
                            "validation_results": validation_results,
                        },
                    )

                    row = {
                        "timestamp_utc": utc_now(),
                        "variant_key": variant.key,
                        "variant_label": variant.label,
                        "instruction_role": variant.instruction_role,
                        "strict_prompt": variant.strict_prompt,
                        "response_format_kind": variant.response_format["type"] if variant.response_format else "",
                        "task_id": task.task_id,
                        "http_status": http_status,
                        "request_success": success,
                        "json_parse_success": parse_ok,
                        "validation_success": validation_success,
                        "files_written_count": len(files_written),
                        "content_length": len(content),
                        "elapsed_ms": round(elapsed_ms, 3),
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                        "predicted_per_second": (response.get("timings") or {}).get("predicted_per_second"),
                        "summary_preview": summary_text[:240].replace("\n", "\\n"),
                        "content_preview": content[:500].replace("\n", "\\n"),
                        "error_message": json_error or (
                            (response.get("error") or {}).get("message")
                            if isinstance(response.get("error"), dict)
                            else response.get("raw_error") or response.get("exception") or ""
                        ),
                    }
                    rows.append(row)
                    print(
                        f"[{variant.key}] task={task.task_id} http={http_status} "
                        f"request_ok={success} parse_ok={parse_ok} validate_ok={validation_success}"
                    )

        csv_path = raw_dir / "results.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        save_json(raw_dir / "results.json", rows)

        payload, report = build_report(rows, output_root)
        save_json(summary_dir / "experiment_report.json", payload)
        (summary_dir / "experiment_report.md").write_text(report, encoding="utf-8")
    finally:
        restore_bench_run_script(bench_backup_path)
        sudo_local(f"systemctl stop {BENCH_SERVICE}", capture=False)
        sudo_local(f"systemctl start {LIVE_SERVICE}", capture=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
