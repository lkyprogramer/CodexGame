#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shlex
import subprocess
import tempfile
import time
import urllib.request
from collections import defaultdict
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

REMOTE_EXECUTOR_RUN_SCRIPT = "/opt/llama.cpp/run-openclaw-executor.sh"
REMOTE_EXECUTOR_SERVICE = "openclaw-executor"
REMOTE_CHAT_SERVICE = "qwen35-35b-a3b-uncensored"
REMOTE_CHAT_ALIAS = "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M"
DEFAULT_LLAMA_SERVER_BIN = "/home/hhtele/llama.cpp-gemma4-build/build/bin/llama-server"
LLAMA_SERVER_BIN = DEFAULT_LLAMA_SERVER_BIN

HF_REPO = "unsloth/gemma-4-26B-A4B-it-GGUF"
HF_FILE = "gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf"
HF_RESOLVE_URL = f"https://huggingface.co/{HF_REPO}/resolve/main/{HF_FILE}"

GCP_TRANSFER_DIR = "/home/luo/hf-ms-transfer"
GCP_MODEL_PATH = f"{GCP_TRANSFER_DIR}/{HF_FILE}"

MODELSCOPE_REPO = "wuniansky/gemma-4-26B-A4B-it-UD-Q4_K_X"
REMOTE_MODEL_DIR = "/data/models/qwen"
REMOTE_GEMMA_FILE = HF_FILE
REMOTE_GEMMA_PATH = f"{REMOTE_MODEL_DIR}/{REMOTE_GEMMA_FILE}"

