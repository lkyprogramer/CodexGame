from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from .catalog import Task
from .client import OpenAICompatibleClient
from .config import RunConfig
from .hardware import GPUSampler
from .patching import apply_unified_diff, extract_unified_diff, git_diff, initialize_git
from .tools import AgentWorkspace, READ_ONLY_TOOL_DEFINITIONS, TOOL_DEFINITIONS, parse_tool_arguments
from .util import append_jsonl, dump_json, read_jsonl, sha256_file, sha256_text, utc_now
from .verifier import verify_task


DEFAULT_SYSTEM_PROMPT = """You are being evaluated as a coding agent. Work only inside the provided repository. Do not claim success without checking available public tests. Never attempt to access hidden tests. For patch tasks, finish by applying a unified diff. For review tasks, return the exact JSON format requested by the task."""


def _usage(raw: dict[str, Any]) -> dict[str, Any]:
    usage = dict(raw or {})
    details = usage.get("completion_tokens_details") or {}
    if "reasoning_tokens" not in usage:
        usage["reasoning_tokens"] = details.get("reasoning_tokens")
    return usage


def _assistant_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(x.get("text", "")) if isinstance(x, dict) else str(x) for x in content)
    return str(content or "")


def _number(mapping: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _endpoint_metrics(raw_responses: list[dict[str, Any]]) -> dict[str, Any]:
    prompt_rates: list[float] = []
    decode_rates: list[float] = []
    prompt_ms = 0.0
    decode_ms = 0.0
    drafted = 0.0
    accepted = 0.0
    timing_seen = False
    draft_seen = False

    for raw in raw_responses:
        timings = raw.get("timings") if isinstance(raw.get("timings"), dict) else {}
        prompt_rate = _number(timings, "prompt_per_second", "prompt_tokens_per_second")
        decode_rate = _number(timings, "predicted_per_second", "decode_tokens_per_second")
        if prompt_rate is not None:
            prompt_rates.append(prompt_rate)
        if decode_rate is not None:
            decode_rates.append(decode_rate)
        current_prompt_ms = _number(timings, "prompt_ms")
        current_decode_ms = _number(timings, "predicted_ms", "decode_ms")
        if current_prompt_ms is not None:
            prompt_ms += current_prompt_ms
            timing_seen = True
        if current_decode_ms is not None:
            decode_ms += current_decode_ms
            timing_seen = True

        current_drafted = _number(raw, "draft_tokens", "draft_n", "n_drafted")
        current_accepted = _number(raw, "accepted_draft_tokens", "draft_n_accepted", "n_accepted")
        if current_drafted is None:
            current_drafted = _number(timings, "draft_tokens", "draft_n", "n_drafted")
        if current_accepted is None:
            current_accepted = _number(timings, "accepted_draft_tokens", "draft_n_accepted", "n_accepted")
        if current_drafted is not None:
            drafted += current_drafted
            draft_seen = True
        if current_accepted is not None:
            accepted += current_accepted
            draft_seen = True

    return {
        "prompt_tokens_per_second_median": sorted(prompt_rates)[len(prompt_rates) // 2] if prompt_rates else None,
        "decode_tokens_per_second_median": sorted(decode_rates)[len(decode_rates) // 2] if decode_rates else None,
        "reported_prompt_ms_total": prompt_ms if timing_seen else None,
        "reported_decode_ms_total": decode_ms if timing_seen else None,
        "draft_tokens": drafted if draft_seen else None,
        "accepted_draft_tokens": accepted if draft_seen else None,
        "mtp_acceptance_rate": (accepted / drafted) if draft_seen and drafted > 0 else None,
        "ttft_seconds": None,
        "ttft_note": "N/A: runner uses non-streaming responses; collect TTFT from server telemetry if required",
    }


def _safe_filename(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return sanitized or "model"


def _load_system_prompt(root: Path, config: RunConfig) -> tuple[str, Path | None]:
    configured = config.inference.system_prompt_file.strip()
    if not configured:
        return DEFAULT_SYSTEM_PROMPT, None
    path = (root / configured).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"System prompt file not found: {path}")
    return path.read_text(encoding="utf-8"), path


def run_task(
    benchmark_root: str | Path,
    task: Task,
    config: RunConfig,
    suite_name: str,
    output_dir: str | Path,
    *,
    seed: int | None = None,
    model_hash_status: str = "not_checked",
) -> dict[str, Any]:
    root = Path(benchmark_root).resolve()
    output_dir = Path(output_dir).resolve()
    started_at = utc_now()
    compact_time = re.sub(r"[^0-9TZ]", "", started_at)
    run_id = f"{compact_time}-{task.id}-{uuid.uuid4().hex[:8]}"
    artifact_dir = output_dir / "artifacts" / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    actual_seed = config.inference.seed if seed is None else seed

    with tempfile.TemporaryDirectory(prefix=f"qcb-{task.id}-") as temporary:
        workspace = Path(temporary) / "workspace"
        shutil.copytree(task.workspace_dir, workspace)
        initialize_git(workspace)
        public_command = task.metadata.get("public_test_command")
        agent_workspace = AgentWorkspace(workspace, public_command)

        system_prompt, system_path = _load_system_prompt(root, config)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task.prompt},
        ]
        client = OpenAICompatibleClient(
            config.endpoint.base_url,
            config.endpoint.api_key,
            config.endpoint.timeout_seconds,
        )
        tools = None
        if config.inference.tool_mode and config.inference.max_tool_calls > 0:
            if task.task_type in {"patch", "agent"}:
                tools = TOOL_DEFINITIONS
            elif task.task_type == "review":
                tools = READ_ONLY_TOOL_DEFINITIONS
        sampler = GPUSampler()
        sampler.start()
        started = time.perf_counter()
        raw_responses: list[dict[str, Any]] = []
        tool_trace: list[dict[str, Any]] = []
        total_usage: dict[str, float | None] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "reasoning_tokens": None,
        }
        outcome = "unknown"
        final_text = ""
        answer_file: Path | None = None
        invalid_tool_calls = 0
        failed_tool_operations = 0
        endpoint_retries = 0
        public_test_results: list[bool] = []
        turn = 0

        try:
            while True:
                last_error: Exception | None = None
                response = None
                for attempt in range(config.inference.max_retries + 1):
                    try:
                        response = client.chat(
                            model=config.endpoint.model,
                            messages=messages,
                            tools=tools,
                            temperature=config.inference.temperature,
                            top_p=config.inference.top_p,
                            top_k=config.inference.top_k,
                            min_p=config.inference.min_p,
                            max_tokens=config.inference.max_tokens,
                            seed=actual_seed,
                            reasoning_effort=config.inference.reasoning_effort,
                            extra_body=config.inference.extra_body,
                        )
                        break
                    except Exception as exc:
                        last_error = exc
                        if attempt >= config.inference.max_retries:
                            raise
                        endpoint_retries += 1
                        time.sleep(min(2.0, 0.5 * (2**attempt)))
                if response is None:
                    raise RuntimeError(f"Endpoint returned no response: {last_error}")

                raw_responses.append(response.raw)
                for key, value in _usage(response.usage).items():
                    if not isinstance(value, (int, float)) or key not in total_usage:
                        continue
                    current = total_usage[key]
                    total_usage[key] = (0 if current is None else current) + value

                message = response.message
                messages.append(message)
                tool_calls = message.get("tool_calls") or []
                if tool_calls and tools:
                    budget_exhausted = False
                    for call in tool_calls:
                        if len(tool_trace) >= config.inference.max_tool_calls:
                            outcome = "tool_budget_exhausted"
                            budget_exhausted = True
                            break
                        function = call.get("function") or {}
                        name = str(function.get("name", ""))
                        arguments = parse_tool_arguments(function.get("arguments"))
                        result = agent_workspace.execute(name, arguments)
                        invocation_valid = bool(result.get("invocation_valid", True))
                        if not invocation_valid:
                            invalid_tool_calls += 1
                        elif not result.get("ok"):
                            failed_tool_operations += 1
                        if name == "run_tests" and invocation_valid:
                            public_test_results.append(bool(result.get("ok")))
                        event = {
                            "turn": turn,
                            "tool": name,
                            "arguments": arguments,
                            "invocation_valid": invocation_valid,
                            "result": result,
                        }
                        tool_trace.append(event)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.get("id", f"call-{turn}-{len(tool_trace)}"),
                                "name": name,
                                "content": json.dumps(result, ensure_ascii=False),
                            }
                        )
                    if budget_exhausted:
                        break
                    turn += 1
                    continue

                final_text = _assistant_text(message)
                if task.task_type == "review":
                    answer_file = artifact_dir / "answer.json"
                    text = final_text.strip()
                    if text.startswith("```"):
                        lines = text.splitlines()
                        if len(lines) >= 3:
                            text = "\n".join(lines[1:-1])
                    answer_file.write_text(text + "\n", encoding="utf-8")
                    outcome = "completed"
                else:
                    existing_diff = git_diff(workspace)
                    if existing_diff.strip():
                        outcome = "completed"
                    else:
                        patch = extract_unified_diff(final_text)
                        if not patch:
                            outcome = "invalid_output"
                        else:
                            ok, apply_output = apply_unified_diff(workspace, patch)
                            outcome = "completed" if ok else "patch_failed"
                            (artifact_dir / "patch-apply.log").write_text(apply_output + "\n", encoding="utf-8")
                break
        except Exception as exc:
            final_text = f"{type(exc).__name__}: {exc}"
            outcome = "endpoint_error"
        finally:
            wall_seconds = time.perf_counter() - started
            gpu = sampler.stop()

        verification = verify_task(task, workspace, answer_file=answer_file)
        diff = git_diff(workspace)
        (artifact_dir / "final-response.txt").write_text(final_text, encoding="utf-8")
        (artifact_dir / "final.patch").write_text(diff, encoding="utf-8")
        dump_json(artifact_dir / "raw-responses.json", raw_responses)
        dump_json(artifact_dir / "tool-trace.json", tool_trace)
        dump_json(artifact_dir / "verification.json", verification)
        if gpu.get("available"):
            dump_json(artifact_dir / "gpu-samples.json", gpu)

        benchmark_version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").is_file() else "unknown"
        manifest_path = root / "MANIFEST.sha256"
        public_test_runs = len(public_test_results)
        record = {
            "schema_version": "1.0.0",
            "benchmark": {
                "name": "QCB-4090",
                "version": benchmark_version,
                "manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
            },
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": utc_now(),
            "suite": suite_name,
            "lane": config.inference.lane,
            "seed": actual_seed,
            "model": {
                "id": config.model.id,
                "family": config.model.family,
                "file": config.model.file,
                "sha256": config.model.sha256,
                "hash_status": model_hash_status,
                "quantization": config.model.quantization,
                "template_id": config.model.template_id,
                "notes": config.model.notes,
            },
            "endpoint": {
                "base_url": config.endpoint.base_url,
                "model": config.endpoint.model,
                "timeout_seconds": config.endpoint.timeout_seconds,
                "retry_count": endpoint_retries,
            },
            "config": {
                "source": str(config.source_path),
                "sha256": sha256_file(config.source_path),
            },
            "inference": {
                "temperature": config.inference.temperature,
                "top_p": config.inference.top_p,
                "top_k": config.inference.top_k,
                "min_p": config.inference.min_p,
                "max_tokens": config.inference.max_tokens,
                "context_size": config.inference.context_size,
                "reasoning_effort": config.inference.reasoning_effort,
                "mtp_enabled": config.inference.mtp_enabled,
                "tool_mode": config.inference.tool_mode,
                "max_tool_calls": config.inference.max_tool_calls,
                "system_prompt_file": str(system_path) if system_path else None,
                "system_prompt_sha256": sha256_text(system_prompt),
            },
            "task": {
                "id": task.id,
                "title": task.title,
                "category": task.category,
                "language": task.language,
                "difficulty": task.difficulty,
                "weight": task.weight,
                "task_type": task.task_type,
                "prompt_sha256": sha256_text(task.prompt),
                "metadata_sha256": sha256_file(task.task_dir / "task.json"),
            },
            "outcome": outcome,
            "verification": verification,
            "usage": total_usage,
            "timing": {"wall_seconds": wall_seconds},
            "endpoint_metrics": _endpoint_metrics(raw_responses),
            "agent": {
                "tool_calls": len(tool_trace),
                "invalid_tool_calls": invalid_tool_calls,
                "failed_tool_operations": failed_tool_operations,
                "public_test_runs": public_test_runs,
                "public_test_failures": sum(1 for value in public_test_results if not value),
                "public_test_final_pass": public_test_results[-1] if public_test_results else None,
                "recovered_after_public_test_failure": bool(public_test_results and not public_test_results[0] and public_test_results[-1]),
                "patch_bytes": len(diff.encode("utf-8")),
            },
            "gpu": {k: v for k, v in gpu.items() if k != "raw"},
            "artifacts": str(artifact_dir),
        }
        return record


