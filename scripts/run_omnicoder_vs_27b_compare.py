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
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT = "project-d4e4f88c-f262-47af-b5b"
ZONE = "us-central1-a"
INSTANCE = "instance-20260222-145427"
REMOTE_HOST = "100.107.189.100"
REMOTE_USER = "hhtele"
REMOTE_PASSWORD = "hhtele"

REMOTE_RUN_SCRIPT = "/opt/llama.cpp/run-openclaw-executor.sh"
REMOTE_SERVICE = "openclaw-executor"
LIVE_SERVICE = "qwen35-35b-a3b-uncensored"
LIVE_ALIAS = "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M"

OMNICODER_MODELSCOPE_REPO = "Tesslate/OmniCoder-9B-GGUF"
OMNICODER_FILENAME = "omnicoder-9b-q8_0.gguf"
OMNICODER_REMOTE_PATH = "/data/models/qwen/omnicoder-9b-q8_0.gguf"

FAIR_SERVER_ARGS_64K = [
    "-ngl 99",
    "-c 65536",
    "-np 1",
    "-fa on",
    "-ctk q4_0",
    "-ctv q4_0",
    "--temp 0.6",
    "--top-p 0.95",
    "--top-k 20",
    "--min-p 0.0",
    """--chat-template-kwargs '{"enable_thinking": true}'""",
    "--host 0.0.0.0",
    "--port 18343",
]

FAIR_SERVER_ARGS_262K = [
    "-ngl 99",
    "-c 262144",
    "-np 1",
    "-fa on",
    "-ctk q4_0",
    "-ctv q4_0",
    "--temp 0.6",
    "--top-p 0.95",
    "--top-k 20",
    "--min-p 0.0",
    """--chat-template-kwargs '{"enable_thinking": true}'""",
    "--host 0.0.0.0",
    "--port 18343",
]

TUNED_AGENTIC_ARGS_64K = [
    "-ngl 99",
    "-c 65536",
    "-np 1",
    "-fa on",
    "-ctk q4_0",
    "-ctv q4_0",
    "--temp 0.3",
    "--top-p 0.95",
    "--top-k 20",
    "--min-p 0.0",
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
        "model_key": "omnicoder_9b_q8_0",
        "model_alias": "bench/omnicoder-9b-q8_0",
        "model_path": OMNICODER_REMOTE_PATH,
    },
]

OMNICODER_TUNED = {
    "model_key": "omnicoder_9b_q8_0_tuned",
    "model_alias": "bench/omnicoder-9b-q8_0-tuned",
    "model_path": OMNICODER_REMOTE_PATH,
}

REPO_REASONING_TASK_IDS = [
    "java_outbox_publish_before_commit",
    "java_retry_duplicate_side_effect",
    "ts_boot_restore_consistency",
    "ts_reconnect_circuit_breaker",
    "ts_runtime_metrics_protocol",
    "ts_build_atomic_write_guard",
]

ARTIFACT_DELIVERY_TASK_IDS = [
    "agentic_ts_metrics_contract_patch",
    "agentic_ts_restore_bootstrap_patch",
    "agentic_bash_log_triage_gz",
    "agentic_python_replay_analyzer_patch",
]

