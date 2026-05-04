#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_guardrail_lib import (
    RecoveredOutput,
    ensure_text,
    extract_session_id,
    is_retryable_cli_error,
    load_json,
    recover_final_output,
    save_json,
    sha256_text,
)


DEFAULT_CONFIG = {
    "hermes_cmd": "hermes",
    "session_root": "~/.hermes/sessions",
    "run_root": "~/.hermes-safe/runs",
    "max_retries": 1,
    "default_timeout_seconds": 300,
}

READONLY_IGNORE_SUBSTRINGS = (
    "__pycache__/",
    ".pytest_cache/",
    ".pyc",
    "CACHEDIR.TAG",
    ".DS_Store",
)


@dataclass(frozen=True)
class AttemptResult:
    attempt: int
    query: str
    exit_code: int
    timed_out: bool
    elapsed_ms: float
    stdout_text: str
    stderr_text: str
    session_id: str
    session_source: str
    session_path: Path | None
    recovered: RecoveredOutput


@dataclass(frozen=True)
class Evaluation:
    success: bool
    soft_success: bool
    contract_success: bool
    json_parse_success: bool
    failure_reason: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_or_init_config(config_root: Path) -> dict[str, Any]:
    ensure_dir(config_root)
    config_path = config_root / "config.json"
    if not config_path.exists():
        save_json(config_path, DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    config = load_json(config_path)
    payload = dict(DEFAULT_CONFIG)
    payload.update(config if isinstance(config, dict) else {})
    save_json(config_path, payload)
    return payload


def expand_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def safe_symlink_latest(config_root: Path, run_dir: Path) -> None:
    latest = config_root / "latest"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(run_dir, target_is_directory=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("--mode", choices=["text", "json", "readonly", "sandbox"], default="text")
    run.add_argument("--cwd", default=os.getcwd())
    run.add_argument("--query")
    run.add_argument("--query-file")
    run.add_argument("--timeout", type=int)
    run.add_argument("--validation-cmd", action="append", default=[])
    run.add_argument("--workspace")
    run.add_argument("--output")
    run.add_argument("--config-root", default="~/.hermes-safe")
    return parser.parse_args()


def load_query(args: argparse.Namespace) -> str:
    if bool(args.query) == bool(args.query_file):
        raise SystemExit("Use exactly one of --query or --query-file")
    if args.query_file:
        return Path(args.query_file).read_text(encoding="utf-8").strip()
    return str(args.query).strip()


def augment_query(mode: str, query: str, retry: bool) -> str:
    parts: list[str] = []
    if mode == "readonly":
        parts.append("Use terminal tools to inspect first. Do not modify files in the current repository.")
        parts.append("Return only the final answer. Do not include tool traces or markdown fences unless the query explicitly asks for markdown.")
    elif mode == "sandbox":
        parts.append(
            "You may use terminal tools and modify files only inside the current working directory. "
            "Do not read, modify, or reference files outside the current working directory."
        )
        parts.append("When finished, briefly summarize what you changed and why. Do not include markdown fences.")
    elif mode == "json":
        parts.append("Return strict JSON only. Do not include markdown fences or explanation.")

    if retry:
        parts.append("Previous attempt did not produce a consumable final answer. Return only the final answer now.")
        if mode == "json":
            parts.append("The final answer must be valid JSON with no markdown wrapper.")

    if not parts:
        return query
    return "\n\n".join(parts + [query]).strip()


def build_command(hermes_cmd: str, mode: str, query: str) -> list[str]:
    cmd = [hermes_cmd, "chat", "-q", query, "-Q"]
    if mode in {"readonly", "sandbox"}:
        cmd.append("--yolo")
    return cmd


def snapshot_session_root(session_root: Path) -> dict[str, int]:
    if not session_root.exists():
        return {}
    return {path.name: path.stat().st_mtime_ns for path in session_root.glob("session_*.json")}


def resolve_session_file(
    session_root: Path,
    before: dict[str, int],
    stdout_text: str,
    stderr_text: str,
    started_ns: int,
) -> tuple[str, str, Path | None]:
    session_id = extract_session_id(stdout_text, stderr_text)
    if session_id:
        explicit = session_root / f"session_{session_id}.json"
        if explicit.exists():
            return session_id, "stdout", explicit

    if not session_root.exists():
        return session_id, "missing", None

    candidates: list[tuple[int, Path]] = []
    lower_bound = started_ns - 5_000_000_000
    for path in session_root.glob("session_*.json"):
        mtime = path.stat().st_mtime_ns
        if before.get(path.name) == mtime:
            continue
        if mtime >= lower_bound:
            candidates.append((mtime, path))

    if not candidates:
        return session_id, "missing", None

    candidates.sort(key=lambda item: item[0], reverse=True)
    chosen = candidates[0][1]
    inferred_id = chosen.stem.removeprefix("session_")
    return inferred_id, "inferred", chosen


def git_status_lines(cwd: Path) -> list[str] | None:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return [line.rstrip() for line in completed.stdout.splitlines() if line.strip()]


def filter_status_lines(lines: list[str] | None) -> list[str]:
    if not lines:
        return []
    filtered: list[str] = []
    for line in lines:
        if any(token in line for token in READONLY_IGNORE_SUBSTRINGS):
            continue
        filtered.append(line)
    return filtered


def readonly_violation(before: list[str] | None, after: list[str] | None) -> tuple[bool, list[str]]:
    before_filtered = set(filter_status_lines(before))
    after_filtered = set(filter_status_lines(after))
    delta = sorted(after_filtered - before_filtered)
    return len(delta) > 0, delta


def run_validation_commands(commands: list[str], cwd: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in commands:
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


def file_hashes(root: Path) -> dict[str, str]:
    import hashlib

    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(root))
            hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def filter_changed_files(paths: list[str]) -> list[str]:
    filtered: list[str] = []
    for item in paths:
        if any(token in item for token in READONLY_IGNORE_SUBSTRINGS):
            continue
        filtered.append(item)
    return filtered


def diff_changed_files(before: dict[str, str], after: dict[str, str]) -> list[str]:
    keys = set(before) | set(after)
    changed = sorted(key for key in keys if before.get(key) != after.get(key))
    return filter_changed_files(changed)


def prepare_sandbox_workspace(run_dir: Path, workspace_arg: str | None) -> Path:
    workspace = run_dir / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    if workspace_arg:
        source = Path(workspace_arg).expanduser().resolve()
        if source.exists() and source.is_dir():
            shutil.copytree(source, workspace)
            return workspace
    ensure_dir(workspace)
    return workspace


def serialize_sandbox_output(summary: str, changed_files: list[str], validation_results: list[dict[str, Any]]) -> str:
    payload = {
        "status": "ok" if all(item["success"] for item in validation_results) else "error",
        "summary": summary.strip(),
        "changed_files": changed_files,
        "validation_success": all(item["success"] for item in validation_results),
        "validation_commands": [
            {
                "command": item["command"],
                "success": item["success"],
                "returncode": item["returncode"],
            }
            for item in validation_results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def evaluate_attempt(
    mode: str,
    attempt: AttemptResult,
    final_output: str,
    json_parse_success: bool,
    validation_success: bool,
    readonly_ok: bool,
) -> Evaluation:
    contract_success = True
    if mode in {"text", "readonly"}:
        contract_success = bool(final_output.strip())
    elif mode == "json":
        contract_success = json_parse_success
    elif mode == "sandbox":
        contract_success = bool(final_output.strip())

    if attempt.timed_out:
        return Evaluation(False, False, contract_success, json_parse_success, "timeout")
    if not readonly_ok:
        return Evaluation(False, False, contract_success, json_parse_success, "readonly_violation")
    if mode == "sandbox" and not validation_success:
        return Evaluation(False, False, contract_success, json_parse_success, "validation_failure")
    if mode == "json" and not json_parse_success:
        return Evaluation(False, False, contract_success, False, "json_parse_failure")
    if not contract_success:
        return Evaluation(False, False, False, json_parse_success, "contract_failure")
    if attempt.exit_code != 0:
        if attempt.session_path and attempt.recovered.output_source == "session":
            return Evaluation(True, True, contract_success, json_parse_success, None)
        if not attempt.session_path:
            return Evaluation(False, False, contract_success, json_parse_success, "session_missing")
        return Evaluation(False, False, contract_success, json_parse_success, "hard_process_failure")
    return Evaluation(True, False, contract_success, json_parse_success, None)


def should_retry(
    attempt_number: int,
    max_retries: int,
    failure_reason: str | None,
    stderr_text: str,
    had_fenced_json: bool,
) -> bool:
    if not failure_reason or attempt_number > max_retries:
        return False
    if failure_reason in {"timeout", "session_missing"}:
        return True
    if failure_reason == "json_parse_failure" and had_fenced_json:
        return True
    if failure_reason in {"contract_failure", "hard_process_failure"} and is_retryable_cli_error(stderr_text):
        return True
    return False


def run_hermes_once(
    hermes_cmd: str,
    mode: str,
    cwd: Path,
    query: str,
    timeout_seconds: int,
    attempt_dir: Path,
    session_root: Path,
) -> AttemptResult:
    ensure_dir(attempt_dir)
    save_json(
        attempt_dir / "request.json",
        {
            "mode": mode,
            "cwd": str(cwd),
            "query": query,
            "timeout_seconds": timeout_seconds,
            "timestamp_utc": utc_now(),
        },
    )
    cmd = build_command(hermes_cmd, mode, query)
    before_sessions = snapshot_session_root(session_root)
    started_ns = time.time_ns()
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env={**os.environ, "PATH": f"{Path.home() / '.local' / 'bin'}:{os.environ.get('PATH', '')}"},
        )
        stdout_text = ensure_text(completed.stdout)
        stderr_text = ensure_text(completed.stderr)
        exit_code = completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        stdout_text = ensure_text(exc.stdout)
        stderr_text = ensure_text(exc.stderr) + f"\nTIMEOUT after {timeout_seconds}s"
        exit_code = 124
        timed_out = True
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)

    (attempt_dir / "stdout.txt").write_text(stdout_text, encoding="utf-8")
    (attempt_dir / "stderr.txt").write_text(stderr_text, encoding="utf-8")

    session_id, session_source, session_path = resolve_session_file(
        session_root=session_root,
        before=before_sessions,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        started_ns=started_ns,
    )
    if session_path:
        shutil.copy2(session_path, attempt_dir / "session.json")
        bundled_session = attempt_dir / "session.json"
    else:
        bundled_session = None

    recovered = recover_final_output(
        mode="json" if mode == "json" else "text",
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        session_path=bundled_session,
    )

    return AttemptResult(
        attempt=attempt_dir.name.removeprefix("attempt-"),
        query=query,
        exit_code=exit_code,
        timed_out=timed_out,
        elapsed_ms=elapsed_ms,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        session_id=session_id,
        session_source=session_source,
        session_path=bundled_session,
        recovered=recovered,
    )


def final_output_for_mode(
    mode: str,
    recovered_output: str,
    changed_files: list[str],
    validation_results: list[dict[str, Any]],
) -> tuple[str, bool]:
    if mode == "sandbox":
        payload = serialize_sandbox_output(recovered_output, changed_files, validation_results)
        return payload, True
    if mode == "json":
        return recovered_output, bool(recovered_output.strip())
    return recovered_output, False


def write_final_artifacts(run_dir: Path, attempt_dir: Path) -> None:
    for name in ("request.json", "stdout.txt", "stderr.txt", "session.json"):
        src = attempt_dir / name
        if src.exists():
            shutil.copy2(src, run_dir / name)


def main() -> int:
    args = parse_args()
    if args.command != "run":
        raise SystemExit(f"Unsupported command: {args.command}")

    config_root = expand_path(args.config_root)
    config = load_or_init_config(config_root)
    run_root = expand_path(str(config["run_root"]))
    session_root = expand_path(str(config["session_root"]))
    ensure_dir(run_root)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    run_dir = run_root / run_id
    ensure_dir(run_dir)

    mode = args.mode
    original_query = load_query(args)
    hermes_cmd = str(config["hermes_cmd"])
    timeout_seconds = int(args.timeout or config["default_timeout_seconds"])
    max_retries = int(config["max_retries"])

    if mode == "sandbox":
        cwd = prepare_sandbox_workspace(run_dir, args.workspace)
    else:
        cwd = Path(args.cwd).expanduser().resolve()

    before_sandbox_hashes = file_hashes(cwd) if mode == "sandbox" else {}
    pre_status = git_status_lines(cwd) if mode == "readonly" else None

    attempt_result: AttemptResult | None = None
    evaluation: Evaluation | None = None
    final_output = ""
    validation_results: list[dict[str, Any]] = []
    changed_files: list[str] = []
    readonly_delta: list[str] = []

    for attempt_number in range(1, max_retries + 2):
        attempt_dir = run_dir / "attempts" / f"attempt-{attempt_number}"
        ensure_dir(attempt_dir)
        query = augment_query(mode, original_query, retry=attempt_number > 1)
        attempt_result = run_hermes_once(
            hermes_cmd=hermes_cmd,
            mode=mode,
            cwd=cwd,
            query=query,
            timeout_seconds=timeout_seconds,
            attempt_dir=attempt_dir,
            session_root=session_root,
        )

        if mode == "readonly":
            post_status = git_status_lines(cwd)
            violation, readonly_delta = readonly_violation(pre_status, post_status)
            readonly_ok = not violation
        else:
            readonly_ok = True

        if mode == "sandbox":
            validation_results = run_validation_commands(args.validation_cmd, cwd)
            changed_files = diff_changed_files(before_sandbox_hashes, file_hashes(cwd))
        else:
            validation_results = []
            changed_files = []

        candidate_output, generated_json = final_output_for_mode(
            mode=mode,
            recovered_output=attempt_result.recovered.final_output,
            changed_files=changed_files,
            validation_results=validation_results,
        )

        json_parse_success = False
        if mode == "json":
            json_parse_success = attempt_result.recovered.json_parse_success
        elif generated_json:
            json_parse_success = True

        validation_success = all(item["success"] for item in validation_results) if validation_results else True
        evaluation = evaluate_attempt(
            mode=mode,
            attempt=attempt_result,
            final_output=candidate_output,
            json_parse_success=json_parse_success,
            validation_success=validation_success,
            readonly_ok=readonly_ok,
        )
        final_output = candidate_output

        save_json(
            attempt_dir / "attempt_result.json",
            {
                "run_id": run_id,
                "attempt": attempt_number,
                "mode": mode,
                "cwd": str(cwd),
                "query_digest": sha256_text(original_query),
                "query": query,
                "session_id": attempt_result.session_id,
                "session_source": attempt_result.session_source,
                "output_source": attempt_result.recovered.output_source,
                "tool_used": attempt_result.recovered.tool_used,
                "exit_code": attempt_result.exit_code,
                "timed_out": attempt_result.timed_out,
                "elapsed_ms": attempt_result.elapsed_ms,
                "contract_success": evaluation.contract_success,
                "json_parse_success": evaluation.json_parse_success,
                "validation_success": validation_success,
                "failure_reason": evaluation.failure_reason,
                "final_output": final_output,
                "readonly_delta": readonly_delta,
                "changed_files": changed_files,
                "validation_results": validation_results,
            },
        )

        if evaluation.success:
            write_final_artifacts(run_dir, attempt_dir)
            break

        if not should_retry(
            attempt_number=attempt_number,
            max_retries=max_retries,
            failure_reason=evaluation.failure_reason,
            stderr_text=attempt_result.stderr_text,
            had_fenced_json=attempt_result.recovered.had_fenced_json,
        ):
            write_final_artifacts(run_dir, attempt_dir)
            break

        timeout_seconds = max(timeout_seconds, int(args.timeout or config["default_timeout_seconds"])) + 60

    assert attempt_result is not None
    assert evaluation is not None

    result_payload = {
        "run_id": run_id,
        "mode": mode,
        "cwd": str(cwd),
        "query_digest": sha256_text(original_query),
        "session_id": attempt_result.session_id,
        "soft_success": evaluation.soft_success,
        "exit_code": attempt_result.exit_code,
        "elapsed_ms": attempt_result.elapsed_ms,
        "tool_used": attempt_result.recovered.tool_used,
        "contract_success": evaluation.contract_success,
        "json_parse_success": evaluation.json_parse_success,
        "validation_success": all(item["success"] for item in validation_results) if validation_results else True,
        "failure_reason": evaluation.failure_reason,
        "final_output": final_output,
        "stdout_file": str(run_dir / "stdout.txt"),
        "stderr_file": str(run_dir / "stderr.txt"),
        "session_file": str(run_dir / "session.json") if (run_dir / "session.json").exists() else "",
        "output_source": attempt_result.recovered.output_source,
        "session_source": attempt_result.session_source,
        "readonly_delta": readonly_delta,
        "changed_files": changed_files,
        "validation_results": validation_results,
        "attempt_count": int(attempt_result.attempt),
        "success": evaluation.success,
    }
    save_json(run_dir / "result.json", result_payload)
    safe_symlink_latest(config_root, run_dir)

    if args.output:
        save_json(Path(args.output).expanduser().resolve(), result_payload)

    if evaluation.success:
        sys.stdout.write(final_output.strip() + ("\n" if final_output and not final_output.endswith("\n") else ""))
        return 0

    if final_output.strip():
        sys.stderr.write(final_output.strip() + ("\n" if not final_output.endswith("\n") else ""))
    if evaluation.failure_reason:
        sys.stderr.write(f"hermes-safe failure: {evaluation.failure_reason}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