def run_suite(
    benchmark_root: str | Path,
    tasks: list[Task],
    config: RunConfig,
    suite_name: str,
    output_dir: str | Path,
    seeds: list[int],
    *,
    resume: bool = False,
    overwrite: bool = False,
) -> Path:
    if resume and overwrite:
        raise ValueError("resume and overwrite are mutually exclusive")
    root = Path(benchmark_root).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_model_id = _safe_filename(config.model.id)
    result_file = output_dir / f"{safe_model_id}-{config.inference.lane}-{suite_name}.jsonl"

    existing_keys: set[tuple[str, int]] = set()
    if result_file.exists() and result_file.stat().st_size > 0:
        if overwrite:
            result_file.unlink()
        elif resume:
            rows = read_jsonl(result_file)
            for row in rows:
                if row.get("model", {}).get("id") != config.model.id:
                    raise ValueError("Existing result file contains a different model ID")
                if row.get("lane") != config.inference.lane or row.get("suite") != suite_name:
                    raise ValueError("Existing result file contains a different lane or suite")
                existing_keys.add((str(row["task"]["id"]), int(row.get("seed", 0))))
        else:
            raise FileExistsError(
                f"Result file already exists: {result_file}. Use --resume to continue or --overwrite to replace it."
            )

    model_hash_status = "not_configured"
    if config.model.file:
        model_path = Path(config.model.file)
        if not model_path.is_file():
            raise FileNotFoundError(f"Configured model file not found: {model_path}")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", config.model.sha256):
            raise ValueError("model.sha256 must be a 64-character hexadecimal SHA-256")
        print("Verifying model SHA-256 once before suite...", flush=True)
        model_hash_status = "match" if sha256_file(model_path) == config.model.sha256.lower() else "mismatch"
        if model_hash_status != "match":
            raise ValueError("Model SHA-256 does not match config")

    planned = [(seed, task) for seed in seeds for task in tasks if (task.id, seed) not in existing_keys]
    if not planned:
        print("No pending task/seed pairs; result file is already complete for this request.", flush=True)
        return result_file

    for seed, task in planned:
        record = run_task(root, task, config, suite_name, output_dir, seed=seed, model_hash_status=model_hash_status)
        append_jsonl(result_file, record)
        status = "PASS" if record["verification"]["passed"] else "FAIL"
        print(f"[{status}] {task.id} seed={seed} outcome={record['outcome']}", flush=True)
    return result_file
