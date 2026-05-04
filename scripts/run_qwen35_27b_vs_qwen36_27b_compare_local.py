#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
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

MODELSCOPE_REPO = "unsloth/Qwen3.6-27B-GGUF"
MODELSCOPE_FILE = "Qwen3.6-27B-UD-Q5_K_XL.gguf"
REMOTE_MODEL_DIR = "/data/models/qwen"
REMOTE_DOWNLOAD_DIR = f"{REMOTE_MODEL_DIR}/.downloads/qwen36-27b-q5xl"
REMOTE_QWEN36_PATH = f"{REMOTE_MODEL_DIR}/{MODELSCOPE_FILE}"

BENCH_RUN_SCRIPT = "/opt/llama.cpp/run-openclaw-executor.sh"
BENCH_SERVICE = "openclaw-executor"
LIVE_SERVICE = "qwen35-35b-a3b-uncensored"
LIVE_ALIAS = "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M"
LLAMA_SERVER_BIN = "/opt/llama.cpp/build/bin/llama-server"

BASELINE = {
    "model_key": "qwen35_27b_ud_q4_xl",
    "model_alias": "bench/qwen35-27b-ud-q4_xl",
    "model_path": f"{REMOTE_MODEL_DIR}/Qwen3.5-27B-UD-Q4_K_XL.gguf",
    "display_name": "Qwen3.5-27B-UD-Q4_K_XL",
}
CANDIDATE = {
    "model_key": "qwen36_27b_ud_q5_xl",
    "model_alias": "bench/qwen36-27b-ud-q5_xl",
    "model_path": REMOTE_QWEN36_PATH,
    "display_name": "Qwen3.6-27B-UD-Q5_K_XL",
}
MODELS = [BASELINE, CANDIDATE]

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

SERVER_ARGS_128K = [
    arg.replace("-c 65536", "-c 131072") if arg == "-c 65536" else arg
    for arg in SERVER_ARGS_64K
]

SERVER_ARGS_262K = [
    arg.replace("-c 65536", "-c 262144") if arg == "-c 65536" else arg
    for arg in SERVER_ARGS_64K
]

SERVER_ARGS_THINKING_64K = [
    arg
    for arg in SERVER_ARGS_64K
    if arg != "--reasoning-format none"
    and """--chat-template-kwargs '{"enable_thinking": false}'""" not in arg
] + ["""--chat-template-kwargs '{"enable_thinking": true}'"""]

SERVER_ARGS_THINKING_128K = [
    arg.replace("-c 65536", "-c 131072") if arg == "-c 65536" else arg
    for arg in SERVER_ARGS_THINKING_64K
]

NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


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
        completed = subprocess.run(cmd, check=False, text=True, capture_output=capture)
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
    nested = "sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {command}".format(
        password=shlex.quote(REMOTE_PASSWORD),
        user=REMOTE_USER,
        host=REMOTE_HOST,
        command=shlex.quote(command),
    )
    return run_jump(nested, capture=capture)


def sudo_remote(command: str, *, capture: bool = True) -> str:
    wrapped = "printf '%s\\n' {password} | sudo -S -p '' bash -lc {command}".format(
        password=shlex.quote(REMOTE_PASSWORD),
        command=shlex.quote(command),
    )
    return run_remote(wrapped, capture=capture)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def fetch_remote_text(remote_path: str, local_path: Path) -> None:
    write_text(local_path, run_remote(f"cat {shlex.quote(remote_path)}"))


