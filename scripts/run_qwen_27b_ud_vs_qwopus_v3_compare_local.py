#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


REMOTE_PASSWORD = "hhtele"
BENCH_RUN_SCRIPT = "/opt/llama.cpp/run-openclaw-executor.sh"
BENCH_SERVICE = "openclaw-executor"
LIVE_SERVICE = "qwen35-35b-a3b-uncensored"
LIVE_ALIAS = "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M"
QWOPUS_REMOTE_PATH = "/data/models/qwen/Qwopus3.5-27B-v3-Q4_K_M.gguf"

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

SERVER_ARGS_262K = [
    "-ngl 99",
    "-c 262144",
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
        "model_key": "27b_ud_q4_xl",
        "model_alias": "bench/qwen35-27b-ud-q4_xl",
        "model_path": "/data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf",
    },
    {
        "model_key": "qwopus35_27b_v3_q4_k_m",
        "model_alias": "bench/qwopus35-27b-v3-q4_k_m",
        "model_path": QWOPUS_REMOTE_PATH,
    },
]


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


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def gpu_snapshot() -> dict[str, int]:
    raw = run_local(
        "nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,utilization.memory --format=csv,noheader,nounits"
    ).strip()
    values = [item.strip() for item in raw.split(",")]
    return {
        "memory_used_mib": int(values[0]),
        "memory_total_mib": int(values[1]),
        "utilization_gpu_pct": int(values[2]),
        "utilization_memory_pct": int(values[3]),
    }


@contextmanager
def capture_round_artifacts(model_output_dir: Path, model_key: str, round_key: str, service_name: str):
    started_at_epoch = int(run_local("date +%s").strip())
    gpu_log = model_output_dir / "gpu_samples.csv"
    vmstat_log = model_output_dir / "vmstat.log"
    free_before = model_output_dir / "free_before.log"
    free_after = model_output_dir / "free_after.log"
    free_before.write_text(run_local("free -h"), encoding="utf-8")
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
        time.sleep(2)
        free_after.write_text(run_local("free -h"), encoding="utf-8")
        try:
            journal = sudo_local(f"journalctl -u {service_name} --since @{started_at_epoch} --no-pager")
            (model_output_dir / "server.log").write_text(journal, encoding="utf-8")
        except Exception:
            (model_output_dir / "server.log").write_text("", encoding="utf-8")


