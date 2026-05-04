#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PROJECT = "project-d4e4f88c-f262-47af-b5b"
ZONE = "us-central1-a"
INSTANCE = "instance-20260222-145427"
REMOTE_HOST = "100.107.189.100"
REMOTE_USER = "hhtele"
REMOTE_PASSWORD = "hhtele"

REMOTE_EXECUTOR_RUN_SCRIPT = "/opt/llama.cpp/run-openclaw-executor.sh"
REMOTE_EXECUTOR_SERVICE = "openclaw-executor"
REMOTE_CHAT_SERVICE = "qwen35-35b-a3b-uncensored"
REMOTE_CHAT_ALIAS = "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M"
REMOTE_MODEL_PATH = "/data/models/qwen/Nemotron-Cascade-2-30B-A3B-IQ4_XS.gguf"

BASE_SERVER_ARGS = [
    "-ngl 99",
    "-c 131072",
    "-np 1",
    "-fa on",
    "-ctk q4_0",
    "-ctv q4_0",
    "--temp 0.2",
    "--top-p 0.90",
    "--top-k 20",
    "--min-p 0.0",
    "--host 0.0.0.0",
    "--port 18343",
]

MODELS = [
    {
        "model_key": "nemotron_iq4_xs_no_think",
        "model_alias": "bench/nemotron-iq4-xs-no-think",
        "thinking": False,
        "reasoning_none": True,
    },
    {
        "model_key": "nemotron_iq4_xs_think",
        "model_alias": "bench/nemotron-iq4-xs-think",
        "thinking": True,
        "reasoning_none": True,
    },
    {
        "model_key": "nemotron_iq4_xs_think_parser_control",
        "model_alias": "bench/nemotron-iq4-xs-think-parser-control",
        "thinking": True,
        "reasoning_none": False,
    },
]

MAIN_TASK_IDS = [
    "longctx_restore_bootstrap",
    "longctx_metrics_contract",
    "longctx_java_change_impact",
    "multi_restore_self_repair",
    "multi_outbox_self_repair",
    "multi_reconnect_self_repair",
    "plan_boot_restore_gap",
    "plan_metrics_exposure",
    "plan_reconnect_fault_injection",
]

CONTROL_TASK_IDS = [
    "longctx_restore_bootstrap",
    "multi_restore_self_repair",
    "plan_metrics_exposure",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(
    cmd: list[str],
    *,
    capture: bool = True,
    check: bool = True,
    retries: int = 1,
    retry_delay_seconds: int = 3,
) -> subprocess.CompletedProcess[str]:
    last_completed: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, retries + 1):
        completed = subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=capture,
        )
        if completed.returncode == 0 or not check:
            return completed
        last_completed = completed
        if attempt < retries:
            time.sleep(retry_delay_seconds * attempt)

    assert last_completed is not None
    raise subprocess.CalledProcessError(
        last_completed.returncode,
        cmd,
        output=last_completed.stdout,
        stderr=last_completed.stderr,
    )


def run_jump(command: str, *, capture: bool = True) -> str:
    cmd = [
        "gcloud",
        "compute",
        "ssh",
        "--zone",
        ZONE,
        INSTANCE,
        "--project",
        PROJECT,
        "--tunnel-through-iap",
        "--ssh-flag=-o ServerAliveInterval=30",
        "--ssh-flag=-o ServerAliveCountMax=6",
        f"--command={command}",
    ]
    completed = run_command(cmd, capture=capture, retries=5, retry_delay_seconds=4)
    return completed.stdout if capture else ""


def scp_to_jump(local_path: Path, remote_path: str) -> None:
    cmd = [
        "gcloud",
        "compute",
        "scp",
        "--zone",
        ZONE,
        "--project",
        PROJECT,
        "--tunnel-through-iap",
        str(local_path),
        f"{INSTANCE}:{remote_path}",
    ]
    run_command(cmd, capture=True, retries=4, retry_delay_seconds=4)


def run_remote(command: str, *, capture: bool = True) -> str:
    nested = (
        "sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {command}".format(
            password=shlex.quote(REMOTE_PASSWORD),
            user=REMOTE_USER,
            host=REMOTE_HOST,
            command=shlex.quote(command),
        )
    )
    return run_jump(nested, capture=capture)


def remote_sudo(command: str, *, capture: bool = True) -> str:
    sudo_block = "printf '%s\\n' {password} | sudo -S -p '' bash -lc {command}".format(
        password=shlex.quote(REMOTE_PASSWORD),
        command=shlex.quote(command),
    )
    return run_remote(sudo_block, capture=capture)


def stop_service(name: str) -> None:
    remote_sudo(f"systemctl stop {name}", capture=False)


