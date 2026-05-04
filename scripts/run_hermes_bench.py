#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_bench_tasks import HermesBenchTask, get_tasks, write_workspace


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_models(local_base_url: str) -> dict[str, Any]:
    import urllib.request

    with urllib.request.urlopen(f"{local_base_url.rstrip('/')}/models", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def strip_ansi(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
    text = text.replace("\r", "\n")
    return text


def ensure_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def extract_session_id(stdout: str) -> str:
    match = re.search(r"session_id:\s*([0-9_]+[a-z0-9]*)", stdout, re.IGNORECASE)
    return match.group(1) if match else ""


def extract_final_output(stdout: str) -> str:
    cleaned = strip_ansi(stdout)
    lines = [line.rstrip() for line in cleaned.splitlines()]
    keep: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("session_id:"):
            continue
        if stripped.startswith("WARNING:"):
            continue
        if stripped.startswith("To increase the performance of the tunnel"):
            continue
        if "♪(´ε` )" in stripped:
            continue
        if stripped.startswith("┊ 💻 $"):
            continue
        if stripped.startswith("💻 $"):
            continue
        keep.append(stripped)
    return "\n".join(keep).strip()


def read_session_file(session_root: Path, session_id: str) -> dict[str, Any] | None:
    if not session_id:
        return None
    path = session_root / f"session_{session_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def copy_session_file(session_root: Path, session_id: str, target: Path) -> None:
    if not session_id:
        return
    src = session_root / f"session_{session_id}.json"
    if src.exists():
        shutil.copy2(src, target)


def build_command(task: HermesBenchTask, hermes_cmd: str, query: str) -> list[str]:
    cmd = [hermes_cmd, "chat", "-q", query, "-Q"]
    if task.family in {"repo_readonly", "terminal", "sandbox"}:
        cmd.append("--yolo")
    return cmd


def json_loads_safe(text: str) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def validate_contract(task: HermesBenchTask, final_output: str) -> tuple[bool, dict[str, Any]]:
    kind = task.output_contract.kind
    spec = task.output_contract.spec
    details: dict[str, Any] = {"kind": kind}

    if kind == "exact_text":
        ok = final_output.strip() == spec["text"]
        details["expected"] = spec["text"]
        return ok, details

    if kind == "line_prefixes":
        lines = [line.strip() for line in final_output.splitlines() if line.strip()]
        required_prefixes = spec.get("required_prefixes")
        if required_prefixes:
            ok = len(lines) == spec.get("exact_count", len(required_prefixes)) and all(
                line.startswith(prefix) for line, prefix in zip(lines, required_prefixes)
            )
            details["lines"] = lines
            return ok, details
        expected_lines = spec.get("lines", [])
        ok = lines == expected_lines
        details["lines"] = lines
        return ok, details

    if kind == "bullet_count":
        lines = [line.strip() for line in final_output.splitlines() if line.strip()]
        bullet_lines = [line for line in lines if line.startswith("-")]
        details["bullet_lines"] = bullet_lines
        return len(bullet_lines) == spec["count"], details

    if kind == "sections":
        lines = [line.strip() for line in final_output.splitlines() if line.strip()]
        prefixes = spec["required_prefixes"]
        ok = all(any(line.startswith(prefix) for line in lines) for prefix in prefixes)
        details["lines"] = lines
        return ok, details

    if kind == "json_keys":
        parsed = json_loads_safe(final_output)
        details["parsed"] = parsed
        if not isinstance(parsed, dict):
            return False, details
        required = spec.get("required_keys", [])
        if any(key not in parsed for key in required):
            return False, details
        for key, expected in spec.get("exact_values", {}).items():
            if parsed.get(key) != expected:
                return False, details
        return True, details

    if kind == "json_array_length":
        parsed = json_loads_safe(final_output)
        details["parsed"] = parsed
        if not isinstance(parsed, dict):
            return False, details
        root_key = spec["root_key"]
        value = parsed.get(root_key)
        return isinstance(value, list) and len(value) == spec["length"], details

    raise ValueError(f"Unknown contract kind: {kind}")


def keyword_hits(task: HermesBenchTask, final_output: str) -> list[str]:
    lowered = final_output.lower()
    hits = []
    for snippet in task.expected_snippets:
        if snippet.lower() in lowered:
            hits.append(snippet)
    return hits


def file_hashes(root: Path) -> dict[str, str]:
    import hashlib

    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(root))
            hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def changed_files(before: dict[str, str], after: dict[str, str]) -> list[str]:
    keys = set(before) | set(after)
    return sorted(key for key in keys if before.get(key) != after.get(key))


def run_validation_commands(task: HermesBenchTask, cwd: Path) -> list[dict[str, Any]]:
    results = []
    for command in task.validation_commands:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        results.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "success": completed.returncode == 0,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
    return results


def start_sampler(command: str, output_path: Path) -> subprocess.Popen[str]:
    handle = output_path.open("w", encoding="utf-8")
    return subprocess.Popen(
        command,
        shell=True,
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )


def stop_sampler(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()


def task_query(task: HermesBenchTask) -> str:
    return task.prompt


def make_service_health(local_base_url: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"timestamp_utc": utc_now()}
    try:
        payload["models"] = load_models(local_base_url)
    except Exception as exc:
        payload["models_error"] = repr(exc)
    completed = subprocess.run(
        ["systemctl", "is-active", "openclaw-executor.service"],
        capture_output=True,
        text=True,
    )
    payload["service_state"] = completed.stdout.strip() or completed.stderr.strip()
    return payload


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--hermes-cmd", default="hermes")
    parser.add_argument("--local-base-url", default="http://127.0.0.1:18343/v1")
    parser.add_argument("--session-root", default=str(Path.home() / ".hermes" / "sessions"))
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--family", action="append", default=[])
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_root = Path(args.output_root).resolve()
    raw_dir = output_root / "raw"
    requests_dir = raw_dir / "requests"
    outputs_dir = raw_dir / "outputs"
    sessions_dir = raw_dir / "sessions"
    sandboxes_dir = raw_dir / "sandboxes"
    metrics_dir = output_root / "metrics"
    summary_dir = output_root / "summary"
    for path in [raw_dir, requests_dir, outputs_dir, sessions_dir, sandboxes_dir, metrics_dir, summary_dir]:
        ensure_dir(path)

    tasks = get_tasks()
    if args.task_id:
        allowed = set(args.task_id)
        tasks = [task for task in tasks if task.task_id in allowed]
    if args.family:
        allowed = set(args.family)
        tasks = [task for task in tasks if task.family in allowed]
    if not tasks:
        raise SystemExit("No tasks selected")

    gpu_proc = start_sampler(
        "nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw --format=csv -l 1",
        metrics_dir / "gpu_samples.csv",
    )
    vm_proc = start_sampler("vmstat 1", metrics_dir / "vmstat.log")

    try:
        save_json(metrics_dir / "service_health_pre.json", make_service_health(args.local_base_url))

        results_csv = summary_dir / "results.csv"
        results_json = summary_dir / "results.json"
        responses_json = raw_dir / "responses.json"
        rows: list[dict[str, Any]] = read_rows(results_csv) if args.append else []
        responses: list[dict[str, Any]] = load_json(responses_json) if args.append and responses_json.exists() else []
        completed_task_ids = {row["task_id"] for row in rows}
        task_manifest = [task.to_manifest_dict() for task in tasks]
        save_json(summary_dir / "task_manifest.json", task_manifest)

        session_root = Path(args.session_root)

        for task in tasks:
            if task.task_id in completed_task_ids:
                print(f"[hermes-bench] skip task={task.task_id} reason=already_recorded")
                continue
            if task.working_dir_kind == "repo":
                task_cwd = repo_root
            elif task.working_dir_kind == "hermes":
                task_cwd = Path.home() / "hermes-agent"
            else:
                task_cwd = sandboxes_dir / task.task_id
                if task_cwd.exists():
                    shutil.rmtree(task_cwd)
                write_workspace(task_cwd, task.workspace_files)

            request_payload = {
                "task_id": task.task_id,
                "family": task.family,
                "cwd": str(task_cwd),
                "query": task_query(task),
                "readonly": task.readonly,
                "sandbox_write": task.sandbox_write,
            }
            save_json(requests_dir / f"{task.task_id}.json", request_payload)

            before_hashes = file_hashes(task_cwd) if task.working_dir_kind in {"sandbox", "fixture", "repo"} else {}

            cmd = build_command(task, args.hermes_cmd, request_payload["query"])
            started = time.perf_counter()
            try:
                completed = subprocess.run(
                    cmd,
                    cwd=task_cwd,
                    capture_output=True,
                    text=True,
                    timeout=task.max_seconds,
                    env={**os.environ, "PATH": f"{Path.home() / '.local' / 'bin'}:{os.environ.get('PATH', '')}"},
                )
                raw_stdout = ensure_text(completed.stdout)
                raw_stderr = ensure_text(completed.stderr)
                exit_code = completed.returncode
            except subprocess.TimeoutExpired as exc:
                raw_stdout = ensure_text(exc.stdout)
                raw_stderr = ensure_text(exc.stderr) + f"\nTIMEOUT after {task.max_seconds}s"
                exit_code = 124
            elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
            session_id = extract_session_id(raw_stdout)
            final_output = extract_final_output(raw_stdout)
            terminal_tool_used = ("💻" in raw_stdout) or ("pwd" in raw_stdout and "┊" in raw_stdout)
            contract_ok, contract_details = validate_contract(task, final_output)
            parsed_json = json_loads_safe(final_output)
            json_parse_success = isinstance(parsed_json, (dict, list))

            after_hashes = file_hashes(task_cwd) if task.working_dir_kind in {"sandbox", "fixture", "repo"} else {}
            changed = changed_files(before_hashes, after_hashes)
            validation_results = run_validation_commands(task, task_cwd) if task.validation_commands else []
            validation_success = all(item["success"] for item in validation_results) if validation_results else (not task.sandbox_write)
            readonly_ok = (not task.readonly) or len(changed) == 0

            stdout_path = outputs_dir / f"{task.task_id}.stdout.txt"
            stderr_path = outputs_dir / f"{task.task_id}.stderr.txt"
            stdout_path.write_text(raw_stdout, encoding="utf-8")
            stderr_path.write_text(raw_stderr, encoding="utf-8")
            copy_session_file(session_root, session_id, sessions_dir / f"{task.task_id}.session.json")

            response_record = {
                    "task_id": task.task_id,
                    "family": task.family,
                "description": task.description,
                "readonly": task.readonly,
                "sandbox_write": task.sandbox_write,
                "cwd": str(task_cwd),
                "session_id": session_id,
                "stdout_file": str(stdout_path),
                "stderr_file": str(stderr_path),
                "session_file": str(sessions_dir / f"{task.task_id}.session.json"),
                "final_output": final_output,
                "contract_details": contract_details,
                "keyword_hits": keyword_hits(task, final_output),
                "changed_files": changed,
                "validation_results": validation_results,
            }
            save_json(outputs_dir / f"{task.task_id}.json", response_record)
            responses.append(response_record)

            rows.append(
                {
                    "timestamp_utc": utc_now(),
                    "task_id": task.task_id,
                    "task_family": task.family,
                    "description": task.description,
                    "readonly": task.readonly,
                    "sandbox_write": task.sandbox_write,
                    "http_model_path": args.local_base_url,
                    "hermes_exit_code": exit_code,
                    "elapsed_ms": elapsed_ms,
                    "stdout_length": len(raw_stdout),
                    "stderr_length": len(raw_stderr),
                    "session_id": session_id,
                    "terminal_tool_used": terminal_tool_used,
                    "json_parse_success": json_parse_success,
                    "validation_success": validation_success,
                    "output_contract_success": contract_ok,
                    "readonly_preserved": readonly_ok,
                    "changed_files_count": len(changed),
                    "changed_files": json.dumps(changed, ensure_ascii=False),
                    "keyword_hit_count": len(keyword_hits(task, final_output)),
                    "keyword_hits": json.dumps(keyword_hits(task, final_output), ensure_ascii=False),
                    "error_message": "" if exit_code == 0 else (raw_stderr or raw_stdout)[-800:],
                    "output_preview": final_output[:500].replace("\n", "\\n"),
                }
            )
            write_rows(results_csv, rows)
            save_json(results_json, rows)
            save_json(responses_json, responses)
            print(
                f"[hermes-bench] task={task.task_id} family={task.family} exit={exit_code} "
                f"contract_ok={contract_ok} validation_ok={validation_success} readonly_ok={readonly_ok}"
            )

        write_rows(results_csv, rows)
        save_json(results_json, rows)
        save_json(responses_json, responses)
        save_json(metrics_dir / "service_health_post.json", make_service_health(args.local_base_url))
        print(f"Wrote benchmark output to {output_root}")
        return 0
    finally:
        stop_sampler(gpu_proc)
        stop_sampler(vm_proc)


if __name__ == "__main__":
    raise SystemExit(main())