def scp_script_to_remote(script_text: str, jump_path: str, remote_path: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(script_text)
    try:
        scp_to_jump(temp_path, jump_path)
    finally:
        temp_path.unlink(missing_ok=True)

    run_jump(
        "sshpass -p {password} scp -o StrictHostKeyChecking=no {jump_path} {user}@{host}:{remote_path}".format(
            password=shlex.quote(REMOTE_PASSWORD),
            jump_path=shlex.quote(jump_path),
            user=REMOTE_USER,
            host=REMOTE_HOST,
            remote_path=shlex.quote(remote_path),
        ),
        capture=False,
    )


def wait_for_model(base_url: str, api_key: str, expected_alias: str, timeout_seconds: int) -> None:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        try:
            request = urllib.request.Request(
                f"{base_url.rstrip('/')}/models",
                headers=headers,
                method="GET",
            )
            with NO_PROXY_OPENER.open(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            aliases = [item.get("id") for item in payload.get("data", [])]
            if expected_alias in aliases:
                return
            last_error = f"aliases={aliases}"
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(3)
    raise TimeoutError(f"Timed out waiting for {expected_alias}: {last_error}")


def wait_service_state(service_name: str, target: str, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        state = run_remote(f"systemctl is-active {shlex.quote(service_name)} || true").strip().splitlines()[-1]
        if target == "inactive":
            if state not in {"active", "activating", "deactivating", "reloading"}:
                return
        elif state == target:
            return
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for {service_name} to become {target}")


def wait_port_release(port: int = 18343, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        listening = run_remote(f"ss -ltn '( sport = :{port} )' | awk 'NR>1 {{print $4}}' || true").strip()
        if not listening:
            return
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for port {port} release")


def stop_service(service_name: str) -> None:
    sudo_remote(f"systemctl stop --no-block {shlex.quote(service_name)}", capture=False)
    wait_service_state(service_name, "inactive")
    try:
        wait_port_release(18343, timeout_seconds=45)
    except TimeoutError:
        sudo_remote(f"systemctl kill -s SIGKILL {shlex.quote(service_name)} || true", capture=False)
        run_remote("pkill -9 -f 'llama-server.*--port 18343' >/dev/null 2>&1 || true", capture=False)
        wait_port_release(18343, timeout_seconds=45)


def start_service(service_name: str) -> None:
    sudo_remote(f"systemctl start {shlex.quote(service_name)}", capture=False)
    wait_service_state(service_name, "active")


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


def make_run_script(model_path: str, model_alias: str, server_args: list[str]) -> str:
    args = (" \\" + "\n  ").join(server_args)
    return f"""#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${{LD_LIBRARY_PATH:-}}
exec {LLAMA_SERVER_BIN} \\
  -m {shlex.quote(model_path)} \\
  --alias {shlex.quote(model_alias)} \\
  {args}
"""


def install_run_script(script_text: str, backup_path: str) -> None:
    jump_path = "/tmp/run-qwen35-vs-qwen36-bench.sh"
    remote_path = "/tmp/run-qwen35-vs-qwen36-bench.sh"
    scp_script_to_remote(script_text, jump_path, remote_path)
    sudo_remote(
        "test -f {backup} || cp {current} {backup}; "
        "cp {remote} {current}; chmod +x {current}".format(
            backup=shlex.quote(backup_path),
            current=shlex.quote(BENCH_RUN_SCRIPT),
            remote=shlex.quote(remote_path),
        ),
        capture=False,
    )


def restore_run_script(backup_path: str) -> None:
    sudo_remote(
        "if test -f {backup}; then cp {backup} {current}; chmod +x {current}; fi".format(
            backup=shlex.quote(backup_path),
            current=shlex.quote(BENCH_RUN_SCRIPT),
        ),
        capture=False,
    )


def switch_model(
    base_url: str,
    api_key: str,
    model: dict[str, str],
    server_args: list[str],
    backup_path: str,
    wait_timeout_seconds: int,
) -> dict[str, Any]:
    install_run_script(make_run_script(model["model_path"], model["model_alias"], server_args), backup_path)
    sudo_remote(f"systemctl reset-failed {BENCH_SERVICE} || true", capture=False)
    sudo_remote(f"systemctl restart {BENCH_SERVICE}", capture=False)
    wait_for_model(base_url, api_key, model["model_alias"], wait_timeout_seconds)
    return {
        "timestamp_utc": utc_now(),
        "model_key": model["model_key"],
        "model_alias": model["model_alias"],
        "model_path": model["model_path"],
        "server_args": server_args,
        "idle_gpu": remote_gpu_snapshot(),
    }


def start_remote_logger(command: str) -> str:
    return run_remote(f"nohup bash -lc {shlex.quote(command)} >/dev/null 2>&1 & echo $!").strip()


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
        for command in [
            f"kill {gpu_pid} {vmstat_pid} >/dev/null 2>&1 || true",
            f"free -h > {shlex.quote(free_after_remote)}",
        ]:
            try:
                run_remote(command)
            except Exception as exc:
                errors.append(f"{command}: {exc!r}")
        time.sleep(2)
        for remote_path, local_name in [
            (gpu_remote, "gpu_samples.csv"),
            (vmstat_remote, "vmstat.log"),
            (free_before_remote, "free_before.log"),
            (free_after_remote, "free_after.log"),
        ]:
            try:
                fetch_remote_text(remote_path, model_output_dir / local_name)
            except Exception as exc:
                errors.append(f"fetch {remote_path}: {exc!r}")
        try:
            journal = run_remote(f"journalctl -u {BENCH_SERVICE} --since @{started_at_epoch} --no-pager")
            write_text(model_output_dir / "server.log", journal)
        except Exception as exc:
            errors.append(f"journal: {exc!r}")
            write_text(model_output_dir / "server.log", "")
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
            errors.append(f"cleanup: {exc!r}")
        if errors:
            write_text(model_output_dir / "artifact_capture_errors.log", "\n".join(errors) + "\n")


def run_benchmark_command(cmd: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        subprocess.run(cmd, check=True, text=True, stdout=handle, stderr=subprocess.STDOUT)


def send_chat_request(base_url: str, api_key: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    try:
        with NO_PROXY_OPENER.open(request, timeout=timeout_seconds) as response:
            raw = response.read()
            payload = json.loads(raw.decode("utf-8"))
            message = ((payload.get("choices") or [{}])[0].get("message") or {})
            return {
                "http_status": response.status,
                "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                "content_length": len(message.get("content") or ""),
                "reasoning_content_length": len(message.get("reasoning_content") or ""),
                "usage": payload.get("usage") or {},
                "content_preview": (message.get("content") or "")[:300],
                "reasoning_preview": (message.get("reasoning_content") or "")[:300],
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {
            "http_status": exc.code,
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "error": raw[:1000],
        }
    except Exception as exc:
        return {
            "http_status": 0,
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "error": repr(exc),
        }


def smoke_chat(
    base_url: str,
    api_key: str,
    model_alias: str,
    timeout_seconds: int,
    *,
    prompt_chars: int = 0,
) -> dict[str, Any]:
    content = "Reply READY only."
    if prompt_chars:
        content = ("A" * prompt_chars) + "\nReply READY only."
    payload = {
        "model": model_alias,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 96,
        "stream": False,
    }
    return send_chat_request(base_url, api_key, payload, timeout_seconds)


def run_coding_round(
    repo_root: Path,
    output_root: Path,
    base_url: str,
    api_key: str,
    model: dict[str, str],
    benchmark_profile: str,
    server_args: list[str],
    families: list[str],
) -> None:
    model_output_dir = output_root / model["model_key"]
    model_output_dir.mkdir(parents=True, exist_ok=True)
    with capture_round_artifacts(model_output_dir, model["model_key"], benchmark_profile):
        cmd = [
            "python3",
            str(repo_root / "scripts" / "qwen_model_compare_bench.py"),
            "--base-url", base_url,
            "--api-key", api_key,
            "--model", model["model_alias"],
            "--model-key", model["model_key"],
            "--instruction-role", "system",
            "--output-dir", str(model_output_dir),
            "--repo-root", str(repo_root),
            "--timeout-seconds", "3000",
            "--repeat", "1",
            "--network-retries", "1",
            "--benchmark-profile", benchmark_profile,
            "--server-args", " ".join(server_args),
        ]
        for family in families:
            cmd.extend(["--family", family])
        run_benchmark_command(cmd, model_output_dir / "bench.log")


def run_agentic_round(
    repo_root: Path,
    output_root: Path,
    base_url: str,
    api_key: str,
    model: dict[str, str],
    repeat: int,
) -> None:
    model_output_dir = output_root / model["model_key"]
    model_output_dir.mkdir(parents=True, exist_ok=True)
    workspace_root = output_root.parent / "workspaces"
    workspace_root.mkdir(parents=True, exist_ok=True)
    with capture_round_artifacts(model_output_dir, model["model_key"], "agentic"):
        cmd = [
            "python3",
            str(repo_root / "scripts" / "qwen_agentic_codegen_bench.py"),
            "--base-url", base_url,
            "--api-key", api_key,
            "--model", model["model_alias"],
            "--model-key", model["model_key"],
            "--output-dir", str(model_output_dir),
            "--workspace-root", str(workspace_root),
            "--timeout-seconds", "3000",
            "--repeat", str(repeat),
            "--instruction-role", "system",
        ]
        run_benchmark_command(cmd, model_output_dir / "bench.log")


def run_preflight(base_url: str, api_key: str) -> dict[str, Any]:
    outputs: dict[str, Any] = {"generated_at_utc": utc_now()}
    commands = {
        "nvidia_smi": "nvidia-smi",
        "df_models": f"df -h {shlex.quote(REMOTE_MODEL_DIR)}",
        "live_status": f"systemctl status {LIVE_SERVICE} --no-pager || true",
        "bench_status": f"systemctl status {BENCH_SERVICE} --no-pager || true",
        "models": "curl -s http://127.0.0.1:18343/v1/models || true",
    }
    for key, command in commands.items():
        outputs[key] = run_remote(command)
    try:
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            method="GET",
        )
        with NO_PROXY_OPENER.open(request, timeout=30) as response:
            outputs["local_models_proxy"] = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        outputs["local_models_proxy_error"] = repr(exc)
    return outputs


def remote_file_meta(path: str) -> dict[str, Any]:
    script = f"""
set -euo pipefail
test -f {shlex.quote(path)}
python3 - <<'PY'
import hashlib, json
from pathlib import Path
p = Path({path!r})
h = hashlib.sha256()
with p.open("rb") as fh:
    for chunk in iter(lambda: fh.read(1024 * 1024), b""):
        h.update(chunk)
print(json.dumps({{"path": str(p), "size": p.stat().st_size, "sha256": h.hexdigest()}}, ensure_ascii=False))
PY
"""
    return json.loads(run_remote(script).strip())


def download_qwen36_model(modelscope_token: str, output_root: Path) -> dict[str, Any]:
    downloader = r'''
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

repo = os.environ["MODELSCOPE_REPO"]
filename = os.environ["MODELSCOPE_FILE"]
target = Path(os.environ["REMOTE_QWEN36_PATH"])
download_dir = Path(os.environ["REMOTE_DOWNLOAD_DIR"])
token = os.environ["MODELSCOPE_TOKEN"]

api_url = f"https://www.modelscope.cn/api/v1/models/{repo}/repo/files?Revision=master&Recursive=true"
req = urllib.request.Request(api_url, headers={"Authorization": f"Bearer {token}"}, method="GET")
with urllib.request.urlopen(req, timeout=120) as response:
    api_payload = json.loads(response.read().decode("utf-8"))

files = (((api_payload.get("Data") or {}).get("Files")) or ((api_payload.get("data") or {}).get("files")) or [])
matches = [
    item for item in files
    if item.get("Name") == filename or item.get("name") == filename
    or str(item.get("Path") or item.get("path") or "").endswith("/" + filename)
    or str(item.get("Path") or item.get("path") or "") == filename
]
if len(matches) != 1:
    raise SystemExit(f"Expected exactly one {filename} in ModelScope metadata, got {len(matches)}")

item = matches[0]
path_in_repo = item.get("Path") or item.get("path") or filename
expected_size = int(item.get("Size") or item.get("size") or 0)
expected_sha = item.get("Sha256") or item.get("sha256") or item.get("SHA256") or ""
download_url = f"https://www.modelscope.cn/models/{repo}/resolve/master/{path_in_repo}"

download_dir.mkdir(parents=True, exist_ok=True)
target.parent.mkdir(parents=True, exist_ok=True)
tmp_path = download_dir / (filename + ".partial")
log_path = download_dir / (filename + ".aria2.log")

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

status = "already_present"
if not target.exists() or (expected_size and target.stat().st_size != expected_size):
    status = "downloaded"
    cmd = [
        "aria2c",
        "--continue=true",
        "--file-allocation=none",
        "--max-connection-per-server=16",
        "--split=16",
        "--min-split-size=10M",
        f"--header=Authorization: Bearer {token}",
        "--dir", str(download_dir),
        "--out", tmp_path.name,
        download_url,
    ]
    with log_path.open("w", encoding="utf-8") as log:
        subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT, text=True)
    if expected_size and tmp_path.stat().st_size != expected_size:
        raise SystemExit(f"Downloaded size mismatch: expected {expected_size}, got {tmp_path.stat().st_size}")
    os.replace(tmp_path, target)

actual_sha = sha256_of(target)
if expected_sha and actual_sha.lower() != expected_sha.lower():
    raise SystemExit(f"SHA256 mismatch: expected {expected_sha}, got {actual_sha}")
if expected_size and target.stat().st_size != expected_size:
    raise SystemExit(f"Target size mismatch: expected {expected_size}, got {target.stat().st_size}")

safe_item = {
    "name": item.get("Name") or item.get("name") or filename,
    "path": path_in_repo,
    "size": expected_size,
    "sha256": expected_sha,
    "revision": item.get("Revision") or item.get("revision"),
}
result = {
    "status": status,
    "repo_id": repo,
    "file": filename,
    "path": str(target),
    "size": target.stat().st_size,
    "sha256": actual_sha,
    "download_log": str(log_path) if log_path.exists() else "",
    "modelscope_file_meta": safe_item,
    "checksum_match": (not expected_sha or actual_sha.lower() == expected_sha.lower()) and (not expected_size or target.stat().st_size == expected_size),
}
print(json.dumps(result, ensure_ascii=False))
'''
    remote_script = "/tmp/qwen36_modelscope_downloader.py"
    scp_script_to_remote(downloader, "/tmp/qwen36_modelscope_downloader.py", remote_script)
    env = {
        "MODELSCOPE_TOKEN": modelscope_token,
        "MODELSCOPE_REPO": MODELSCOPE_REPO,
        "MODELSCOPE_FILE": MODELSCOPE_FILE,
        "REMOTE_QWEN36_PATH": REMOTE_QWEN36_PATH,
        "REMOTE_DOWNLOAD_DIR": REMOTE_DOWNLOAD_DIR,
    }
    exports = " ".join(f"{key}={shlex.quote(value)}" for key, value in env.items())
    raw = run_remote(f"{exports} python3 {shlex.quote(remote_script)}")
    result = json.loads(raw.strip().splitlines()[-1])
    transfer_dir = output_root / "transfer"
    save_json(transfer_dir / "modelscope_file_meta.json", result["modelscope_file_meta"])
    save_json(transfer_dir / "remote_download_meta.json", {k: v for k, v in result.items() if k != "modelscope_file_meta"})
    save_json(
        transfer_dir / "checksums.json",
        {
            "remote_size": result["size"],
            "remote_sha256": result["sha256"],
            "modelscope_size": result["modelscope_file_meta"].get("size"),
            "modelscope_sha256": result["modelscope_file_meta"].get("sha256"),
            "match": result["checksum_match"],
        },
    )
    save_json(output_root / "summary" / "download_meta.json", {k: v for k, v in result.items() if k != "modelscope_file_meta"})
    return result


def run_smoke_matrix(
    base_url: str,
    api_key: str,
    backup_path: str,
    wait_timeout_seconds: int,
    smoke_timeout_seconds: int,
    output_root: Path,
    startup_metrics: list[dict[str, Any]],
    run_profile: str,
) -> list[dict[str, Any]]:
    smoke_results: list[dict[str, Any]] = []
    matrix: list[tuple[str, dict[str, str], list[str], int]] = []
    if run_profile == "128k":
        for model in MODELS:
            matrix.append(("128k_short_no_think", model, SERVER_ARGS_128K, 0))
            matrix.append(("128k_20k_no_think", model, SERVER_ARGS_128K, 20000))
            matrix.append(("128k_short_thinking", model, SERVER_ARGS_THINKING_128K, 0))
    else:
        for model in MODELS:
            matrix.append(("64k_short_no_think", model, SERVER_ARGS_64K, 0))
            matrix.append(("64k_20k_no_think", model, SERVER_ARGS_64K, 20000))
            matrix.append(("64k_short_thinking", model, SERVER_ARGS_THINKING_64K, 0))
        matrix.append(("128k_short_no_think", CANDIDATE, SERVER_ARGS_128K, 0))

    for phase, model, server_args, prompt_chars in matrix:
        started = time.perf_counter()
        try:
            startup = switch_model(base_url, api_key, model, server_args, backup_path, wait_timeout_seconds)
            startup["phase"] = f"smoke:{phase}"
            startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
            startup_metrics.append(startup)
            result = smoke_chat(base_url, api_key, model["model_alias"], smoke_timeout_seconds, prompt_chars=prompt_chars)
            result.update(
                {
                    "phase": phase,
                    "model_key": model["model_key"],
                    "model_alias": model["model_alias"],
                    "prompt_chars": prompt_chars,
                    "server_args": server_args,
                    "success": result.get("http_status") == 200,
                }
            )
        except Exception as exc:
            result = {
                "phase": phase,
                "model_key": model["model_key"],
                "model_alias": model["model_alias"],
                "prompt_chars": prompt_chars,
                "server_args": server_args,
                "success": False,
                "error": repr(exc),
            }
        smoke_results.append(result)
        save_json(output_root / "smoke" / f"{model['model_key']}__{phase}.json", result)
    return smoke_results


def run_phase(
    *,
    phase: str,
    repo_root: Path,
    output_root: Path,
    base_url: str,
    api_key: str,
    backup_path: str,
    wait_timeout_seconds: int,
    startup_metrics: list[dict[str, Any]],
    agentic_repeat: int,
) -> None:
    if phase == "64k":
        server_args = SERVER_ARGS_64K
        benchmark_profile = "64k-coding-v3"
        families = ["java", "ts", "script"]
        phase_output_root = output_root / phase
    elif phase == "262k":
        server_args = SERVER_ARGS_262K
        benchmark_profile = "262k-extreme-v3"
        families = ["extreme"]
        phase_output_root = output_root / phase
    elif phase == "agentic":
        server_args = SERVER_ARGS_64K
        benchmark_profile = "agentic"
        families = []
        phase_output_root = output_root / phase
    elif phase == "128k-coding":
        server_args = SERVER_ARGS_128K
        benchmark_profile = "128k-coding-v1"
        families = ["java", "ts", "script"]
        phase_output_root = output_root / "128k" / "coding"
    elif phase == "128k-agentic":
        server_args = SERVER_ARGS_128K
        benchmark_profile = "128k-agentic"
        families = []
        phase_output_root = output_root / "128k" / "agentic"
    else:
        raise ValueError(phase)

    for model in MODELS:
        phase_dir = phase_output_root / model["model_key"]
        phase_dir.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        try:
            startup = switch_model(base_url, api_key, model, server_args, backup_path, wait_timeout_seconds)
            startup["phase"] = phase
            startup["startup_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
            startup_metrics.append(startup)
            if phase in {"agentic", "128k-agentic"}:
                run_agentic_round(repo_root, phase_output_root, base_url, api_key, model, agentic_repeat)
            else:
                run_coding_round(
                    repo_root,
                    phase_output_root,
                    base_url,
                    api_key,
                    model,
                    benchmark_profile,
                    server_args,
                    families,
                )
        except Exception as exc:
            failure = {
                "timestamp_utc": utc_now(),
                "phase": phase,
                "model_key": model["model_key"],
                "model_alias": model["model_alias"],
                "model_path": model["model_path"],
                "server_args": server_args,
                "startup_elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                "error": repr(exc),
            }
            startup_metrics.append(failure)
            save_json(phase_dir / "phase_failure.json", failure)


def build_score_packet(repo_root: Path, output_root: Path, run_profile: str) -> None:
    if run_profile == "128k":
        coding_root = output_root / "128k" / "coding"
    else:
        coding_root = output_root / "64k"

    baseline_results = coding_root / BASELINE["model_key"] / "results.csv"
    candidate_results = coding_root / CANDIDATE["model_key"] / "results.csv"
    if not baseline_results.exists() or not candidate_results.exists():
        save_json(
            output_root / "summary" / "coding_score_packet_skipped.json",
            {
                "reason": "64k results missing",
                "baseline_results_exists": baseline_results.exists(),
                "candidate_results_exists": candidate_results.exists(),
            },
        )
        return
    cmd = [
        "python3",
        str(repo_root / "scripts" / "build_qwen_compare_score_packet.py"),
        "--baseline-results", str(baseline_results),
        "--candidate-results", str(candidate_results),
        "--baseline-key", BASELINE["model_key"],
        "--candidate-key", CANDIDATE["model_key"],
        "--task-manifest", str(coding_root / BASELINE["model_key"] / "task_manifest.json"),
        "--baseline-responses", str(coding_root / BASELINE["model_key"] / "responses.json"),
        "--candidate-responses", str(coding_root / CANDIDATE["model_key"] / "responses.json"),
        "--output-json", str(output_root / "summary" / "coding_score_packet.json"),
        "--output-template-json", str(output_root / "summary" / "coding_manual_rubric_template.json"),
        "--output-md", str(output_root / "summary" / "coding_score_packet.md"),
    ]
    run_command(cmd, capture=False)


def build_agentic_score_packet(repo_root: Path, output_root: Path, run_profile: str) -> None:
    if run_profile != "128k":
        return
    agentic_root = output_root / "128k" / "agentic"
    baseline_results = agentic_root / BASELINE["model_key"] / "results.csv"
    candidate_results = agentic_root / CANDIDATE["model_key"] / "results.csv"
    if not baseline_results.exists() or not candidate_results.exists():
        save_json(
            output_root / "summary" / "agentic_score_packet_skipped.json",
            {
                "reason": "128k agentic results missing",
                "baseline_results_exists": baseline_results.exists(),
                "candidate_results_exists": candidate_results.exists(),
            },
        )
        return
    cmd = [
        "python3",
        str(repo_root / "scripts" / "build_qwen_agentic_score_packet.py"),
        "--baseline-results", str(baseline_results),
        "--candidate-results", str(candidate_results),
        "--baseline-key", BASELINE["model_key"],
        "--candidate-key", CANDIDATE["model_key"],
        "--task-manifest", str(agentic_root / BASELINE["model_key"] / "task_manifest.json"),
        "--baseline-responses", str(agentic_root / BASELINE["model_key"] / "responses.json"),
        "--candidate-responses", str(agentic_root / CANDIDATE["model_key"] / "responses.json"),
        "--workspace-root", str(output_root / "128k" / "workspaces"),
        "--output-json", str(output_root / "summary" / "agentic_score_packet.json"),
        "--output-template-json", str(output_root / "summary" / "agentic_manual_rubric_template.json"),
        "--output-md", str(output_root / "summary" / "agentic_score_packet.md"),
    ]
    run_command(cmd, capture=False)


def render_final_report(repo_root: Path, output_root: Path, run_profile: str) -> None:
    renderer = "render_qwen35_27b_vs_qwen36_27b_report.py"
    if run_profile == "128k":
        renderer = "render_qwen35_27b_vs_qwen36_27b_128k_report.py"
    cmd = [
        "python3",
        str(repo_root / "scripts" / renderer),
        "--output-root", str(output_root),
        "--baseline-key", BASELINE["model_key"],
        "--candidate-key", CANDIDATE["model_key"],
        "--baseline-name", BASELINE["display_name"],
        "--candidate-name", CANDIDATE["display_name"],
        "--output-md", str(output_root / "summary" / ("final_128k_evaluation_report.md" if run_profile == "128k" else "final_evaluation_report.md")),
        "--output-json", str(output_root / "summary" / ("comparison_128k_summary.json" if run_profile == "128k" else "comparison_summary.json")),
    ]
    run_command(cmd, capture=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18343/v1")
    parser.add_argument("--api-key", default="sk-no-key-required")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--modelscope-token", default=os.environ.get("MODELSCOPE_TOKEN", ""))
    parser.add_argument("--wait-timeout-seconds", type=int, default=480)
    parser.add_argument("--smoke-timeout-seconds", type=int, default=240)
    parser.add_argument("--agentic-repeat", type=int, default=2)
    parser.add_argument("--run-profile", choices=["full", "128k"], default="full")
    parser.add_argument("--skip-benchmarks", action="store_true")
    args = parser.parse_args()

    if not args.modelscope_token:
        raise SystemExit("MODELSCOPE_TOKEN is required")

    repo_root = Path(__file__).resolve().parents[1]
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "summary").mkdir(parents=True, exist_ok=True)

    preflight = run_preflight(args.base_url, args.api_key)
    save_json(output_root / "summary" / "preflight.json", preflight)

    download_meta = download_qwen36_model(args.modelscope_token, output_root)
    baseline_meta = remote_file_meta(BASELINE["model_path"])
    candidate_meta = remote_file_meta(CANDIDATE["model_path"])
    save_json(
        output_root / "summary" / "preflight_models.json",
        {
            "generated_at_utc": utc_now(),
            BASELINE["model_key"]: baseline_meta,
            CANDIDATE["model_key"]: candidate_meta,
            "download": {k: v for k, v in download_meta.items() if k != "modelscope_file_meta"},
        },
    )

    backup_path = f"{BENCH_RUN_SCRIPT}.bench-{output_root.name}.bak"
    startup_metrics: list[dict[str, Any]] = []
    smoke_results: list[dict[str, Any]] = []

    try:
        stop_service(LIVE_SERVICE)
        try:
            stop_service(BENCH_SERVICE)
        except Exception:
            sudo_remote(f"systemctl reset-failed {BENCH_SERVICE} || true", capture=False)
        sudo_remote(f"systemctl reset-failed {BENCH_SERVICE} || true", capture=False)

        smoke_results = run_smoke_matrix(
            args.base_url,
            args.api_key,
            backup_path,
            args.wait_timeout_seconds,
            args.smoke_timeout_seconds,
            output_root,
            startup_metrics,
            args.run_profile,
        )
        save_json(output_root / "summary" / "smoke_results.json", smoke_results)
        save_json(output_root / "summary" / "startup_metrics.json", startup_metrics)

        if not args.skip_benchmarks:
            phases = ["64k", "262k", "agentic"]
            if args.run_profile == "128k":
                phases = ["128k-coding", "128k-agentic"]
            for phase in phases:
                run_phase(
                    phase=phase,
                    repo_root=repo_root,
                    output_root=output_root,
                    base_url=args.base_url,
                    api_key=args.api_key,
                    backup_path=backup_path,
                    wait_timeout_seconds=args.wait_timeout_seconds,
                    startup_metrics=startup_metrics,
                    agentic_repeat=args.agentic_repeat,
                )
                save_json(output_root / "summary" / "startup_metrics.json", startup_metrics)
    finally:
        try:
            restore_run_script(backup_path)
        finally:
            try:
                stop_service(BENCH_SERVICE)
            finally:
                start_service(LIVE_SERVICE)
                wait_for_model(args.base_url, args.api_key, LIVE_ALIAS, args.wait_timeout_seconds)

    save_json(output_root / "summary" / "startup_metrics.json", startup_metrics)
    save_json(output_root / "summary" / "smoke_results.json", smoke_results)
    build_score_packet(repo_root, output_root, args.run_profile)
    build_agentic_score_packet(repo_root, output_root, args.run_profile)
    render_final_report(repo_root, output_root, args.run_profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
