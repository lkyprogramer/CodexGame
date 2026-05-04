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
from pathlib import Path


PROJECT = "project-d4e4f88c-f262-47af-b5b"
ZONE = "us-central1-a"
INSTANCE = "instance-20260222-145427"
REMOTE_HOST = "100.107.189.100"
REMOTE_USER = "hhtele"
REMOTE_PASSWORD = "hhtele"
REMOTE_RUN_SCRIPT = "/opt/llama.cpp/run-qwen.sh"


MODELS = [
    {
        "model_key": "ud_q4_xl",
        "model_alias": "unsloth/Qwen3.5-27B-UD-Q4_K_XL",
        "model_path": "/data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf",
    },
    {
        "model_key": "distilled_q4_k_m",
        "model_alias": "jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-Q4_K_M",
        "model_path": "/data/models/qwen/Qwen3.5-27B.Q4_K_M.gguf",
    },
]


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
        f"--command={command}",
    ]
    completed = run_command(cmd, capture=capture, retries=4, retry_delay_seconds=4)
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


def make_run_script(model_path: str, model_alias: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${{LD_LIBRARY_PATH:-}}
exec /opt/llama.cpp/build/bin/llama-server \\
  -m {model_path} \\
  --alias {model_alias} \\
  -ngl 99 \\
  -c 65536 \\
  -np 1 \\
  -fa on \\
  -ctk q4_0 \\
  -ctv q4_0 \\
  --temp 0.6 \\
  --top-p 0.95 \\
  --top-k 20 \\
  --min-p 0.0 \\
  --chat-template-kwargs '{{"enable_thinking": true}}' \\
  --host 0.0.0.0 \\
  --port 18343
"""


def install_run_script(script_text: str, backup_path: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(script_text)

    try:
        scp_to_jump(temp_path, "/tmp/run-qwen-agentic.sh")
    finally:
        temp_path.unlink(missing_ok=True)

    sudo_block = (
        "printf '%s\\n' {password} | sudo -S -p '' bash -lc {command}".format(
            password=shlex.quote(REMOTE_PASSWORD),
            command=shlex.quote(
                "test -f {backup} || cp {current} {backup}; "
                "cp /tmp/run-qwen-agentic.sh {current}; "
                "chmod +x {current}; "
                "systemctl restart llama-qwen".format(
                    backup=backup_path,
                    current=REMOTE_RUN_SCRIPT,
                )
            ),
        )
    )
    jump_command = f"""
sshpass -p {shlex.quote(REMOTE_PASSWORD)} scp -o StrictHostKeyChecking=no /tmp/run-qwen-agentic.sh {REMOTE_USER}@{REMOTE_HOST}:/tmp/run-qwen-agentic.sh
sshpass -p {shlex.quote(REMOTE_PASSWORD)} ssh -o StrictHostKeyChecking=no {REMOTE_USER}@{REMOTE_HOST} {shlex.quote(sudo_block)}
""".strip()
    run_jump(jump_command)


def restore_run_script(backup_path: str) -> None:
    sudo_block = (
        "printf '%s\\n' {password} | sudo -S -p '' bash -lc {command}".format(
            password=shlex.quote(REMOTE_PASSWORD),
            command=shlex.quote(
                "if test -f {backup}; then "
                "cp {backup} {current}; "
                "chmod +x {current}; "
                "systemctl restart llama-qwen; "
                "fi".format(
                    backup=backup_path,
                    current=REMOTE_RUN_SCRIPT,
                )
            ),
        )
    )
    remote_command = f"""
if test -f {shlex.quote(backup_path)}; then
  {sudo_block}
fi
""".strip()
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


def start_remote_logger(command: str) -> str:
    logger_cmd = f"nohup bash -lc {shlex.quote(command)} >/dev/null 2>&1 & echo $!"
    return run_remote(logger_cmd).strip()


def fetch_remote_text(remote_path: str, local_path: Path) -> None:
    local_path.write_text(run_remote(f"cat {shlex.quote(remote_path)}"), encoding="utf-8")


def run_benchmark(
    repo_root: Path,
    output_root: Path,
    base_url: str,
    api_key: str,
    model_key: str,
    model_alias: str,
    repeat: int,
) -> None:
    model_output_dir = output_root / model_key
    model_output_dir.mkdir(parents=True, exist_ok=True)
    workspace_root = output_root / "workspaces"
    workspace_root.mkdir(parents=True, exist_ok=True)

    started_at = run_remote("date --iso-8601=seconds").strip()
    gpu_remote = f"/tmp/{model_key}-agentic-gpu.csv"
    vmstat_remote = f"/tmp/{model_key}-agentic-vmstat.log"
    free_before_remote = f"/tmp/{model_key}-agentic-free-before.log"
    free_after_remote = f"/tmp/{model_key}-agentic-free-after.log"

    run_remote(f"free -h > {shlex.quote(free_before_remote)}")
    gpu_pid = start_remote_logger(
        f"nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw --format=csv -l 1 > {shlex.quote(gpu_remote)}"
    )
    vmstat_pid = start_remote_logger(f"vmstat 1 > {shlex.quote(vmstat_remote)}")

    bench_log = model_output_dir / "bench.log"
    cmd = [
        "python3",
        str(repo_root / "scripts" / "qwen_agentic_codegen_bench.py"),
        "--base-url",
        base_url,
        "--api-key",
        api_key,
        "--model",
        model_alias,
        "--model-key",
        model_key,
        "--output-dir",
        str(model_output_dir),
        "--workspace-root",
        str(workspace_root),
        "--timeout-seconds",
        "2400",
        "--repeat",
        str(repeat),
        "--instruction-role",
        "system",
    ]

    try:
        with bench_log.open("w", encoding="utf-8") as handle:
            subprocess.run(cmd, check=True, text=True, stdout=handle, stderr=subprocess.STDOUT)
    finally:
        run_remote(f"kill {gpu_pid} {vmstat_pid} >/dev/null 2>&1 || true")
        time.sleep(2)
        run_remote(f"free -h > {shlex.quote(free_after_remote)}")
        fetch_remote_text(gpu_remote, model_output_dir / "gpu_samples.csv")
        fetch_remote_text(vmstat_remote, model_output_dir / "vmstat.log")
        fetch_remote_text(free_before_remote, model_output_dir / "free_before.log")
        fetch_remote_text(free_after_remote, model_output_dir / "free_after.log")
        journal = run_remote(f"journalctl -u llama-qwen --since {shlex.quote(started_at)} --no-pager")
        (model_output_dir / "server.log").write_text(journal, encoding="utf-8")
        run_remote(
            "rm -f {paths}".format(
                paths=" ".join(
                    shlex.quote(path)
                    for path in [gpu_remote, vmstat_remote, free_before_remote, free_after_remote]
                )
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--wait-timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    backup_path = f"{REMOTE_RUN_SCRIPT}.agentic-bench-{output_root.name}.bak"
    summary_dir = output_root / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    try:
        for model in MODELS:
            script_text = make_run_script(model["model_path"], model["model_alias"])
            install_run_script(script_text, backup_path)
            wait_for_model(args.base_url, args.api_key, model["model_alias"], args.wait_timeout_seconds)
            run_benchmark(
                repo_root=repo_root,
                output_root=output_root,
                base_url=args.base_url,
                api_key=args.api_key,
                model_key=model["model_key"],
                model_alias=model["model_alias"],
                repeat=args.repeat,
            )
    finally:
        restore_run_script(backup_path)
        wait_for_model(
            args.base_url,
            args.api_key,
            "jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-Q4_K_M",
            args.wait_timeout_seconds,
        )

    report_cmd = [
        "python3",
        str(repo_root / "scripts" / "render_qwen_agentic_compare_report.py"),
        "--baseline-results",
        str(output_root / "ud_q4_xl" / "results.csv"),
        "--candidate-results",
        str(output_root / "distilled_q4_k_m" / "results.csv"),
        "--baseline-key",
        "ud_q4_xl",
        "--candidate-key",
        "distilled_q4_k_m",
        "--baseline-name",
        MODELS[0]["model_alias"],
        "--candidate-name",
        MODELS[1]["model_alias"],
        "--output-md",
        str(summary_dir / "agentic_compare_report.md"),
        "--output-json",
        str(summary_dir / "agentic_compare_summary.json"),
    ]
    subprocess.run(report_cmd, check=True, text=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