def run_benchmark_command(cmd: list[str], log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as handle:
        subprocess.run(cmd, check=True, text=True, stdout=handle, stderr=subprocess.STDOUT)


def switch_model(base_url: str, api_key: str, model: dict[str, str], server_args: list[str], backup_path: str, wait_timeout_seconds: int) -> dict[str, object]:
    install_run_script(make_run_script(model["model_path"], model["model_alias"], server_args), backup_path)
    sudo_local(f"systemctl reset-failed {BENCH_SERVICE} || true", capture=False)
    sudo_local(f"systemctl restart {BENCH_SERVICE}", capture=False)
    wait_for_model(base_url, api_key, model["model_alias"], wait_timeout_seconds)
    return {
        "timestamp_utc": utc_now(),
        "model_key": model["model_key"],
        "model_alias": model["model_alias"],
        "model_path": model["model_path"],
        "server_args": server_args,
        "idle_gpu": gpu_snapshot(),
    }


def run_coding_round(repo_root: Path, output_root: Path, base_url: str, api_key: str, model_key: str, model_alias: str, benchmark_profile: str, families: list[str]) -> None:
    model_output_dir = output_root / model_key
    model_output_dir.mkdir(parents=True, exist_ok=True)
    bench_log = model_output_dir / "bench.log"
    with capture_round_artifacts(model_output_dir, model_key, benchmark_profile, BENCH_SERVICE):
        cmd = [
            "python3",
            str(repo_root / "scripts" / "qwen_model_compare_bench.py"),
            "--base-url", base_url,
            "--api-key", api_key,
            "--model", model_alias,
            "--model-key", model_key,
            "--instruction-role", "system",
            "--output-dir", str(model_output_dir),
            "--repo-root", str(repo_root),
            "--timeout-seconds", "3000",
            "--repeat", "1",
            "--network-retries", "1",
            "--benchmark-profile", benchmark_profile,
            "--server-args", " ".join(SERVER_ARGS_262K if "262k" in benchmark_profile else SERVER_ARGS_64K),
        ]
        for family in families:
            cmd.extend(["--family", family])
        run_benchmark_command(cmd, bench_log)


def run_agentic_round(repo_root: Path, output_root: Path, base_url: str, api_key: str, model_key: str, model_alias: str, repeat: int) -> None:
    model_output_dir = output_root / model_key
    model_output_dir.mkdir(parents=True, exist_ok=True)
    workspace_root = output_root.parent / "workspaces"
    workspace_root.mkdir(parents=True, exist_ok=True)
    bench_log = model_output_dir / "bench.log"
    with capture_round_artifacts(model_output_dir, model_key, "agentic", BENCH_SERVICE):
        cmd = [
            "python3",
            str(repo_root / "scripts" / "qwen_agentic_codegen_bench.py"),
            "--base-url", base_url,
            "--api-key", api_key,
            "--model", model_alias,
            "--model-key", model_key,
            "--output-dir", str(model_output_dir),
            "--workspace-root", str(workspace_root),
            "--timeout-seconds", "3000",
            "--repeat", str(repeat),
            "--instruction-role", "system",
        ]
        run_benchmark_command(cmd, bench_log)


def ensure_qwopus_present(output_root: Path) -> dict[str, object]:
    transfer_dir = output_root / "transfer"
    transfer_dir.mkdir(parents=True, exist_ok=True)
    target = Path(QWOPUS_REMOTE_PATH)
    if not target.exists():
        raise FileNotFoundError(QWOPUS_REMOTE_PATH)
    payload = {
        "target": str(target),
        "downloaded": False,
        "size_bytes": target.stat().st_size,
        "sha256": file_sha256(target),
    }
    (transfer_dir / "remote_download_meta.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18343/v1")
    parser.add_argument("--api-key", default="sk-no-key-required")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--wait-timeout-seconds", type=int, default=420)
    parser.add_argument("--agentic-repeat", type=int, default=2)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    summary_dir = output_root / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    download_meta = ensure_qwopus_present(output_root)
    (summary_dir / "download_meta.json").write_text(json.dumps(download_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    bench_backup_path = f"{BENCH_RUN_SCRIPT}.bench-{output_root.name}.bak"
    startup_metrics: dict[str, list[dict[str, object]]] = {"64k": [], "262k": [], "agentic": []}

    try:
        sudo_local(f"systemctl stop {LIVE_SERVICE}", capture=False)
        sudo_local(f"systemctl stop {BENCH_SERVICE}", capture=False)
        sudo_local(f"systemctl reset-failed {BENCH_SERVICE} || true", capture=False)

        for model in MODELS:
            started = time.perf_counter()
            startup = switch_model(args.base_url, args.api_key, model, SERVER_ARGS_64K, bench_backup_path, args.wait_timeout_seconds)
            startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
            startup_metrics["64k"].append(startup)
            run_coding_round(repo_root, output_root / "64k", args.base_url, args.api_key, model["model_key"], model["model_alias"], "64k-coding-v3", ["java", "ts", "script"])

        for model in MODELS:
            started = time.perf_counter()
            startup = switch_model(args.base_url, args.api_key, model, SERVER_ARGS_262K, bench_backup_path, args.wait_timeout_seconds)
            startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
            startup_metrics["262k"].append(startup)
            run_coding_round(repo_root, output_root / "262k", args.base_url, args.api_key, model["model_key"], model["model_alias"], "262k-extreme-v3", ["extreme"])

        for model in MODELS:
            started = time.perf_counter()
            startup = switch_model(args.base_url, args.api_key, model, SERVER_ARGS_64K, bench_backup_path, args.wait_timeout_seconds)
            startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
            startup_metrics["agentic"].append(startup)
            run_agentic_round(repo_root, output_root / "agentic", args.base_url, args.api_key, model["model_key"], model["model_alias"], args.agentic_repeat)
    finally:
        restore_bench_run_script(bench_backup_path)
        sudo_local(f"systemctl stop {BENCH_SERVICE}", capture=False)
        sudo_local(f"systemctl start {LIVE_SERVICE}", capture=False)

    (summary_dir / "startup_metrics.json").write_text(json.dumps(startup_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
