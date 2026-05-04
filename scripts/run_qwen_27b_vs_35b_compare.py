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
REMOTE_RUN_SCRIPT = "/opt/llama.cpp/run-openclaw-executor.sh"
REMOTE_SERVICE = "openclaw-executor"
RESTORE_ALIAS = "openclaw/Qwen3.5-27B-UD-Q4_K_XL"


SERVER_ARGS = [
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


MODELS = [
    {
        "model_key": "27b_dense_ud_q4_xl",
        "model_alias": "bench/qwen35-27b-dense-ud-q4_xl",
        "model_path": "/data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf",
    },
    {
        "model_key": "35b_a3b_ud_q4_xl",
        "model_alias": "bench/qwen35-35b-a3b-ud-q4_xl",
        "model_path": "/data/models/qwen/Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf",
    },
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


def make_run_script(model_path: str, model_alias: str) -> str:
    args = " \\\n  ".join(SERVER_ARGS)
    return f"""#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${{LD_LIBRARY_PATH:-}}
exec /opt/llama.cpp/build/bin/llama-server \\
  -m {model_path} \\
  --alias {model_alias} \\
  {args}
"""


def install_run_script(script_text: str, backup_path: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(script_text)

    try:
        scp_to_jump(temp_path, "/tmp/run-openclaw-bench.sh")
    finally:
        temp_path.unlink(missing_ok=True)

    remote_block = """
sshpass -p {password} scp -o StrictHostKeyChecking=no /tmp/run-openclaw-bench.sh {user}@{host}:/tmp/run-openclaw-bench.sh
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
                    "cp /tmp/run-openclaw-bench.sh {current}; "
                    "chmod +x {current}; "
                    "systemctl restart {service}".format(
                        backup=backup_path,
                        current=REMOTE_RUN_SCRIPT,
                        service=REMOTE_SERVICE,
                    )
                ),
            )
        ),
    ).strip()
    run_jump(remote_block)


def restore_run_script(backup_path: str) -> None:
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
                current=REMOTE_RUN_SCRIPT,
                service=REMOTE_SERVICE,
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


def start_remote_logger(command: str) -> str:
    logger_cmd = f"nohup bash -lc {shlex.quote(command)} >/dev/null 2>&1 & echo $!"
    return run_remote(logger_cmd).strip()


def fetch_remote_text(remote_path: str, local_path: Path) -> None:
    local_path.write_text(run_remote(f"cat {shlex.quote(remote_path)}"), encoding="utf-8")


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


def run_benchmark_command(cmd: list[str], log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as handle:
        subprocess.run(cmd, check=True, text=True, stdout=handle, stderr=subprocess.STDOUT)


def capture_round_artifacts(
    model_output_dir: Path,
    model_key: str,
    round_key: str,
    started_at_epoch: int,
) -> None:
    gpu_remote = f"/tmp/{model_key}-{round_key}-gpu.csv"
    vmstat_remote = f"/tmp/{model_key}-{round_key}-vmstat.log"
    free_before_remote = f"/tmp/{model_key}-{round_key}-free-before.log"
    free_after_remote = f"/tmp/{model_key}-{round_key}-free-after.log"

    run_remote(f"free -h > {shlex.quote(free_before_remote)}")
    gpu_pid = start_remote_logger(
        "nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw "
        f"--format=csv -l 1 > {shlex.quote(gpu_remote)}"
    )
    vmstat_pid = start_remote_logger(f"vmstat 1 > {shlex.quote(vmstat_remote)}")

    try:
        yield gpu_pid, vmstat_pid, free_before_remote, free_after_remote, gpu_remote, vmstat_remote
    finally:
        errors: list[str] = []
        try:
            run_remote(f"kill {gpu_pid} {vmstat_pid} >/dev/null 2>&1 || true")
        except Exception as exc:
            errors.append(f"kill_loggers: {exc!r}")
        time.sleep(2)
        try:
            run_remote(f"free -h > {shlex.quote(free_after_remote)}")
        except Exception as exc:
            errors.append(f"capture_free_after: {exc!r}")

        for remote_path, local_name in [
            (gpu_remote, "gpu_samples.csv"),
            (vmstat_remote, "vmstat.log"),
            (free_before_remote, "free_before.log"),
            (free_after_remote, "free_after.log"),
        ]:
            try:
                fetch_remote_text(remote_path, model_output_dir / local_name)
            except Exception as exc:
                errors.append(f"fetch_{local_name}: {exc!r}")

        try:
            journal = run_remote(f"journalctl -u {REMOTE_SERVICE} --since @{started_at_epoch} --no-pager")
            write_text(model_output_dir / "server.log", journal)
        except Exception as exc:
            errors.append(f"fetch_server_log: {exc!r}")
            write_text(model_output_dir / "server.log", "")

        try:
            run_remote(
                "rm -f {paths}".format(
                    paths=" ".join(
                        shlex.quote(path)
                        for path in [
                            gpu_remote,
                            vmstat_remote,
                            free_before_remote,
                            free_after_remote,
                        ]
                    )
                )
            )
        except Exception as exc:
            errors.append(f"cleanup_remote_artifacts: {exc!r}")

        if errors:
            write_text(model_output_dir / "artifact_capture_errors.log", "\n".join(errors) + "\n")


def run_coding_round(
    repo_root: Path,
    output_root: Path,
    base_url: str,
    api_key: str,
    model_key: str,
    model_alias: str,
) -> None:
    model_output_dir = output_root / "coding" / model_key
    model_output_dir.mkdir(parents=True, exist_ok=True)
    bench_log = model_output_dir / "bench.log"
    started_at_epoch = int(run_remote("date +%s").strip())

    capture = capture_round_artifacts(model_output_dir, model_key, "coding", started_at_epoch)
    next(capture)
    try:
        cmd = [
            "python3",
            str(repo_root / "scripts" / "qwen_model_compare_bench.py"),
            "--base-url",
            base_url,
            "--api-key",
            api_key,
            "--model",
            model_alias,
            "--model-key",
            model_key,
            "--instruction-role",
            "system",
            "--output-dir",
            str(model_output_dir),
            "--repo-root",
            str(repo_root),
            "--timeout-seconds",
            "2400",
            "--repeat",
            "1",
            "--network-retries",
            "1",
            "--benchmark-profile",
            "27b-vs-35b-64k-executor-coding",
            "--server-args",
            " ".join(SERVER_ARGS),
            "--family",
            "java",
            "--family",
            "ts",
            "--family",
            "script",
        ]
        run_benchmark_command(cmd, bench_log)
    finally:
        try:
            next(capture)
        except StopIteration:
            pass


def run_agentic_round(
    repo_root: Path,
    output_root: Path,
    base_url: str,
    api_key: str,
    model_key: str,
    model_alias: str,
    repeat: int,
) -> None:
    model_output_dir = output_root / "agentic" / model_key
    model_output_dir.mkdir(parents=True, exist_ok=True)
    workspace_root = output_root / "agentic" / "workspaces"
    workspace_root.mkdir(parents=True, exist_ok=True)
    bench_log = model_output_dir / "bench.log"
    started_at_epoch = int(run_remote("date +%s").strip())

    capture = capture_round_artifacts(model_output_dir, model_key, "agentic", started_at_epoch)
    next(capture)
    try:
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
        run_benchmark_command(cmd, bench_log)
    finally:
        try:
            next(capture)
        except StopIteration:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--wait-timeout-seconds", type=int, default=360)
    parser.add_argument("--agentic-repeat", type=int, default=2)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    summary_dir = output_root / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    backup_path = f"{REMOTE_RUN_SCRIPT}.bench-{output_root.name}.bak"
    startup_metrics: list[dict[str, object]] = []

    try:
        print(f"[runner] output_root={output_root}", flush=True)
        run_remote(
            "printf '%s\\n' {password} | sudo -S -p '' systemctl stop {service}".format(
                password=shlex.quote(REMOTE_PASSWORD),
                service=REMOTE_SERVICE,
            ),
            capture=False,
        )
        print(f"[runner] stopped {REMOTE_SERVICE}", flush=True)

        for model in MODELS:
            print(f"[runner] switching model={model['model_key']} alias={model['model_alias']}", flush=True)
            script_text = make_run_script(model["model_path"], model["model_alias"])
            started = time.perf_counter()
            install_run_script(script_text, backup_path)
            wait_for_model(args.base_url, args.api_key, model["model_alias"], args.wait_timeout_seconds)
            startup_elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
            idle_gpu = remote_gpu_snapshot()
            print(
                "[runner] ready model={model_key} startup_ms={startup_ms} idle_mem_mib={mem}".format(
                    model_key=model["model_key"],
                    startup_ms=startup_elapsed_ms,
                    mem=idle_gpu["memory_used_mib"],
                ),
                flush=True,
            )
            startup_metrics.append(
                {
                    "timestamp_utc": utc_now(),
                    "model_key": model["model_key"],
                    "model_alias": model["model_alias"],
                    "model_path": model["model_path"],
                    "startup_elapsed_ms": startup_elapsed_ms,
                    "idle_gpu": idle_gpu,
                    "server_args": SERVER_ARGS,
                }
            )

            run_coding_round(
                repo_root=repo_root,
                output_root=output_root,
                base_url=args.base_url,
                api_key=args.api_key,
                model_key=model["model_key"],
                model_alias=model["model_alias"],
            )
            print(f"[runner] coding round done model={model['model_key']}", flush=True)
            run_agentic_round(
                repo_root=repo_root,
                output_root=output_root,
                base_url=args.base_url,
                api_key=args.api_key,
                model_key=model["model_key"],
                model_alias=model["model_alias"],
                repeat=args.agentic_repeat,
            )
            print(f"[runner] agentic round done model={model['model_key']}", flush=True)
    finally:
        print("[runner] restoring original executor service", flush=True)
        restore_run_script(backup_path)
        wait_for_model(args.base_url, args.api_key, RESTORE_ALIAS, args.wait_timeout_seconds)
        print(f"[runner] restored alias={RESTORE_ALIAS}", flush=True)

    (summary_dir / "startup_metrics.json").write_text(
        json.dumps(startup_metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    coding_report_cmd = [
        "python3",
        str(repo_root / "scripts" / "render_qwen_model_compare_report.py"),
        "--baseline-results",
        str(output_root / "coding" / MODELS[0]["model_key"] / "results.csv"),
        "--candidate-results",
        str(output_root / "coding" / MODELS[1]["model_key"] / "results.csv"),
        "--baseline-key",
        MODELS[0]["model_key"],
        "--candidate-key",
        MODELS[1]["model_key"],
        "--baseline-name",
        MODELS[0]["model_alias"],
        "--candidate-name",
        MODELS[1]["model_alias"],
        "--output-md",
        str(summary_dir / "coding_compare_report.md"),
    ]
    subprocess.run(coding_report_cmd, check=True, text=True)

    agentic_report_cmd = [
        "python3",
        str(repo_root / "scripts" / "render_qwen_agentic_compare_report.py"),
        "--baseline-results",
        str(output_root / "agentic" / MODELS[0]["model_key"] / "results.csv"),
        "--candidate-results",
        str(output_root / "agentic" / MODELS[1]["model_key"] / "results.csv"),
        "--baseline-key",
        MODELS[0]["model_key"],
        "--candidate-key",
        MODELS[1]["model_key"],
        "--baseline-name",
        MODELS[0]["model_alias"],
        "--candidate-name",
        MODELS[1]["model_alias"],
        "--output-md",
        str(summary_dir / "agentic_compare_report.md"),
        "--output-json",
        str(summary_dir / "agentic_compare_summary.json"),
    ]
    subprocess.run(agentic_report_cmd, check=True, text=True)

    score_packet_cmd = [
        "python3",
        str(repo_root / "scripts" / "build_qwen_compare_score_packet.py"),
        "--baseline-results",
        str(output_root / "coding" / MODELS[0]["model_key"] / "results.csv"),
        "--candidate-results",
        str(output_root / "coding" / MODELS[1]["model_key"] / "results.csv"),
        "--baseline-key",
        MODELS[0]["model_key"],
        "--candidate-key",
        MODELS[1]["model_key"],
        "--task-manifest",
        str(output_root / "coding" / MODELS[0]["model_key"] / "task_manifest.json"),
        "--baseline-responses",
        str(output_root / "coding" / MODELS[0]["model_key"] / "responses.json"),
        "--candidate-responses",
        str(output_root / "coding" / MODELS[1]["model_key"] / "responses.json"),
        "--output-json",
        str(summary_dir / "score_packet.json"),
        "--output-template-json",
        str(summary_dir / "scores.template.json"),
        "--output-md",
        str(summary_dir / "score_packet.md"),
    ]
    subprocess.run(score_packet_cmd, check=True, text=True)
    print("[runner] summary artifacts generated", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