EXECUTOR_SERVER_ARGS = [
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

ANALYST_SERVER_ARGS = [
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
    "--reasoning-format none",
    """--chat-template-kwargs '{"enable_thinking": false}'""",
    "--host 0.0.0.0",
    "--port 18343",
]

EXECUTOR_MODELS = [
    {
        "model_key": "gemma4_26b_a4b_ud_q4_k_xl",
        "model_alias": "bench/gemma4-26b-a4b-it-ud-q4_k_xl",
        "model_path": REMOTE_GEMMA_PATH,
    },
    {
        "model_key": "qwen35_a3b_ud_q4_xl",
        "model_alias": "bench/qwen35-35b-a3b-ud-q4_xl",
        "model_path": "/data/models/qwen/Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf",
    },
]

ANALYST_MODELS = [
    {
        "model_key": "gemma4_26b_a4b_ud_q4_k_xl",
        "model_alias": "bench/gemma4-26b-a4b-it-ud-q4_k_xl-analyst",
        "model_path": REMOTE_GEMMA_PATH,
    },
    {
        "model_key": "qwen35_a3b_ud_q4_xl",
        "model_alias": "bench/qwen35-35b-a3b-ud-q4_xl-analyst",
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
    try:
        run_command(cmd, capture=True, retries=4, retry_delay_seconds=4)
    except subprocess.CalledProcessError:
        payload = base64.b64encode(local_path.read_bytes()).decode("ascii")
        remote_command = """
python3 - <<'PY'
import base64
from pathlib import Path
path = Path({remote_path!r})
path.write_bytes(base64.b64decode({payload!r}.encode("ascii")))
PY
""".format(remote_path=remote_path, payload=payload).strip()
        run_jump(remote_command)


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


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def load_cached_transfer_metadata(transfer_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    hf_path = transfer_dir / "hf_head.json"
    gcp_path = transfer_dir / "gcp_download_meta.json"
    ms_file_path = transfer_dir / "modelscope_file_meta.json"
    remote_path = transfer_dir / "remote_download_meta.json"
    required = [hf_path, gcp_path, ms_file_path, remote_path]
    if not all(path.exists() for path in required):
        return None
    return (
        load_json(hf_path),
        load_json(gcp_path),
        load_json(ms_file_path),
        load_json(remote_path),
    )


def fetch_hf_head() -> dict[str, Any]:
    request = urllib.request.Request(HF_RESOLVE_URL, method="HEAD")
    with urllib.request.urlopen(request, timeout=60) as response:
        return {
            "repo": HF_REPO,
            "file": HF_FILE,
            "url": HF_RESOLVE_URL,
            "content_length": int(response.headers.get("content-length", "0")),
            "final_url": response.geturl(),
        }


def gcp_download_hf_model(summary_dir: Path) -> dict[str, Any]:
    remote_log = f"{GCP_MODEL_PATH}.download.log"
    script = f"""
set -euo pipefail
mkdir -p {shlex.quote(GCP_TRANSFER_DIR)}
if test -f {shlex.quote(GCP_MODEL_PATH)}; then
  size=$(stat -c %s {shlex.quote(GCP_MODEL_PATH)})
  if [ "$size" = "{fetch_hf_head()['content_length']}" ]; then
    python3 - <<'PY'
import hashlib, json
from pathlib import Path
path = Path({GCP_MODEL_PATH!r})
h = hashlib.sha256()
with path.open('rb') as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b''):
        h.update(chunk)
print(json.dumps({{
  "path": str(path),
  "size": path.stat().st_size,
  "sha256": h.hexdigest(),
  "download_log": {remote_log!r},
  "status": "already_present",
}}, ensure_ascii=False))
PY
    exit 0
  fi
fi
aria2c --continue=true --file-allocation=none --max-connection-per-server=16 --split=16 --min-split-size=10M \\
  --dir {shlex.quote(GCP_TRANSFER_DIR)} \\
  --out {shlex.quote(HF_FILE)} \\
  {shlex.quote(HF_RESOLVE_URL)} > {shlex.quote(remote_log)} 2>&1
python3 - <<'PY'
import hashlib, json
from pathlib import Path
path = Path({GCP_MODEL_PATH!r})
h = hashlib.sha256()
with path.open('rb') as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b''):
        h.update(chunk)
print(json.dumps({{
  "path": str(path),
  "size": path.stat().st_size,
  "sha256": h.hexdigest(),
  "download_log": {remote_log!r},
  "status": "downloaded",
}}, ensure_ascii=False))
PY
"""
    payload = json.loads(run_jump(script))
    save_json(summary_dir / "gcp_download_meta.json", payload)
    return payload


def ensure_gcp_modelscope_venv() -> str:
    venv_dir = f"{GCP_TRANSFER_DIR}/.msvenv"
    script = f"""
set -euo pipefail
mkdir -p {shlex.quote(GCP_TRANSFER_DIR)}
if [ ! -x {shlex.quote(venv_dir + '/bin/python')} ]; then
  python3 -m venv {shlex.quote(venv_dir)}
fi
{shlex.quote(venv_dir + '/bin/pip')} -q install --disable-pip-version-check modelscope requests
echo {shlex.quote(venv_dir)}
"""
    return run_jump(script).strip()


def upload_to_modelscope(token: str, gcp_meta: dict[str, Any], summary_dir: Path) -> dict[str, Any]:
    existing = fetch_modelscope_file_metadata(token, allow_missing=True)
    if existing and existing["size"] == int(gcp_meta["size"]):
        payload = {
            "repo_id": MODELSCOPE_REPO,
            "path_in_repo": HF_FILE,
            "local_path": gcp_meta["path"],
            "status": "already_present",
            "remote_revision": existing.get("revision"),
        }
        save_json(summary_dir / "modelscope_upload_meta.json", payload)
        return payload

    venv_dir = ensure_gcp_modelscope_venv()
    remote_result = f"{GCP_TRANSFER_DIR}/modelscope_upload_result.json"
    script = f"""
set -euo pipefail
rm -f {shlex.quote(remote_result)}
{shlex.quote(venv_dir + '/bin/python')} - <<'PY'
import json
from pathlib import Path
from modelscope.hub.api import HubApi

token = {token!r}
repo_id = {MODELSCOPE_REPO!r}
path = Path({gcp_meta['path']!r})
api = HubApi()
api.login(token)
commit = api.upload_file(
    path_or_fileobj=path,
    path_in_repo=path.name,
    repo_id=repo_id,
    repo_type='model',
    token=token,
    commit_message='upload gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf',
    buffer_size_mb=8,
)
payload = {{
    "repo_id": repo_id,
    "path_in_repo": path.name,
    "local_path": str(path),
    "commit": str(commit),
}}
Path({remote_result!r}).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(payload, ensure_ascii=False))
PY
cat {shlex.quote(remote_result)}
"""
    raw = run_jump(script)
    json_payload = None
    for line in reversed([line.strip() for line in raw.splitlines() if line.strip()]):
        if line.startswith("{") and line.endswith("}"):
            json_payload = line
            break
    if json_payload is None:
        raise RuntimeError(f"Could not parse ModelScope upload result: {raw}")
    payload = json.loads(json_payload)
    save_json(summary_dir / "modelscope_upload_meta.json", payload)
    return payload


def fetch_modelscope_file_metadata(token: str, *, allow_missing: bool = False) -> dict[str, Any] | None:
    request = urllib.request.Request(
        f"https://www.modelscope.cn/api/v1/models/{MODELSCOPE_REPO}/repo/files?Revision=master&Recursive=true",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    files = payload["Data"]["Files"]
    matches = [item for item in files if item.get("Name") == HF_FILE]
    if len(matches) == 0 and allow_missing:
        return None
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one ModelScope file named {HF_FILE}, got {len(matches)}")
    item = matches[0]
    return {
        "name": item["Name"],
        "path": item["Path"],
        "size": int(item["Size"]),
        "revision": item.get("Revision"),
        "sha256": item.get("Sha256"),
        "download_url": f"https://www.modelscope.cn/models/{MODELSCOPE_REPO}/resolve/master/{item['Path']}",
    }


def ensure_remote_model_downloaded(token: str, file_meta: dict[str, Any], expected_sha: str, summary_dir: Path) -> dict[str, Any]:
    remote_json_path = f"{REMOTE_GEMMA_PATH}.download.json"
    remote_log_path = f"{REMOTE_GEMMA_PATH}.download.log"
    remote_sha_path = f"{REMOTE_GEMMA_PATH}.sha256"
    script = f"""
set -euo pipefail
mkdir -p {shlex.quote(REMOTE_MODEL_DIR)}
if test -f {shlex.quote(REMOTE_GEMMA_PATH)}; then
  size=$(stat -c %s {shlex.quote(REMOTE_GEMMA_PATH)})
  if [ "$size" = "{file_meta['size']}" ]; then
    sha=$(sha256sum {shlex.quote(REMOTE_GEMMA_PATH)} | awk '{{print $1}}')
    if [ "$sha" = "{expected_sha}" ]; then
      printf '%s\\n' "$sha" > {shlex.quote(remote_sha_path)}
      python3 - <<'PY'
import json
print(json.dumps({{
  "status": "already_present",
  "path": {REMOTE_GEMMA_PATH!r},
  "size": {file_meta['size']},
  "sha256": {expected_sha!r},
}}, ensure_ascii=False))
PY
      exit 0
    fi
  fi
fi
aria2c --continue=true --file-allocation=none --max-connection-per-server=16 --split=16 --min-split-size=10M \\
  --header='Authorization: Bearer {token}' \\
  --dir {shlex.quote(REMOTE_MODEL_DIR)} \\
  --out {shlex.quote(REMOTE_GEMMA_FILE)} \\
  {shlex.quote(file_meta['download_url'])} > {shlex.quote(remote_log_path)} 2>&1
sha256sum {shlex.quote(REMOTE_GEMMA_PATH)} | awk '{{print $1}}' > {shlex.quote(remote_sha_path)}
python3 - <<'PY'
import json
from pathlib import Path
path = Path({REMOTE_GEMMA_PATH!r})
sha = Path({remote_sha_path!r}).read_text(encoding='utf-8').strip()
print(json.dumps({{
  "status": "downloaded",
  "path": str(path),
  "size": path.stat().st_size,
  "sha256": sha,
  "download_log": {remote_log_path!r},
}}, ensure_ascii=False))
PY
"""
    payload = json.loads(run_remote(script))
    save_json(summary_dir / "remote_download_meta.json", payload)
    if int(payload["size"]) != int(file_meta["size"]) or payload["sha256"] != expected_sha:
        raise RuntimeError(f"Remote download verification failed: {payload}")
    return payload


def cleanup_gcp_large_file(summary_dir: Path) -> None:
    run_jump(f"rm -f {shlex.quote(GCP_MODEL_PATH)}", capture=False)
    save_json(summary_dir / "gcp_cleanup.json", {"deleted": GCP_MODEL_PATH, "timestamp_utc": utc_now()})


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


def smoke_chat(base_url: str, api_key: str, model_alias: str, timeout_seconds: int, *, long_context: bool = False) -> dict[str, object]:
    content = "Reply READY only."
    if long_context:
        content = ("A" * 20000) + "\nReply READY only."
    payload = {
        "model": model_alias,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 64,
        "stream": False,
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers=headers,
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
    except Exception as exc:
        return {"http_status": 0, "error": repr(exc)}


def ensure_remote_model(path: str) -> dict[str, Any]:
    script = f"""
set -euo pipefail
test -f {shlex.quote(path)}
python3 - <<'PY'
import hashlib, json, pathlib
p = pathlib.Path({path!r})
h = hashlib.sha256()
with p.open('rb') as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b''):
        h.update(chunk)
print(json.dumps({{"path": str(p), "size": p.stat().st_size, "sha256": h.hexdigest()}}, ensure_ascii=False))
PY
"""
    return json.loads(run_remote(script))


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


def make_run_script(model_path: str, model_alias: str, server_args: list[str]) -> str:
    joined = " \\\n  ".join(server_args)
    return f"""#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${{LD_LIBRARY_PATH:-}}
exec {LLAMA_SERVER_BIN} \\
  -m {model_path} \\
  --alias {model_alias} \\
  {joined}
"""


def install_executor_run_script(script_text: str, backup_path: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(script_text)
    try:
        scp_to_jump(temp_path, "/tmp/run-gemma4-bench.sh")
    finally:
        temp_path.unlink(missing_ok=True)

    remote_block = """
sshpass -p {password} scp -o StrictHostKeyChecking=no /tmp/run-gemma4-bench.sh {user}@{host}:/tmp/run-gemma4-bench.sh
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
                    "cp /tmp/run-gemma4-bench.sh {current}; "
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


def wait_service_active_state(name: str, target: str, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        state = run_remote(f"systemctl is-active {name} || true").strip().splitlines()[-1].strip()
        if target == "inactive":
            if state not in {"active", "activating", "deactivating", "reloading"}:
                return
        elif state == target:
            return
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for service {name} to become {target}")


def wait_port_release(port: int, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        listening = run_remote(
            f"ss -ltn '( sport = :{port} )' | awk 'NR>1 {{print $4}}' || true"
        ).strip()
        if not listening:
            return
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for port {port} to be released")


def stop_service(name: str) -> None:
    remote_sudo(f"systemctl stop --no-block {name}", capture=False)
    wait_service_active_state(name, "inactive")
    try:
        wait_port_release(18343, timeout_seconds=45)
    except TimeoutError:
        # llama-server can keep the listening socket open after systemd reports inactive.
        remote_sudo(f"systemctl kill -s SIGKILL {name} || true", capture=False)
        run_remote("pkill -9 -f 'llama-server.*--port 18343' >/dev/null 2>&1 || true", capture=False)
        wait_port_release(18343, timeout_seconds=45)


def start_service(name: str) -> None:
    remote_sudo(f"systemctl start {name}", capture=False)
    wait_service_active_state(name, "active")


@contextmanager
def capture_round_artifacts(model_output_dir: Path, model_key: str, round_key: str, service_name: str, started_at_epoch: int):
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
            journal = run_remote(f"journalctl -u {shlex.quote(service_name)} --since @{started_at_epoch} --no-pager")
            write_text(model_output_dir / "server.log", journal)
        except Exception as exc:
            errors.append(f"fetch_server_log: {exc!r}")
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
            errors.append(f"cleanup_remote_artifacts: {exc!r}")
        if errors:
            write_text(model_output_dir / "artifact_capture_errors.log", "\n".join(errors) + "\n")


def run_benchmark_command(cmd: list[str], log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as handle:
        subprocess.run(cmd, check=True, text=True, stdout=handle, stderr=subprocess.STDOUT)


def run_executor_coding_round(repo_root: Path, output_root: Path, base_url: str, api_key: str, model_key: str, model_alias: str) -> None:
    model_output_dir = output_root / "executor" / model_key
    model_output_dir.mkdir(parents=True, exist_ok=True)
    bench_log = model_output_dir / "coding.bench.log"
    started_at_epoch = int(run_remote("date +%s").strip())
    with capture_round_artifacts(model_output_dir, model_key, "executor-coding", REMOTE_EXECUTOR_SERVICE, started_at_epoch):
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
            "--timeout-seconds", "2400",
            "--repeat", "1",
            "--network-retries", "1",
            "--benchmark-profile", "gemma4-vs-qwen35-ud-64k-executor-coding",
            "--server-args", " ".join(EXECUTOR_SERVER_ARGS),
            "--family", "java",
            "--family", "ts",
            "--family", "script",
        ]
        run_benchmark_command(cmd, bench_log)


def run_executor_agentic_round(repo_root: Path, output_root: Path, base_url: str, api_key: str, model_key: str, model_alias: str, repeat: int) -> None:
    model_output_dir = output_root / "executor-agentic" / model_key
    model_output_dir.mkdir(parents=True, exist_ok=True)
    workspace_root = output_root / "executor-agentic" / "workspaces"
    workspace_root.mkdir(parents=True, exist_ok=True)
    bench_log = model_output_dir / "agentic.bench.log"
    started_at_epoch = int(run_remote("date +%s").strip())
    with capture_round_artifacts(model_output_dir, model_key, "executor-agentic", REMOTE_EXECUTOR_SERVICE, started_at_epoch):
        cmd = [
            "python3",
            str(repo_root / "scripts" / "qwen_agentic_codegen_bench.py"),
            "--base-url", base_url,
            "--api-key", api_key,
            "--model", model_alias,
            "--model-key", model_key,
            "--output-dir", str(model_output_dir),
            "--workspace-root", str(workspace_root),
            "--timeout-seconds", "2400",
            "--repeat", str(repeat),
            "--instruction-role", "system",
        ]
        run_benchmark_command(cmd, bench_log)


def run_analyst_round(repo_root: Path, output_root: Path, base_url: str, api_key: str, model_key: str, model_alias: str) -> None:
    model_output_dir = output_root / "analyst" / model_key
    model_output_dir.mkdir(parents=True, exist_ok=True)
    bench_log = model_output_dir / "analyst.bench.log"
    started_at_epoch = int(run_remote("date +%s").strip())
    with capture_round_artifacts(model_output_dir, model_key, "analyst", REMOTE_EXECUTOR_SERVICE, started_at_epoch):
        cmd = [
            "python3",
            str(repo_root / "scripts" / "nemotron_thinking_specialized_bench.py"),
            "--base-url", base_url,
            "--api-key", api_key,
            "--model", model_alias,
            "--model-key", model_key,
            "--output-dir", str(model_output_dir),
            "--repo-root", str(repo_root),
            "--timeout-seconds", "2400",
        ]
        run_benchmark_command(cmd, bench_log)


def build_analyst_template_rows(task_manifest_path: Path, model_keys: list[str]) -> list[dict[str, object]]:
    manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for task in manifest:
        for model_key in model_keys:
            rows.append(
                {
                    "model_key": model_key,
                    "task_id": task["task_id"],
                    "family": task["family"],
                    "score_total": None,
                    "score_task_completion": None,
                    "score_evidence_grounding": None,
                    "score_constraint_adherence": None,
                    "score_decision_completeness": None,
                    "score_penalty": 0,
                    "winner": "",
                    "notes": "",
                }
            )
    return rows


def build_checksums_json(summary_dir: Path, hf_meta: dict[str, Any], gcp_meta: dict[str, Any], remote_meta: dict[str, Any]) -> None:
    payload = {
        "hf_content_length": hf_meta["content_length"],
        "gcp_size": gcp_meta["size"],
        "gcp_sha256": gcp_meta["sha256"],
        "remote_size": remote_meta["size"],
        "remote_sha256": remote_meta["sha256"],
        "match": (
            int(hf_meta["content_length"]) == int(gcp_meta["size"]) == int(remote_meta["size"])
            and gcp_meta["sha256"] == remote_meta["sha256"]
        ),
    }
    save_json(summary_dir / "checksums.json", payload)


def main() -> int:
    global LLAMA_SERVER_BIN
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--modelscope-token", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--server-bin", default=DEFAULT_LLAMA_SERVER_BIN)
    parser.add_argument("--wait-timeout-seconds", type=int, default=420)
    parser.add_argument("--agentic-repeat", type=int, default=2)
    parser.add_argument("--smoke-timeout-seconds", type=int, default=120)
    args = parser.parse_args()
    LLAMA_SERVER_BIN = args.server_bin

    repo_root = Path(__file__).resolve().parents[1]
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    summary_dir = output_root / "summary"
    transfer_dir = output_root / "transfer"
    summary_dir.mkdir(parents=True, exist_ok=True)
    transfer_dir.mkdir(parents=True, exist_ok=True)

    cached_transfer = load_cached_transfer_metadata(transfer_dir)
    if cached_transfer is not None:
        hf_meta, gcp_meta, modelscope_file, remote_meta = cached_transfer
    else:
        hf_meta = fetch_hf_head()
        save_json(transfer_dir / "hf_head.json", hf_meta)
        gcp_meta = gcp_download_hf_model(transfer_dir)
        upload_meta = upload_to_modelscope(args.modelscope_token, gcp_meta, transfer_dir)
        modelscope_file = fetch_modelscope_file_metadata(args.modelscope_token)
        save_json(transfer_dir / "modelscope_file_meta.json", modelscope_file)
        remote_meta = ensure_remote_model_downloaded(args.modelscope_token, modelscope_file, gcp_meta["sha256"], transfer_dir)
        build_checksums_json(transfer_dir, hf_meta, gcp_meta, remote_meta)
        cleanup_gcp_large_file(transfer_dir)

    preflight_path = summary_dir / "preflight_models.json"
    if preflight_path.exists():
        preflight = load_json(preflight_path)
    else:
        preflight = {
            "generated_at_utc": utc_now(),
            "gemma4": ensure_remote_model(EXECUTOR_MODELS[0]["model_path"]),
            "qwen35_ud": ensure_remote_model(EXECUTOR_MODELS[1]["model_path"]),
        }
        save_json(preflight_path, preflight)

    backup_path = f"{REMOTE_EXECUTOR_RUN_SCRIPT}.bench-{output_root.name}.bak"
    startup_metrics: list[dict[str, object]] = []
    smoke_results: list[dict[str, object]] = []

    try:
        stop_service(REMOTE_CHAT_SERVICE)
        start_service(REMOTE_EXECUTOR_SERVICE)

        for model in EXECUTOR_MODELS:
            script_text = make_run_script(model["model_path"], model["model_alias"], EXECUTOR_SERVER_ARGS)
            started = time.perf_counter()
            install_executor_run_script(script_text, backup_path)
            wait_for_model(args.base_url, args.api_key, model["model_alias"], args.wait_timeout_seconds)
            startup_metrics.append(
                {
                    "timestamp_utc": utc_now(),
                    "phase": "executor",
                    "model_key": model["model_key"],
                    "model_alias": model["model_alias"],
                    "model_path": model["model_path"],
                    "startup_elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "idle_gpu": remote_gpu_snapshot(),
                    "server_args": EXECUTOR_SERVER_ARGS,
                }
            )
            smoke = smoke_chat(args.base_url, args.api_key, model["model_alias"], args.smoke_timeout_seconds, long_context=False)
            smoke.update({"phase": "executor", "model_key": model["model_key"], "model_alias": model["model_alias"]})
            smoke_results.append(smoke)
            if smoke.get("http_status") != 200:
                raise SystemExit(f"Executor smoke failed for {model['model_key']}: {smoke}")
            run_executor_coding_round(repo_root, output_root, args.base_url, args.api_key, model["model_key"], model["model_alias"])
            run_executor_agentic_round(repo_root, output_root, args.base_url, args.api_key, model["model_key"], model["model_alias"], args.agentic_repeat)

        for model in ANALYST_MODELS:
            script_text = make_run_script(model["model_path"], model["model_alias"], ANALYST_SERVER_ARGS)
            started = time.perf_counter()
            install_executor_run_script(script_text, backup_path)
            wait_for_model(args.base_url, args.api_key, model["model_alias"], args.wait_timeout_seconds)
            startup_metrics.append(
                {
                    "timestamp_utc": utc_now(),
                    "phase": "analyst",
                    "model_key": model["model_key"],
                    "model_alias": model["model_alias"],
                    "model_path": model["model_path"],
                    "startup_elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "idle_gpu": remote_gpu_snapshot(),
                    "server_args": ANALYST_SERVER_ARGS,
                }
            )
            smoke = smoke_chat(args.base_url, args.api_key, model["model_alias"], args.smoke_timeout_seconds, long_context=True)
            smoke.update({"phase": "analyst", "model_key": model["model_key"], "model_alias": model["model_alias"]})
            smoke_results.append(smoke)
            if smoke.get("http_status") != 200:
                raise SystemExit(f"Analyst smoke failed for {model['model_key']}: {smoke}")
            run_analyst_round(repo_root, output_root, args.base_url, args.api_key, model["model_key"], model["model_alias"])
    finally:
        try:
            restore_executor_run_script(backup_path)
        finally:
            stop_service(REMOTE_EXECUTOR_SERVICE)
            start_service(REMOTE_CHAT_SERVICE)
            wait_for_model(args.base_url, args.api_key, REMOTE_CHAT_ALIAS, args.wait_timeout_seconds)

    save_json(summary_dir / "startup_metrics.json", startup_metrics)
    save_json(summary_dir / "smoke_results.json", smoke_results)

    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_qwen_model_compare_report.py"),
            "--baseline-results",
            str(output_root / "executor" / EXECUTOR_MODELS[0]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "executor" / EXECUTOR_MODELS[1]["model_key"] / "results.csv"),
            "--baseline-key",
            EXECUTOR_MODELS[0]["model_key"],
            "--candidate-key",
            EXECUTOR_MODELS[1]["model_key"],
            "--baseline-name",
            EXECUTOR_MODELS[0]["model_alias"],
            "--candidate-name",
            EXECUTOR_MODELS[1]["model_alias"],
            "--output-md",
            str(summary_dir / "executor_coding_compare_report.md"),
        ],
        check=True,
        text=True,
    )

    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_qwen_agentic_compare_report.py"),
            "--baseline-results",
            str(output_root / "executor-agentic" / EXECUTOR_MODELS[0]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "executor-agentic" / EXECUTOR_MODELS[1]["model_key"] / "results.csv"),
            "--baseline-key",
            EXECUTOR_MODELS[0]["model_key"],
            "--candidate-key",
            EXECUTOR_MODELS[1]["model_key"],
            "--baseline-name",
            EXECUTOR_MODELS[0]["model_alias"],
            "--candidate-name",
            EXECUTOR_MODELS[1]["model_alias"],
            "--output-md",
            str(summary_dir / "executor_agentic_compare_report.md"),
            "--output-json",
            str(summary_dir / "executor_agentic_compare_summary.json"),
        ],
        check=True,
        text=True,
    )

    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "render_nemotron_thinking_specialized_report.py"),
            "--baseline-results",
            str(output_root / "analyst" / ANALYST_MODELS[0]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "analyst" / ANALYST_MODELS[1]["model_key"] / "results.csv"),
            "--baseline-name",
            ANALYST_MODELS[0]["model_alias"],
            "--candidate-name",
            ANALYST_MODELS[1]["model_alias"],
            "--output-md",
            str(summary_dir / "analyst_compare_report.md"),
        ],
        check=True,
        text=True,
    )

    subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "build_qwen_compare_score_packet.py"),
            "--baseline-results",
            str(output_root / "executor" / EXECUTOR_MODELS[0]["model_key"] / "results.csv"),
            "--candidate-results",
            str(output_root / "executor" / EXECUTOR_MODELS[1]["model_key"] / "results.csv"),
            "--baseline-key",
            EXECUTOR_MODELS[0]["model_key"],
            "--candidate-key",
            EXECUTOR_MODELS[1]["model_key"],
            "--task-manifest",
            str(output_root / "executor" / EXECUTOR_MODELS[0]["model_key"] / "task_manifest.json"),
            "--baseline-responses",
            str(output_root / "executor" / EXECUTOR_MODELS[0]["model_key"] / "responses.json"),
            "--candidate-responses",
            str(output_root / "executor" / EXECUTOR_MODELS[1]["model_key"] / "responses.json"),
            "--output-json",
            str(summary_dir / "coding_score_packet.json"),
            "--output-template-json",
            str(summary_dir / "coding_manual_rubric_template.json"),
            "--output-md",
            str(summary_dir / "coding_score_packet.md"),
        ],
        check=True,
        text=True,
    )

    analyst_template = build_analyst_template_rows(
        output_root / "analyst" / ANALYST_MODELS[0]["model_key"] / "task_manifest.json",
        [ANALYST_MODELS[0]["model_key"], ANALYST_MODELS[1]["model_key"]],
    )
    save_json(summary_dir / "analyst_manual_rubric_template.json", analyst_template)

    write_text(
        summary_dir / "run_summary.md",
        "\n".join(
            [
                "# Gemma4 vs Qwen35 UD Run Summary",
                "",
                f"- Generated at (UTC): `{utc_now()}`",
                f"- HF source: `{HF_REPO}/{HF_FILE}`",
                f"- ModelScope repo: `{MODELSCOPE_REPO}`",
                f"- Gemma path: `{preflight['gemma4']['path']}`",
                f"- Gemma size bytes: `{preflight['gemma4']['size']}`",
                f"- Gemma sha256: `{preflight['gemma4']['sha256']}`",
                f"- Qwen35 UD path: `{preflight['qwen35_ud']['path']}`",
                f"- Qwen35 UD size bytes: `{preflight['qwen35_ud']['size']}`",
                f"- Qwen35 UD sha256: `{preflight['qwen35_ud']['sha256']}`",
                f"- Restored live alias: `{REMOTE_CHAT_ALIAS}`",
                "",
                "Artifacts:",
                "- `transfer/gcp_download_meta.json`",
                "- `transfer/modelscope_upload_meta.json`",
                "- `transfer/remote_download_meta.json`",
                "- `transfer/checksums.json`",
                "- `summary/executor_coding_compare_report.md`",
                "- `summary/executor_agentic_compare_report.md`",
                "- `summary/analyst_compare_report.md`",
                "- `summary/coding_score_packet.md`",
                "- `summary/coding_manual_rubric_template.json`",
                "- `summary/analyst_manual_rubric_template.json`",
            ]
        )
        + "\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