MAIN_AGENTIC_TASK_IDS = [
    "agentic_python_reconcile_pkg",
    "agentic_python_restore_bootstrap",
    "agentic_python_metrics_contract",
    "agentic_bash_log_triage",
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


def sudo_remote(command: str, *, capture: bool = True) -> str:
    wrapped = (
        "printf '%s\\n' {password} | sudo -S -p '' bash -lc {command}".format(
            password=shlex.quote(REMOTE_PASSWORD),
            command=shlex.quote(command),
        )
    )
    return run_remote(wrapped, capture=capture)


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def load_existing_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_modelscope_file() -> dict[str, Any]:
    url = f"https://www.modelscope.cn/api/v1/models/{OMNICODER_MODELSCOPE_REPO}/repo/files"
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    files = payload["Data"]["Files"]
    for item in files:
        if item["Name"] == OMNICODER_FILENAME:
            return {
                "repo": OMNICODER_MODELSCOPE_REPO,
                "name": item["Name"],
                "path": item["Path"],
                "size": item["Size"],
                "sha256": item["Sha256"],
                "revision": item["Revision"],
                "resolve_url": f"https://www.modelscope.cn/models/{OMNICODER_MODELSCOPE_REPO}/resolve/master/{item['Path']}",
            }
    raise RuntimeError(f"Did not find {OMNICODER_FILENAME} in {OMNICODER_MODELSCOPE_REPO}")


def ensure_remote_omnicoder(file_meta: dict[str, Any], summary_dir: Path) -> dict[str, Any]:
    remote_dir = str(Path(OMNICODER_REMOTE_PATH).parent)
    remote_log = f"{remote_dir}/omnicoder-9b-q8_0.download.log"
    remote_json = f"{remote_dir}/omnicoder-9b-q8_0.download.json"
    sudo_remote(f"mkdir -p {shlex.quote(remote_dir)}", capture=False)
    size = int(file_meta["size"])
    sha256 = file_meta["sha256"]

    check_script = f"""
python3 - <<'PY'
import hashlib, json
from pathlib import Path
path = Path({OMNICODER_REMOTE_PATH!r})
expected_size = {size}
expected_sha = {sha256!r}
result = {{"exists": path.exists(), "path": str(path)}}
if path.exists():
    stat = path.stat()
    result["size"] = stat.st_size
    if stat.st_size == expected_size:
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        result["sha256"] = h.hexdigest()
        result["ok"] = result["sha256"] == expected_sha
    else:
        result["ok"] = False
print(json.dumps(result, ensure_ascii=False))
PY
""".strip()
    current = json.loads(run_remote(check_script))
    if current.get("ok"):
        save_json(summary_dir / "download.json", {"source": file_meta, "remote": current, "downloaded": False})
        return current

    download_cmd = f"""
set -euo pipefail
cd {shlex.quote(remote_dir)}
aria2c --continue=true --file-allocation=none --max-connection-per-server=16 --split=16 --min-split-size=10M \\
  -o {shlex.quote(Path(OMNICODER_REMOTE_PATH).name)} \\
  {shlex.quote(file_meta['resolve_url'])} > {shlex.quote(remote_log)} 2>&1
python3 - <<'PY'
import hashlib, json
from pathlib import Path
path = Path({OMNICODER_REMOTE_PATH!r})
h = hashlib.sha256()
with path.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        h.update(chunk)
payload = {{
    "path": str(path),
    "size": path.stat().st_size,
    "sha256": h.hexdigest(),
}}
Path({remote_json!r}).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
PY
""".strip()
    result = json.loads(run_remote(download_cmd))
    save_json(summary_dir / "download.json", {"source": file_meta, "remote": result, "downloaded": True})
    if result["size"] != size or result["sha256"] != sha256:
        raise RuntimeError(f"Downloaded OmniCoder checksum mismatch: {result}")
    return result


def make_run_script(model_path: str, model_alias: str, server_args: list[str]) -> str:
    args = " \\\n  ".join(server_args)
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
        scp_to_jump(temp_path, "/tmp/run-omnicoder-bench.sh")
    finally:
        temp_path.unlink(missing_ok=True)

    remote_block = """
sshpass -p {password} scp -o StrictHostKeyChecking=no /tmp/run-omnicoder-bench.sh {user}@{host}:/tmp/run-omnicoder-bench.sh
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
                    "cp /tmp/run-omnicoder-bench.sh {current}; "
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
    sudo_remote(
        "if test -f {backup}; then "
        "cp {backup} {current}; chmod +x {current}; "
        "fi".format(
            backup=shlex.quote(backup_path),
            current=shlex.quote(REMOTE_RUN_SCRIPT),
        ),
        capture=False,
    )


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


@contextmanager
def capture_round_artifacts(model_output_dir: Path, model_key: str, round_key: str):
    started_at_epoch = int(run_remote("date +%s").strip())
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
        yield
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
        try:
            run_remote(
                "rm -f {paths}".format(
                    paths=" ".join(
                        shlex.quote(path)
                        for path in [gpu_remote, vmstat_remote, free_before_remote, free_after_remote]
                    )
                )
            )
        except Exception as exc:
            errors.append(f"cleanup_remote_artifacts: {exc!r}")
        if errors:
            write_text(model_output_dir / "artifact_capture_errors.log", "\n".join(errors) + "\n")


def run_benchmark_command(cmd: list[str], log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as handle:
        subprocess.run(cmd, check=True, text=True, stdout=handle, stderr=subprocess.STDOUT)


def switch_model(
    base_url: str,
    api_key: str,
    model_path: str,
    model_alias: str,
    server_args: list[str],
    backup_path: str,
    wait_timeout_seconds: int,
) -> dict[str, Any]:
    install_run_script(make_run_script(model_path, model_alias, server_args), backup_path)
    wait_for_model(base_url, api_key, model_alias, wait_timeout_seconds)
    return {
        "timestamp_utc": utc_now(),
        "model_alias": model_alias,
        "model_path": model_path,
        "server_args": server_args,
        "idle_gpu": remote_gpu_snapshot(),
    }


def run_coding_round(
    repo_root: Path,
    output_dir: Path,
    base_url: str,
    api_key: str,
    model_key: str,
    model_alias: str,
    benchmark_profile: str,
    server_args: list[str],
    *,
    task_ids: list[str] | None = None,
    families: list[str] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with capture_round_artifacts(output_dir, model_key, benchmark_profile):
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
            str(output_dir),
            "--repo-root",
            str(repo_root),
            "--timeout-seconds",
            "3000",
            "--repeat",
            "1",
            "--network-retries",
            "1",
            "--benchmark-profile",
            benchmark_profile,
            "--server-args",
            " ".join(server_args),
        ]
        for family in families or []:
            cmd.extend(["--family", family])
        for task_id in task_ids or []:
            cmd.extend(["--task-id", task_id])
        run_benchmark_command(cmd, output_dir / "bench.log")


def run_agentic_round(
    repo_root: Path,
    output_dir: Path,
    workspace_root: Path,
    base_url: str,
    api_key: str,
    model_key: str,
    model_alias: str,
    repeat: int,
    round_key: str,
    *,
    task_ids: list[str] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    workspace_root.mkdir(parents=True, exist_ok=True)
    with capture_round_artifacts(output_dir, model_key, round_key):
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
            str(output_dir),
            "--workspace-root",
            str(workspace_root),
            "--timeout-seconds",
            "3000",
            "--repeat",
            str(repeat),
            "--instruction-role",
            "system",
        ]
        for task_id in task_ids or []:
            cmd.extend(["--task-id", task_id])
        run_benchmark_command(cmd, output_dir / "bench.log")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--wait-timeout-seconds", type=int, default=420)
    parser.add_argument("--agentic-repeat", type=int, default=2)
    parser.add_argument(
        "--phases",
        nargs="+",
        choices=["all", "64k", "262k", "agentic", "agentic_extension", "tuned"],
        default=["all"],
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    summary_dir = output_root / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    file_meta = fetch_modelscope_file()
    save_json(summary_dir / "download_source.json", file_meta)
    ensure_remote_omnicoder(file_meta, summary_dir)

    backup_path = f"{REMOTE_RUN_SCRIPT}.bench-{output_root.name}.bak"
    startup_metrics: dict[str, list[dict[str, Any]]] = load_existing_json(summary_dir / "startup_metrics.json") or {
        "64k": [],
        "262k": [],
        "agentic": [],
        "agentic_extension_repo": [],
        "agentic_extension_artifact": [],
        "agentic_tuned": [],
        "agentic_extension_repo_tuned": [],
        "agentic_extension_artifact_tuned": [],
    }
    selected_phases = set(args.phases)
    if "all" in selected_phases:
        selected_phases = {"64k", "262k", "agentic", "agentic_extension", "tuned"}
    if "64k" in selected_phases:
        startup_metrics["64k"] = []
    if "262k" in selected_phases:
        startup_metrics["262k"] = []
    if "agentic" in selected_phases:
        startup_metrics["agentic"] = []
    if "agentic_extension" in selected_phases:
        startup_metrics["agentic_extension_repo"] = []
        startup_metrics["agentic_extension_artifact"] = []
    if "tuned" in selected_phases:
        startup_metrics["agentic_tuned"] = []
        startup_metrics["agentic_extension_repo_tuned"] = []
        startup_metrics["agentic_extension_artifact_tuned"] = []

    try:
        sudo_remote(f"systemctl stop {LIVE_SERVICE}", capture=False)
        sudo_remote(f"systemctl stop {REMOTE_SERVICE}", capture=False)

        # same-param 64k coding
        if "64k" in selected_phases:
            for model in MODELS:
                started = time.perf_counter()
                startup = switch_model(
                    args.base_url,
                    args.api_key,
                    model["model_path"],
                    model["model_alias"],
                    FAIR_SERVER_ARGS_64K,
                    backup_path,
                    args.wait_timeout_seconds,
                )
                startup["model_key"] = model["model_key"]
                startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
                startup_metrics["64k"].append(startup)
                run_coding_round(
                    repo_root,
                    output_root / "64k" / model["model_key"],
                    args.base_url,
                    args.api_key,
                    model["model_key"],
                    model["model_alias"],
                    "omnicoder-vs-27b-64k",
                    FAIR_SERVER_ARGS_64K,
                    families=["java", "ts", "script"],
                )

        # same-param 262k extreme
        if "262k" in selected_phases:
            for model in MODELS:
                started = time.perf_counter()
                startup = switch_model(
                    args.base_url,
                    args.api_key,
                    model["model_path"],
                    model["model_alias"],
                    FAIR_SERVER_ARGS_262K,
                    backup_path,
                    args.wait_timeout_seconds,
                )
                startup["model_key"] = model["model_key"]
                startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
                startup_metrics["262k"].append(startup)
                run_coding_round(
                    repo_root,
                    output_root / "262k" / model["model_key"],
                    args.base_url,
                    args.api_key,
                    model["model_key"],
                    model["model_alias"],
                    "omnicoder-vs-27b-262k",
                    FAIR_SERVER_ARGS_262K,
                    families=["extreme"],
                )

        # same-param agentic
        if "agentic" in selected_phases:
            for model in MODELS:
                started = time.perf_counter()
                startup = switch_model(
                    args.base_url,
                    args.api_key,
                    model["model_path"],
                    model["model_alias"],
                    FAIR_SERVER_ARGS_64K,
                    backup_path,
                    args.wait_timeout_seconds,
                )
                startup["model_key"] = model["model_key"]
                startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
                startup_metrics["agentic"].append(startup)
                run_agentic_round(
                    repo_root,
                    output_root / "agentic" / model["model_key"],
                    output_root / "agentic" / "workspaces",
                    args.base_url,
                    args.api_key,
                    model["model_key"],
                    model["model_alias"],
                    args.agentic_repeat,
                    "agentic-main",
                    task_ids=MAIN_AGENTIC_TASK_IDS,
                )

        # same-param extension repo reasoning
        if "agentic_extension" in selected_phases:
            for model in MODELS:
                started = time.perf_counter()
                startup = switch_model(
                    args.base_url,
                    args.api_key,
                    model["model_path"],
                    model["model_alias"],
                    FAIR_SERVER_ARGS_64K,
                    backup_path,
                    args.wait_timeout_seconds,
                )
                startup["model_key"] = model["model_key"]
                startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
                startup_metrics["agentic_extension_repo"].append(startup)
                run_coding_round(
                    repo_root,
                    output_root / "agentic-extension" / "repo_reasoning" / model["model_key"],
                    args.base_url,
                    args.api_key,
                    model["model_key"],
                    model["model_alias"],
                    "omnicoder-vs-27b-agentic-repo",
                    FAIR_SERVER_ARGS_64K,
                    task_ids=REPO_REASONING_TASK_IDS,
                )

        # same-param extension artifact delivery
            for model in MODELS:
                started = time.perf_counter()
                startup = switch_model(
                    args.base_url,
                    args.api_key,
                    model["model_path"],
                    model["model_alias"],
                    FAIR_SERVER_ARGS_64K,
                    backup_path,
                    args.wait_timeout_seconds,
                )
                startup["model_key"] = model["model_key"]
                startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
                startup_metrics["agentic_extension_artifact"].append(startup)
                run_agentic_round(
                    repo_root,
                    output_root / "agentic-extension" / "artifact_delivery" / model["model_key"],
                    output_root / "agentic-extension" / "artifact_delivery" / "workspaces",
                    args.base_url,
                    args.api_key,
                    model["model_key"],
                    model["model_alias"],
                    1,
                    "agentic-ext-artifact",
                    task_ids=ARTIFACT_DELIVERY_TASK_IDS,
                )

        # tuned OmniCoder main agentic
        if "tuned" in selected_phases:
            started = time.perf_counter()
            startup = switch_model(
                args.base_url,
                args.api_key,
                OMNICODER_TUNED["model_path"],
                OMNICODER_TUNED["model_alias"],
                TUNED_AGENTIC_ARGS_64K,
                backup_path,
                args.wait_timeout_seconds,
            )
            startup["model_key"] = OMNICODER_TUNED["model_key"]
            startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
            startup_metrics["agentic_tuned"].append(startup)
            run_agentic_round(
                repo_root,
                output_root / "agentic-tuned" / OMNICODER_TUNED["model_key"],
                output_root / "agentic-tuned" / "workspaces",
                args.base_url,
                args.api_key,
                OMNICODER_TUNED["model_key"],
                OMNICODER_TUNED["model_alias"],
                args.agentic_repeat,
                "agentic-main-tuned",
                task_ids=MAIN_AGENTIC_TASK_IDS,
            )

        # tuned OmniCoder extension repo reasoning
            started = time.perf_counter()
            startup = switch_model(
                args.base_url,
                args.api_key,
                OMNICODER_TUNED["model_path"],
                OMNICODER_TUNED["model_alias"],
                TUNED_AGENTIC_ARGS_64K,
                backup_path,
                args.wait_timeout_seconds,
            )
            startup["model_key"] = OMNICODER_TUNED["model_key"]
            startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
            startup_metrics["agentic_extension_repo_tuned"].append(startup)
            run_coding_round(
                repo_root,
                output_root / "agentic-extension-tuned" / "repo_reasoning" / OMNICODER_TUNED["model_key"],
                args.base_url,
                args.api_key,
                OMNICODER_TUNED["model_key"],
                OMNICODER_TUNED["model_alias"],
                "omnicoder-agentic-repo-tuned",
                TUNED_AGENTIC_ARGS_64K,
                task_ids=REPO_REASONING_TASK_IDS,
            )

        # tuned OmniCoder extension artifact delivery
            started = time.perf_counter()
            startup = switch_model(
                args.base_url,
                args.api_key,
                OMNICODER_TUNED["model_path"],
                OMNICODER_TUNED["model_alias"],
                TUNED_AGENTIC_ARGS_64K,
                backup_path,
                args.wait_timeout_seconds,
            )
            startup["model_key"] = OMNICODER_TUNED["model_key"]
            startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
            startup_metrics["agentic_extension_artifact_tuned"].append(startup)
            run_agentic_round(
                repo_root,
                output_root / "agentic-extension-tuned" / "artifact_delivery" / OMNICODER_TUNED["model_key"],
                output_root / "agentic-extension-tuned" / "artifact_delivery" / "workspaces",
                args.base_url,
                args.api_key,
                OMNICODER_TUNED["model_key"],
                OMNICODER_TUNED["model_alias"],
                1,
                "agentic-ext-artifact-tuned",
                task_ids=ARTIFACT_DELIVERY_TASK_IDS,
            )
    finally:
        restore_run_script(backup_path)
        sudo_remote(f"systemctl stop {REMOTE_SERVICE}", capture=False)
        sudo_remote(f"systemctl start {LIVE_SERVICE}", capture=False)
        wait_for_model(args.base_url, args.api_key, LIVE_ALIAS, args.wait_timeout_seconds)

    save_json(summary_dir / "startup_metrics.json", startup_metrics)

    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_qwen_model_compare_report.py"),
            "--baseline-results",
            str(output_root / "64k" / MODELS[0]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "64k" / MODELS[1]["model_key"] / "results.csv"),
            "--baseline-key",
            MODELS[0]["model_key"],
            "--candidate-key",
            MODELS[1]["model_key"],
            "--baseline-name",
            MODELS[0]["model_alias"],
            "--candidate-name",
            MODELS[1]["model_alias"],
            "--output-md",
            str(summary_dir / "64k_compare_report.md"),
        ],
        check=True,
        text=True,
    )
    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_qwen_model_compare_report.py"),
            "--baseline-results",
            str(output_root / "262k" / MODELS[0]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "262k" / MODELS[1]["model_key"] / "results.csv"),
            "--baseline-key",
            MODELS[0]["model_key"],
            "--candidate-key",
            MODELS[1]["model_key"],
            "--baseline-name",
            MODELS[0]["model_alias"],
            "--candidate-name",
            MODELS[1]["model_alias"],
            "--output-md",
            str(summary_dir / "262k_compare_report.md"),
        ],
        check=True,
        text=True,
    )
    subprocess.run(
        [
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
        ],
        check=True,
        text=True,
    )
    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_qwen_model_compare_report.py"),
            "--baseline-results",
            str(output_root / "agentic-extension" / "repo_reasoning" / MODELS[0]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "agentic-extension" / "repo_reasoning" / MODELS[1]["model_key"] / "results.csv"),
            "--baseline-key",
            MODELS[0]["model_key"],
            "--candidate-key",
            MODELS[1]["model_key"],
            "--baseline-name",
            MODELS[0]["model_alias"],
            "--candidate-name",
            MODELS[1]["model_alias"],
            "--output-md",
            str(summary_dir / "agentic_extension_repo_compare_report.md"),
        ],
        check=True,
        text=True,
    )
    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_qwen_agentic_compare_report.py"),
            "--baseline-results",
            str(output_root / "agentic-extension" / "artifact_delivery" / MODELS[0]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "agentic-extension" / "artifact_delivery" / MODELS[1]["model_key"] / "results.csv"),
            "--baseline-key",
            MODELS[0]["model_key"],
            "--candidate-key",
            MODELS[1]["model_key"],
            "--baseline-name",
            MODELS[0]["model_alias"],
            "--candidate-name",
            MODELS[1]["model_alias"],
            "--output-md",
            str(summary_dir / "agentic_extension_artifact_compare_report.md"),
            "--output-json",
            str(summary_dir / "agentic_extension_artifact_compare_summary.json"),
        ],
        check=True,
        text=True,
    )
    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_qwen_agentic_compare_report.py"),
            "--baseline-results",
            str(output_root / "agentic" / MODELS[1]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "agentic-tuned" / OMNICODER_TUNED["model_key"] / "results.csv"),
            "--baseline-key",
            MODELS[1]["model_key"],
            "--candidate-key",
            OMNICODER_TUNED["model_key"],
            "--baseline-name",
            MODELS[1]["model_alias"],
            "--candidate-name",
            OMNICODER_TUNED["model_alias"],
            "--output-md",
            str(summary_dir / "agentic_tuned_appendix_report.md"),
            "--output-json",
            str(summary_dir / "agentic_tuned_appendix_summary.json"),
        ],
        check=True,
        text=True,
    )
    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_qwen_model_compare_report.py"),
            "--baseline-results",
            str(output_root / "agentic-extension" / "repo_reasoning" / MODELS[1]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "agentic-extension-tuned" / "repo_reasoning" / OMNICODER_TUNED["model_key"] / "results.csv"),
            "--baseline-key",
            MODELS[1]["model_key"],
            "--candidate-key",
            OMNICODER_TUNED["model_key"],
            "--baseline-name",
            MODELS[1]["model_alias"],
            "--candidate-name",
            OMNICODER_TUNED["model_alias"],
            "--output-md",
            str(summary_dir / "agentic_extension_repo_tuned_appendix_report.md"),
        ],
        check=True,
        text=True,
    )
    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_qwen_agentic_compare_report.py"),
            "--baseline-results",
            str(output_root / "agentic-extension" / "artifact_delivery" / MODELS[1]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "agentic-extension-tuned" / "artifact_delivery" / OMNICODER_TUNED["model_key"] / "results.csv"),
            "--baseline-key",
            MODELS[1]["model_key"],
            "--candidate-key",
            OMNICODER_TUNED["model_key"],
            "--baseline-name",
            MODELS[1]["model_alias"],
            "--candidate-name",
            OMNICODER_TUNED["model_alias"],
            "--output-md",
            str(summary_dir / "agentic_extension_artifact_tuned_appendix_report.md"),
            "--output-json",
            str(summary_dir / "agentic_extension_artifact_tuned_appendix_summary.json"),
        ],
        check=True,
        text=True,
    )

    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_omnicoder_vs_27b_report.py"),
            "--baseline-key",
            MODELS[0]["model_key"],
            "--candidate-key",
            MODELS[1]["model_key"],
            "--baseline-name",
            MODELS[0]["model_alias"],
            "--candidate-name",
            MODELS[1]["model_alias"],
            "--64k-baseline-results",
            str(output_root / "64k" / MODELS[0]["model_key"] / "results.csv"),
            "--64k-candidate-results",
            str(output_root / "64k" / MODELS[1]["model_key"] / "results.csv"),
            "--262k-baseline-results",
            str(output_root / "262k" / MODELS[0]["model_key"] / "results.csv"),
            "--262k-candidate-results",
            str(output_root / "262k" / MODELS[1]["model_key"] / "results.csv"),
            "--agentic-summary-json",
            str(summary_dir / "agentic_compare_summary.json"),
            "--extension-repo-baseline-results",
            str(output_root / "agentic-extension" / "repo_reasoning" / MODELS[0]["model_key"] / "results.csv"),
            "--extension-repo-candidate-results",
            str(output_root / "agentic-extension" / "repo_reasoning" / MODELS[1]["model_key"] / "results.csv"),
            "--extension-artifact-summary-json",
            str(summary_dir / "agentic_extension_artifact_compare_summary.json"),
            "--tuned-agentic-summary-json",
            str(summary_dir / "agentic_tuned_appendix_summary.json"),
            "--tuned-extension-repo-baseline-results",
            str(output_root / "agentic-extension" / "repo_reasoning" / MODELS[1]["model_key"] / "results.csv"),
            "--tuned-extension-repo-candidate-results",
            str(output_root / "agentic-extension-tuned" / "repo_reasoning" / OMNICODER_TUNED["model_key"] / "results.csv"),
            "--tuned-extension-artifact-summary-json",
            str(summary_dir / "agentic_extension_artifact_tuned_appendix_summary.json"),
            "--startup-metrics-json",
            str(summary_dir / "startup_metrics.json"),
            "--download-json",
            str(summary_dir / "download.json"),
            "--output-md",
            str(summary_dir / "final_report.md"),
            "--output-json",
            str(summary_dir / "final_report.json"),
        ],
        check=True,
        text=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