def start_service(name: str) -> None:
    remote_sudo(f"systemctl start {name}", capture=False)


def make_run_script(model_alias: str, *, thinking: bool, reasoning_none: bool) -> str:
    args = list(BASE_SERVER_ARGS)
    if reasoning_none:
        args.append("--reasoning-format none")
    args.append(f"""--chat-template-kwargs '{{"enable_thinking": {"true" if thinking else "false"}}}'""")
    joined = " \\\n  ".join(args)
    return f"""#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${{LD_LIBRARY_PATH:-}}
exec /opt/llama.cpp/build/bin/llama-server \\
  -m {REMOTE_MODEL_PATH} \\
  --alias {model_alias} \\
  {joined}
"""


def install_executor_run_script(script_text: str, backup_path: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(script_text)

    try:
        scp_to_jump(temp_path, "/tmp/run-nemotron-thinking.sh")
    finally:
        temp_path.unlink(missing_ok=True)

    remote_block = """
sshpass -p {password} scp -o StrictHostKeyChecking=no /tmp/run-nemotron-thinking.sh {user}@{host}:/tmp/run-nemotron-thinking.sh
sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {sudo_block}
""".format(
        password=shlex.quote(REMOTE_PASSWORD),
        user=REMOTE_USER,
        host=REMOTE_HOST,
        sudo_block=shlex.quote(
            "printf '%s\\n' {password} | sudo -S -p '' bash -lc {command}".format(
                password=shlex.quote(REMOTE_PASSWORD),
                command=shlex.quote(
                    "test -f {backup} || cp {current} {backup}; "
                    "cp /tmp/run-nemotron-thinking.sh {current}; "
                    "chmod +x {current}; "
                    "systemctl restart {service}".format(
                        backup=backup_path,
                        current=REMOTE_EXECUTOR_RUN_SCRIPT,
                        service=REMOTE_EXECUTOR_SERVICE,
                    )
                ),
            )
        ),
    ).strip()
    run_jump(remote_block)


def restore_executor_run_script(backup_path: str) -> None:
    remote_command = """
if test -f {backup}; then
  printf '%s\\n' {password} | sudo -S -p '' bash -lc {command}
fi
""".format(
        backup=shlex.quote(backup_path),
        password=shlex.quote(REMOTE_PASSWORD),
        command=shlex.quote(
            "cp {backup} {current}; "
            "chmod +x {current}; "
            "systemctl restart {service}".format(
                backup=backup_path,
                current=REMOTE_EXECUTOR_RUN_SCRIPT,
                service=REMOTE_EXECUTOR_SERVICE,
            )
        ),
    ).strip()
    run_remote(remote_command)


def wait_for_model(base_url: str, api_key: str, expected_alias: str, timeout_seconds: int) -> None:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            request = urllib.request.Request(
                f"{base_url.rstrip('/')}/models",
                headers=headers,
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            aliases = [item.get("id") for item in payload.get("data", [])]
            if expected_alias in aliases:
                return
        except Exception:
            pass
        time.sleep(3)
    raise TimeoutError(f"Timed out waiting for {expected_alias}")


def smoke_chat(base_url: str, api_key: str, model_alias: str, timeout_seconds: int) -> dict[str, object]:
    payload = {
        "model": model_alias,
        "messages": [{"role": "user", "content": "Reply READY only."}],
        "max_tokens": 96,
        "stream": False,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
            payload = json.loads(raw.decode("utf-8"))
            message = ((payload.get("choices") or [{}])[0].get("message") or {})
            return {
                "http_status": response.status,
                "elapsed_ms": elapsed_ms,
                "content": message.get("content") or "",
                "reasoning_content": message.get("reasoning_content") or "",
            }
    except urllib.error.HTTPError as exc:
        return {"http_status": exc.code, "error": exc.read().decode("utf-8", errors="replace")}
    except Exception as exc:
        return {"http_status": 0, "error": repr(exc)}


def run_benchmark_command(cmd: list[str], log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as handle:
        subprocess.run(cmd, check=True, text=True, stdout=handle, stderr=subprocess.STDOUT)


def run_specialized_round(
    repo_root: Path,
    output_dir: Path,
    base_url: str,
    api_key: str,
    model_key: str,
    model_alias: str,
    task_ids: list[str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    bench_log = output_dir / "bench.log"
    cmd = [
        "python3",
        str(repo_root / "scripts" / "nemotron_thinking_specialized_bench.py"),
        "--base-url",
        base_url,
        "--api-key",
        api_key,
        "--model",
        model_alias,
        "--model-key",
        model_key,
        "--output-dir",
        str(output_dir),
        "--repo-root",
        str(repo_root),
        "--timeout-seconds",
        "2400",
    ]
    for task_id in task_ids:
        cmd.extend(["--task-id", task_id])
    run_benchmark_command(cmd, bench_log)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def remote_gpu_snapshot() -> dict[str, int]:
    raw = run_remote(
        "nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,utilization.memory "
        "--format=csv,noheader,nounits"
    ).strip()
    values = [item.strip() for item in raw.split(",")]
    return {
        "memory_used_mib": int(values[0]),
        "memory_total_mib": int(values[1]),
        "utilization_gpu_pct": int(values[2]),
        "utilization_memory_pct": int(values[3]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--wait-timeout-seconds", type=int, default=420)
    parser.add_argument("--smoke-timeout-seconds", type=int, default=120)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    summary_dir = output_root / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    backup_path = f"{REMOTE_EXECUTOR_RUN_SCRIPT}.thinking-{output_root.name}.bak"
    startup_metrics: list[dict[str, object]] = []
    smoke_results: list[dict[str, object]] = []

    try:
        stop_service(REMOTE_CHAT_SERVICE)
        start_service(REMOTE_EXECUTOR_SERVICE)

        for model in MODELS:
            script_text = make_run_script(
                model_alias=model["model_alias"],
                thinking=bool(model["thinking"]),
                reasoning_none=bool(model["reasoning_none"]),
            )
            started = time.perf_counter()
            install_executor_run_script(script_text, backup_path)
            wait_for_model(args.base_url, args.api_key, model["model_alias"], args.wait_timeout_seconds)
            startup_metrics.append(
                {
                    "timestamp_utc": utc_now(),
                    "model_key": model["model_key"],
                    "model_alias": model["model_alias"],
                    "thinking": model["thinking"],
                    "reasoning_none": model["reasoning_none"],
                    "startup_elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "idle_gpu": remote_gpu_snapshot(),
                }
            )
            smoke = smoke_chat(args.base_url, args.api_key, model["model_alias"], args.smoke_timeout_seconds)
            smoke["model_key"] = model["model_key"]
            smoke["model_alias"] = model["model_alias"]
            smoke["thinking"] = model["thinking"]
            smoke["reasoning_none"] = model["reasoning_none"]
            smoke_results.append(smoke)
            if smoke.get("http_status") != 200:
                raise SystemExit(f"Smoke failed for {model['model_key']}: {smoke}")

            task_ids = MAIN_TASK_IDS if model["reasoning_none"] else CONTROL_TASK_IDS
            target_dir = output_root / ("main" if model["reasoning_none"] else "control") / model["model_key"]
            run_specialized_round(
                repo_root=repo_root,
                output_dir=target_dir,
                base_url=args.base_url,
                api_key=args.api_key,
                model_key=model["model_key"],
                model_alias=model["model_alias"],
                task_ids=task_ids,
            )
    finally:
        try:
            restore_executor_run_script(backup_path)
        finally:
            stop_service(REMOTE_EXECUTOR_SERVICE)
            start_service(REMOTE_CHAT_SERVICE)
            wait_for_model(args.base_url, args.api_key, REMOTE_CHAT_ALIAS, args.wait_timeout_seconds)

    write_text(summary_dir / "startup_metrics.json", json.dumps(startup_metrics, ensure_ascii=False, indent=2))
    write_text(summary_dir / "smoke_results.json", json.dumps(smoke_results, ensure_ascii=False, indent=2))

    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_nemotron_thinking_specialized_report.py"),
            "--baseline-results",
            str(output_root / "main" / MODELS[0]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "main" / MODELS[1]["model_key"] / "results.csv"),
            "--baseline-name",
            MODELS[0]["model_alias"],
            "--candidate-name",
            MODELS[1]["model_alias"],
            "--output-md",
            str(summary_dir / "main_compare_report.md"),
        ],
        check=True,
        text=True,
    )

    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_nemotron_thinking_specialized_report.py"),
            "--baseline-results",
            str(output_root / "control" / MODELS[2]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "main" / MODELS[1]["model_key"] / "results.csv"),
            "--baseline-name",
            MODELS[2]["model_alias"],
            "--candidate-name",
            MODELS[1]["model_alias"],
            "--output-md",
            str(summary_dir / "parser_control_report.md"),
        ],
        check=True,
        text=True,
    )

    write_text(
        summary_dir / "run_summary.md",
        "\n".join(
            [
                "# Nemotron Thinking Specialized Run Summary",
                "",
                f"- Generated at (UTC): `{utc_now()}`",
                f"- Restored live alias: `{REMOTE_CHAT_ALIAS}`",
                "- Main compare: `thinking=false` vs `thinking=true`, both with `--reasoning-format none`",
                "- Parser control: `thinking=true` with parser enabled vs `thinking=true` with `--reasoning-format none`",
            ]
        )
        + "\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
