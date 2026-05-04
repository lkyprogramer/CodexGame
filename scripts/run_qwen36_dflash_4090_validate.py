#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT = "project-d4e4f88c-f262-47af-b5b"
ZONE = "us-central1-a"
INSTANCE = "instance-20260222-145427"

REMOTE_HOST = "100.107.189.100"
REMOTE_USER = "hhtele"
REMOTE_PASSWORD = "hhtele"

LIVE_SERVICE = "qwen35-35b-a3b-uncensored"
BENCH_SERVICE = "openclaw-executor"
LIVE_ALIAS = "hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M"

MODELSCOPE_REPO = "wuniansky/Qwen3.6-27B-Q4_K_M"
GCP_TRANSFER_DIR = "/home/luo/hf-ms-transfer/qwen36-dflash"
GCP_LEGACY_GEMMA = "/home/luo/hf-ms-transfer/gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf"

REMOTE_MODEL_DIR = "/data/models/qwen"
REMOTE_DOWNLOAD_DIR = f"{REMOTE_MODEL_DIR}/.downloads/qwen36-dflash"
REMOTE_QWEN36_Q4 = f"{REMOTE_MODEL_DIR}/Qwen3.6-27B-Q4_K_M.gguf"
REMOTE_DRAFT = f"{REMOTE_MODEL_DIR}/dflash-draft/model.safetensors"
REMOTE_LUCEBOX = "/home/hhtele/lucebox-hub-dflash-qwen36"
REMOTE_DFLASH = f"{REMOTE_LUCEBOX}/dflash"

LLAMA_SERVER_BIN = "/opt/llama.cpp/build/bin/llama-server"
BASELINE_MODEL = f"{REMOTE_MODEL_DIR}/Qwen3.6-27B-UD-Q5_K_XL.gguf"
BASELINE_ALIAS = "bench/qwen36-q5-llama-baseline"
UPLOAD_PART_BYTES = 1024 * 1024 * 1024


@dataclass(frozen=True)
class Artifact:
    key: str
    hf_repo: str
    hf_file: str
    modelscope_path: str
    gcp_path: str
    remote_path: str

    @property
    def hf_url(self) -> str:
        return f"https://huggingface.co/{self.hf_repo}/resolve/main/{self.hf_file}"


ARTIFACTS = [
    Artifact(
        key="qwen36_q4_k_m",
        hf_repo="unsloth/Qwen3.6-27B-GGUF",
        hf_file="Qwen3.6-27B-Q4_K_M.gguf",
        modelscope_path="Qwen3.6-27B-Q4_K_M.gguf",
        gcp_path=f"{GCP_TRANSFER_DIR}/Qwen3.6-27B-Q4_K_M.gguf",
        remote_path=REMOTE_QWEN36_Q4,
    ),
    Artifact(
        key="qwen35_dflash_draft",
        hf_repo="z-lab/Qwen3.5-27B-DFlash",
        hf_file="model.safetensors",
        modelscope_path="draft/model.safetensors",
        gcp_path=f"{GCP_TRANSFER_DIR}/model.safetensors",
        remote_path=REMOTE_DRAFT,
    ),
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
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    last: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, retries + 1):
        completed = subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=capture,
            timeout=timeout,
        )
        if completed.returncode == 0 or not check:
            return completed
        last = completed
        if attempt < retries:
            time.sleep(retry_delay_seconds * attempt)
    assert last is not None
    raise subprocess.CalledProcessError(last.returncode, cmd, output=last.stdout, stderr=last.stderr)


def run_jump(command: str, *, capture: bool = True, timeout: int | None = None) -> str:
    cmd = [
        "gcloud",
        "compute",
        "ssh",
        INSTANCE,
        "--project",
        PROJECT,
        "--zone",
        ZONE,
        "--tunnel-through-iap",
        "--ssh-flag=-o ServerAliveInterval=30",
        "--ssh-flag=-o ServerAliveCountMax=6",
        f"--command={command}",
    ]
    completed = run_command(cmd, capture=capture, retries=5, retry_delay_seconds=4, timeout=timeout)
    return completed.stdout if capture else ""


def run_remote(command: str, *, capture: bool = True, timeout: int | None = None) -> str:
    nested = "sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {command}".format(
        password=shlex.quote(REMOTE_PASSWORD),
        user=REMOTE_USER,
        host=REMOTE_HOST,
        command=shlex.quote(command),
    )
    return run_jump(nested, capture=capture, timeout=timeout)


def remote_sudo(command: str, *, capture: bool = True, timeout: int | None = None) -> str:
    wrapped = "printf '%s\\n' {password} | sudo -S -p '' bash -lc {command}".format(
        password=shlex.quote(REMOTE_PASSWORD),
        command=shlex.quote(command),
    )
    return run_remote(wrapped, capture=capture, timeout=timeout)


def scp_to_jump(local_path: Path, remote_path: str) -> None:
    cmd = [
        "gcloud",
        "compute",
        "scp",
        "--project",
        PROJECT,
        "--zone",
        ZONE,
        "--tunnel-through-iap",
        str(local_path),
        f"{INSTANCE}:{remote_path}",
    ]
    run_command(cmd, capture=True, retries=4, retry_delay_seconds=4)


def scp_script_to_remote(script_text: str, jump_path: str, remote_path: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        tmp = Path(handle.name)
        handle.write(script_text)
    try:
        scp_to_jump(tmp, jump_path)
    finally:
        tmp.unlink(missing_ok=True)
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


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def parse_last_json(raw: str) -> Any:
    for line in reversed([line.strip() for line in raw.splitlines() if line.strip()]):
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
        if line.startswith("[") and line.endswith("]"):
            return json.loads(line)
    raise RuntimeError(f"Could not parse JSON from output tail: {raw[-2000:]}")


def fetch_hf_head(artifact: Artifact) -> dict[str, Any]:
    request = urllib.request.Request(artifact.hf_url, method="HEAD")
    with urllib.request.urlopen(request, timeout=90) as response:
        return {
            "key": artifact.key,
            "repo": artifact.hf_repo,
            "file": artifact.hf_file,
            "url": artifact.hf_url,
            "content_length": int(response.headers.get("content-length", "0")),
            "final_url": response.geturl(),
        }


def gcp_cleanup(output_root: Path) -> dict[str, Any]:
    script = f"""
set -euo pipefail
python3 - <<'PY'
import json
import os
import shutil
import subprocess
from pathlib import Path

default_paths = [
    ({GCP_LEGACY_GEMMA!r}, "legacy gemma transfer artifact", "default"),
    ("/tmp/openclaw", "openclaw tmp data", "default"),
    ("/tmp/openclaw-1001", "openclaw tmp data", "default"),
    ("/home/luo/.openclaw", "openclaw runtime config/cache", "default"),
    ("/home/luo/archive_openclaw_bot_mirror", "archived openclaw mirror", "default"),
]
extended_paths = [
    ("/home/luo/downloads", "large downloads cache", "extended"),
    ("/home/luo/.npm", "npm cache", "extended"),
    ("/home/luo/.npm-global/lib/node_modules/openclaw", "global openclaw npm package", "extended"),
]
glob_paths = [
    ("/tmp", "openclaw*.log", "openclaw tmp logs", "default"),
]

def df():
    out = subprocess.check_output(["df", "-B1", "/"], text=True).splitlines()[-1].split()
    return {{"filesystem": out[0], "size": int(out[1]), "used": int(out[2]), "avail": int(out[3]), "use_pct": out[4], "mount": out[5]}}

def size_of(path: Path) -> int:
    if not path.exists() and not path.is_symlink():
        return 0
    if path.is_file() or path.is_symlink():
        return path.stat().st_size
    total = 0
    for root, dirs, files in os.walk(path):
        for name in files:
            p = Path(root) / name
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total

def delete_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()

before = df()
candidates = []
for raw, reason, tier in default_paths + extended_paths:
    p = Path(raw)
    candidates.append({{"path": raw, "reason": reason, "tier": tier, "exists": p.exists() or p.is_symlink(), "size": size_of(p)}})
for base, pattern, reason, tier in glob_paths:
    for p in Path(base).glob(pattern):
        candidates.append({{"path": str(p), "reason": reason, "tier": tier, "exists": True, "size": size_of(p)}})

deleted = []
skipped = []
for item in candidates:
    if item["tier"] != "default" or not item["exists"]:
        skipped.append({{**item, "why": "not default tier or missing"}})
        continue
    delete_path(Path(item["path"]))
    deleted.append(item)

mid = df()
# The GCP staging root disk is 40 GB. After deleting old transfer artifacts
# and OpenClaw data, 25 GiB is enough for the Qwen3.6 Q4_K_M target plus the
# DFlash draft and upload metadata, while avoiding journal/cache churn.
min_avail = 25 * 1024 * 1024 * 1024
if mid["avail"] < min_avail:
    for item in candidates:
        if item["tier"] != "extended" or not item["exists"]:
            continue
        delete_path(Path(item["path"]))
        deleted.append(item)

after = df()
print(json.dumps({{
    "timestamp_utc": {utc_now()!r},
    "before": before,
    "after": after,
    "min_avail_required": min_avail,
    "candidates": candidates,
    "deleted": deleted,
    "skipped": skipped,
    "reclaimed_bytes_estimate": sum(item["size"] for item in deleted),
}}, ensure_ascii=False))
PY
"""
    payload = parse_last_json(run_jump(script, timeout=600))
    save_json(output_root / "cleanup" / "gcp_cleanup_preflight.json", payload)
    save_json(output_root / "cleanup" / "cleanup_candidates.json", payload["candidates"])
    if int(payload["after"]["avail"]) < 25 * 1024 * 1024 * 1024:
        raise RuntimeError(f"GCP cleanup left insufficient free space: {payload['after']}")
    return payload


def gcp_download_artifact(artifact: Artifact, head: dict[str, Any], output_root: Path) -> dict[str, Any]:
    script = f"""
set -euo pipefail
mkdir -p {shlex.quote(GCP_TRANSFER_DIR)}
target={shlex.quote(artifact.gcp_path)}
url={shlex.quote(artifact.hf_url)}
expected_size={shlex.quote(str(head.get("content_length") or 0))}
log="$target.download.log"
if [ -f "$target" ] && [ "$expected_size" != "0" ] && [ "$(stat -c %s "$target")" = "$expected_size" ]; then
  status=already_present
else
  status=downloaded
  aria2c --continue=true --file-allocation=none --max-connection-per-server=16 --split=16 --min-split-size=10M \\
    --dir {shlex.quote(GCP_TRANSFER_DIR)} --out {shlex.quote(Path(artifact.gcp_path).name)} "$url" > "$log" 2>&1
fi
STATUS="$status" python3 - <<'PY'
import hashlib, json
import os
from pathlib import Path
path = Path({artifact.gcp_path!r})
h = hashlib.sha256()
with path.open("rb") as fh:
    for chunk in iter(lambda: fh.read(1024 * 1024), b""):
        h.update(chunk)
print(json.dumps({{
    "key": {artifact.key!r},
    "status": os.environ["STATUS"],
    "path": str(path),
    "size": path.stat().st_size,
    "sha256": h.hexdigest(),
    "download_log": {str(artifact.gcp_path) + ".download.log"!r},
    "hf_content_length": {int(head.get("content_length") or 0)},
}}, ensure_ascii=False))
PY
"""
    payload = parse_last_json(run_jump(script, timeout=7200))
    if head.get("content_length") and int(payload["size"]) != int(head["content_length"]):
        raise RuntimeError(f"GCP size mismatch for {artifact.key}: {payload} vs {head}")
    save_json(output_root / "transfer" / f"{artifact.key}_gcp_download_meta.json", payload)
    return payload


def ensure_gcp_modelscope_venv() -> str:
    script = f"""
set -euo pipefail
mkdir -p {shlex.quote(GCP_TRANSFER_DIR)}
venv={shlex.quote(GCP_TRANSFER_DIR + "/.msvenv")}
if [ ! -x "$venv/bin/python" ]; then
  python3 -m venv "$venv"
fi
"$venv/bin/pip" -q install --disable-pip-version-check modelscope requests
printf '%s\\n' "$venv"
"""
    return run_jump(script, timeout=1200).strip().splitlines()[-1]


def fetch_modelscope_files(token: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        f"https://www.modelscope.cn/api/v1/models/{MODELSCOPE_REPO}/repo/files?Revision=master&Recursive=true",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return (((payload.get("Data") or {}).get("Files")) or ((payload.get("data") or {}).get("files")) or [])


def find_modelscope_file(token: str, path_in_repo: str, *, allow_missing: bool = False) -> dict[str, Any] | None:
    files = fetch_modelscope_files(token)
    matches = [
        item for item in files
        if (item.get("Path") or item.get("path") or item.get("Name") or item.get("name")) == path_in_repo
        or str(item.get("Path") or item.get("path") or "").endswith("/" + path_in_repo)
    ]
    if not matches and allow_missing:
        return None
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one ModelScope file {path_in_repo}, got {len(matches)}")
    item = matches[0]
    size = int(item.get("Size") or item.get("size") or 0)
    sha = item.get("Sha256") or item.get("sha256") or item.get("SHA256") or ""
    path = item.get("Path") or item.get("path") or path_in_repo
    return {
        "name": item.get("Name") or item.get("name") or Path(path_in_repo).name,
        "path": path,
        "size": size,
        "sha256": sha,
        "revision": item.get("Revision") or item.get("revision"),
        "download_url": f"https://www.modelscope.cn/models/{MODELSCOPE_REPO}/resolve/master/{path}",
    }


def upload_artifact_to_modelscope(token: str, artifact: Artifact, gcp_meta: dict[str, Any], output_root: Path) -> dict[str, Any]:
    existing = find_modelscope_file(token, artifact.modelscope_path, allow_missing=True)
    if existing and existing.get("size") == int(gcp_meta["size"]) and (
        not existing.get("sha256") or existing["sha256"].lower() == gcp_meta["sha256"].lower()
    ):
        payload = {
            "key": artifact.key,
            "repo_id": MODELSCOPE_REPO,
            "path_in_repo": artifact.modelscope_path,
            "local_path": gcp_meta["path"],
            "status": "already_present",
            "remote_revision": existing.get("revision"),
        }
        save_json(output_root / "transfer" / f"{artifact.key}_modelscope_upload_meta.json", payload)
        return payload

    venv = ensure_gcp_modelscope_venv()
    remote_result = f"{GCP_TRANSFER_DIR}/{artifact.key}.modelscope_upload_result.json"
    script = f"""
set -euo pipefail
rm -f {shlex.quote(remote_result)}
MODELSCOPE_TOKEN="$MODELSCOPE_TOKEN" {shlex.quote(venv + "/bin/python")} - <<'PY'
import json
import os
from pathlib import Path
from modelscope.hub.api import HubApi

token = os.environ["MODELSCOPE_TOKEN"]
api = HubApi()
commit = api.upload_file(
    path_or_fileobj=Path({gcp_meta["path"]!r}),
    path_in_repo={artifact.modelscope_path!r},
    repo_id={MODELSCOPE_REPO!r},
    repo_type="model",
    token=token,
    commit_message={("upload " + artifact.modelscope_path)!r},
    buffer_size_mb=8,
)
payload = {{
    "key": {artifact.key!r},
    "repo_id": {MODELSCOPE_REPO!r},
    "path_in_repo": {artifact.modelscope_path!r},
    "local_path": {gcp_meta["path"]!r},
    "status": "uploaded",
    "commit": str(commit),
}}
Path({remote_result!r}).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
PY
cat {shlex.quote(remote_result)}
"""
    script = f"export MODELSCOPE_TOKEN={shlex.quote(token)}\n" + script
    raw = run_jump(script, timeout=14400)
    payload = parse_last_json(raw)
    save_json(output_root / "transfer" / f"{artifact.key}_modelscope_upload_meta.json", payload)
    return payload


def start_modelscope_parts_upload_job(token: str, metas: dict[str, dict[str, Any]], output_root: Path) -> dict[str, Any]:
    """Start a detached GCP upload job so large ModelScope transfers do not depend on SSH lifetime."""
    venv = ensure_gcp_modelscope_venv()
    remote_script = f"{GCP_TRANSFER_DIR}/upload_parts_nohup.py"
    pid_file = f"{GCP_TRANSFER_DIR}/upload_parts_nohup.pid"
    progress_log = f"{GCP_TRANSFER_DIR}/upload_parts_progress.jsonl"
    nohup_log = f"{GCP_TRANSFER_DIR}/upload_parts_nohup.log"
    state_file = f"{GCP_TRANSFER_DIR}/upload_parts_state.json"
    manifest_file = f"{GCP_TRANSFER_DIR}/modelscope_parts_manifest.json"
    parts_tmp = f"{GCP_TRANSFER_DIR}/parts_tmp"
    upload_items = [
        {
            "key": artifact.key,
            "local_path": metas[artifact.key]["path"],
            "repo_path": artifact.modelscope_path,
            "size": int(metas[artifact.key]["size"]),
            "sha256": metas[artifact.key]["sha256"],
        }
        for artifact in ARTIFACTS
    ]
    uploader = r'''
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from modelscope.hub.api import HubApi

repo_id = os.environ["MODELSCOPE_REPO"]
payload = json.loads(os.environ["UPLOAD_PAYLOAD"])
chunk_size = int(os.environ.get("UPLOAD_PART_BYTES", str(1024 * 1024 * 1024)))
progress_log = Path(os.environ["UPLOAD_PROGRESS_LOG"])
state_file = Path(os.environ["UPLOAD_STATE_FILE"])
manifest_file = Path(os.environ["UPLOAD_MANIFEST_FILE"])
parts_tmp = Path(os.environ["UPLOAD_PARTS_TMP"])
token = os.environ["MODELSCOPE_TOKEN"]
api = HubApi()
parts_tmp.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(event: str, **fields):
    payload = {"ts": now(), "event": event, **fields}
    line = json.dumps(payload, ensure_ascii=False)
    with progress_log.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
    print(line, flush=True)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_paths() -> set[str]:
    try:
        files = api.get_model_files(model_id=repo_id, recursive=True)
    except TypeError:
        files = api.get_model_files(repo_id=repo_id, recursive=True)
    paths = set()
    for item in files or []:
        if isinstance(item, str):
            paths.add(item)
        elif isinstance(item, dict):
            paths.add(item.get("Path") or item.get("path") or item.get("Name") or item.get("name") or "")
    return {p for p in paths if p}


def upload_file(local_path: Path, repo_path: str, message: str):
    api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=repo_path,
        repo_id=repo_id,
        repo_type="model",
        token=token,
        commit_message=message,
        buffer_size_mb=8,
    )


def write_state(status: str, **extra):
    state_file.write_text(
        json.dumps({"ts": now(), "status": status, **extra}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


try:
    existing = remote_paths()
    emit("upload_job_start", chunk_size=chunk_size, remote_file_count=len(existing))
    manifest = {
        "repo_id": repo_id,
        "chunk_size": chunk_size,
        "artifacts": [],
    }
    for item in payload["items"]:
        source = Path(item["local_path"])
        if not source.exists():
            raise FileNotFoundError(str(source))
        actual_size = source.stat().st_size
        actual_sha = sha256_of(source)
        if actual_size != int(item["size"]) or actual_sha.lower() != item["sha256"].lower():
            raise RuntimeError(f"{item['key']}: local checksum mismatch")
        part_count = math.ceil(actual_size / chunk_size)
        artifact_entry = {
            "key": item["key"],
            "repo_path": item["repo_path"],
            "size": actual_size,
            "sha256": actual_sha,
            "part_count": part_count,
            "parts": [],
        }
        emit("artifact_start", path=item["repo_path"], size=actual_size, sha256=actual_sha, part_count=part_count)
        with source.open("rb") as fh:
            for index in range(part_count):
                part_name = f"{Path(item['repo_path']).name}.part-{index:04d}"
                repo_part = f"parts/{part_name}"
                expected = min(chunk_size, actual_size - index * chunk_size)
                part_path = parts_tmp / part_name
                if not part_path.exists() or part_path.stat().st_size != expected:
                    with part_path.open("wb") as out:
                        remaining = expected
                        while remaining:
                            data = fh.read(min(8 * 1024 * 1024, remaining))
                            if not data:
                                break
                            out.write(data)
                            remaining -= len(data)
                else:
                    fh.seek(expected, os.SEEK_CUR)
                part_sha = sha256_of(part_path)
                part_payload = {
                    "index": index,
                    "path": repo_part,
                    "size": part_path.stat().st_size,
                    "sha256": part_sha,
                }
                artifact_entry["parts"].append(part_payload)
                if repo_part in existing:
                    emit("upload_part_skip", **part_payload, status="already_present")
                    continue
                emit("upload_part_start", **part_payload)
                start = time.time()
                upload_file(part_path, repo_part, f"upload {repo_part}")
                elapsed = round(time.time() - start, 3)
                existing.add(repo_part)
                emit("upload_part_done", **part_payload, elapsed_seconds=elapsed)
        manifest["artifacts"].append(artifact_entry)
        emit("artifact_done", path=item["repo_path"], part_count=part_count)
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    upload_file(manifest_file, "parts/manifest.json", "upload parts manifest")
    write_state("done", manifest=str(manifest_file))
    emit("upload_job_done", manifest=str(manifest_file))
except Exception as exc:
    write_state("failed", error=repr(exc))
    emit("upload_job_failed", error=repr(exc))
    raise
'''
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        tmp = Path(handle.name)
        handle.write(uploader)
    try:
        scp_to_jump(tmp, remote_script)
    finally:
        tmp.unlink(missing_ok=True)
    payload = {"items": upload_items}
    launcher = f"""
set -euo pipefail
mkdir -p {shlex.quote(GCP_TRANSFER_DIR)}
if [ -f {shlex.quote(pid_file)} ] && kill -0 "$(cat {shlex.quote(pid_file)})" 2>/dev/null; then
  echo "upload job already running: $(cat {shlex.quote(pid_file)})"
else
  rm -f {shlex.quote(progress_log)} {shlex.quote(state_file)} {shlex.quote(nohup_log)}
  nohup env \
    MODELSCOPE_TOKEN={shlex.quote(token)} \
    MODELSCOPE_REPO={shlex.quote(MODELSCOPE_REPO)} \
    UPLOAD_PAYLOAD={shlex.quote(json.dumps(payload, ensure_ascii=False))} \
    UPLOAD_PART_BYTES={UPLOAD_PART_BYTES} \
    UPLOAD_PROGRESS_LOG={shlex.quote(progress_log)} \
    UPLOAD_STATE_FILE={shlex.quote(state_file)} \
    UPLOAD_MANIFEST_FILE={shlex.quote(manifest_file)} \
    UPLOAD_PARTS_TMP={shlex.quote(parts_tmp)} \
    {shlex.quote(venv + "/bin/python")} {shlex.quote(remote_script)} \
    > {shlex.quote(nohup_log)} 2>&1 &
  echo $! > {shlex.quote(pid_file)}
fi
python3 - <<'PY'
import json
from pathlib import Path
payload = {{
    "status": "started",
    "pid_file": {pid_file!r},
    "pid": Path({pid_file!r}).read_text().strip(),
    "script": {remote_script!r},
    "progress_log": {progress_log!r},
    "nohup_log": {nohup_log!r},
    "state_file": {state_file!r},
    "manifest_file": {manifest_file!r},
    "parts_tmp": {parts_tmp!r},
}}
print(json.dumps(payload, ensure_ascii=False))
PY
"""
    result = parse_last_json(run_jump(launcher, timeout=600))
    save_json(output_root / "transfer" / "modelscope_parts_upload_job.json", result)
    return result


def write_and_upload_sha256s(token: str, metas: dict[str, dict[str, Any]], output_root: Path) -> dict[str, Any]:
    lines = [f"{meta['sha256']}  {artifact.modelscope_path}" for artifact in ARTIFACTS for meta in [metas[artifact.key]]]
    local = output_root / "transfer" / "SHA256SUMS"
    save_text(local, "\n".join(lines) + "\n")
    remote_sha = f"{GCP_TRANSFER_DIR}/SHA256SUMS"
    scp_to_jump(local, remote_sha)
    sha_artifact = Artifact(
        key="sha256s",
        hf_repo="",
        hf_file="SHA256SUMS",
        modelscope_path="SHA256SUMS",
        gcp_path=remote_sha,
        remote_path=f"{REMOTE_DOWNLOAD_DIR}/SHA256SUMS",
    )
    gcp_meta = {"path": remote_sha, "size": local.stat().st_size, "sha256": ""}
    return upload_artifact_to_modelscope(token, sha_artifact, gcp_meta, output_root)


def remote_download_artifacts(token: str, expected: dict[str, dict[str, Any]], output_root: Path) -> dict[str, Any]:
    file_meta_by_key = {}
    for artifact in ARTIFACTS:
        meta = find_modelscope_file(token, artifact.modelscope_path)
        assert meta is not None
        file_meta_by_key[artifact.key] = meta
        save_json(output_root / "transfer" / f"{artifact.key}_modelscope_file_meta.json", meta)

    downloader = r'''
import hashlib
import json
import os
import subprocess
from pathlib import Path

token = os.environ["MODELSCOPE_TOKEN"]
payload = json.loads(os.environ["DOWNLOAD_PAYLOAD"])
download_dir = Path(payload["download_dir"])
download_dir.mkdir(parents=True, exist_ok=True)
results = {}

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

for item in payload["items"]:
    key = item["key"]
    target = Path(item["remote_path"])
    target.parent.mkdir(parents=True, exist_ok=True)
    expected_sha = item["expected_sha256"]
    expected_size = int(item["expected_size"])
    tmp = download_dir / (Path(item["remote_path"]).name + ".partial")
    log = download_dir / (Path(item["remote_path"]).name + ".aria2.log")
    status = "already_present"
    if not target.exists() or target.stat().st_size != expected_size or sha256_of(target).lower() != expected_sha.lower():
        status = "downloaded"
        if tmp.exists() and tmp.stat().st_size == expected_size and sha256_of(tmp).lower() == expected_sha.lower():
            pass
        else:
            cmd = [
                "aria2c",
                "--continue=true",
                "--file-allocation=none",
                "--max-connection-per-server=16",
                "--split=16",
                "--min-split-size=10M",
                f"--header=Authorization: Bearer {token}",
                "--dir", str(download_dir),
                "--out", tmp.name,
                item["download_url"],
            ]
            with log.open("w", encoding="utf-8") as handle:
                subprocess.run(cmd, check=True, text=True, stdout=handle, stderr=subprocess.STDOUT)
        if tmp.stat().st_size != expected_size:
            raise SystemExit(f"{key}: size mismatch after download")
        if sha256_of(tmp).lower() != expected_sha.lower():
            raise SystemExit(f"{key}: sha256 mismatch after download")
        os.replace(tmp, target)
    actual_sha = sha256_of(target)
    results[key] = {
        "status": status,
        "path": str(target),
        "size": target.stat().st_size,
        "sha256": actual_sha,
        "download_log": str(log) if log.exists() else "",
        "checksum_match": target.stat().st_size == expected_size and actual_sha.lower() == expected_sha.lower(),
    }
print(json.dumps(results, ensure_ascii=False))
'''
    remote_script = "/tmp/qwen36_dflash_modelscope_downloader.py"
    scp_script_to_remote(downloader, "/tmp/qwen36_dflash_modelscope_downloader.py", remote_script)
    items = [
        {
            "key": artifact.key,
            "remote_path": artifact.remote_path,
            "expected_size": expected[artifact.key]["size"],
            "expected_sha256": expected[artifact.key]["sha256"],
            "download_url": file_meta_by_key[artifact.key]["download_url"],
        }
        for artifact in ARTIFACTS
    ]
    payload = {"download_dir": REMOTE_DOWNLOAD_DIR, "items": items}
    raw = run_remote(
        "MODELSCOPE_TOKEN={token} DOWNLOAD_PAYLOAD={payload} python3 {script}".format(
            token=shlex.quote(token),
            payload=shlex.quote(json.dumps(payload, ensure_ascii=False)),
            script=shlex.quote(remote_script),
        ),
        timeout=7200,
    )
    result = parse_last_json(raw)
    save_json(output_root / "transfer" / "remote_download_meta.json", result)
    checksums = {
        key: {
            "gcp_size": expected[key]["size"],
            "gcp_sha256": expected[key]["sha256"],
            "remote_size": result[key]["size"],
            "remote_sha256": result[key]["sha256"],
            "match": result[key]["checksum_match"],
        }
        for key in result
    }
    save_json(output_root / "transfer" / "checksums.json", checksums)
    if not all(item["match"] for item in checksums.values()):
        raise RuntimeError(f"Remote checksum mismatch: {checksums}")
    return result


def cleanup_gcp_transfer_large_files(output_root: Path) -> dict[str, Any]:
    paths = [artifact.gcp_path for artifact in ARTIFACTS]
    script = f"""
set -euo pipefail
python3 - <<'PY'
import json
from pathlib import Path
paths = {paths!r}
deleted = []
for raw in paths:
    p = Path(raw)
    if p.exists():
        size = p.stat().st_size
        p.unlink()
        deleted.append({{"path": raw, "size": size}})
print(json.dumps({{"timestamp_utc": {utc_now()!r}, "deleted": deleted}}, ensure_ascii=False))
PY
"""
    payload = parse_last_json(run_jump(script, timeout=600))
    save_json(output_root / "cleanup" / "gcp_cleanup_post_transfer.json", payload)
    return payload


def setup_lucebox_build(output_root: Path) -> dict[str, Any]:
    script = f"""
set -euo pipefail
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${{LD_LIBRARY_PATH:-}}
if [ ! -d {shlex.quote(REMOTE_LUCEBOX)}/.git ]; then
  rm -rf {shlex.quote(REMOTE_LUCEBOX)}
  git clone --recurse-submodules https://github.com/Luce-Org/lucebox-hub {shlex.quote(REMOTE_LUCEBOX)}
else
  git -C {shlex.quote(REMOTE_LUCEBOX)} fetch origin
  git -C {shlex.quote(REMOTE_LUCEBOX)} checkout main
  git -C {shlex.quote(REMOTE_LUCEBOX)} pull --ff-only
  git -C {shlex.quote(REMOTE_LUCEBOX)} submodule update --init --recursive
fi
cd {shlex.quote(REMOTE_DFLASH)}
python3 - <<'PY'
from pathlib import Path
p = Path("CMakeLists.txt")
s = p.read_text()
s = s.replace('CUDA_ARCHITECTURES "86"', 'CUDA_ARCHITECTURES "89"')
p.write_text(s)
PY
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 > /tmp/qwen36_dflash_cmake.log 2>&1
cmake --build build --target smoke_load_target smoke_load_draft test_generate test_dflash -j > /tmp/qwen36_dflash_build.log 2>&1
python3 -m venv .venv
.venv/bin/pip -q install --disable-pip-version-check fastapi uvicorn transformers jinja2 huggingface_hub
python3 - <<'PY'
import json, subprocess
from pathlib import Path
root = Path({REMOTE_DFLASH!r})
def out(cmd):
    return subprocess.check_output(cmd, text=True).strip()
print(json.dumps({{
    "repo": str(root.parent),
    "commit": out(["git", "-C", str(root.parent), "rev-parse", "HEAD"]),
    "submodule": out(["git", "-C", str(root / "deps" / "llama.cpp"), "rev-parse", "HEAD"]),
    "target_exists": (root / "build" / "test_dflash").exists(),
    "cuda": out(["/usr/local/cuda/bin/nvcc", "--version"]).splitlines()[-1],
    "cmake_log": "/tmp/qwen36_dflash_cmake.log",
    "build_log": "/tmp/qwen36_dflash_build.log",
}}, ensure_ascii=False))
PY
"""
    raw = run_remote(script, timeout=7200)
    payload = parse_last_json(raw)
    save_json(output_root / "build" / "build_config.json", payload)
    cmake_log = run_remote("cat /tmp/qwen36_dflash_cmake.log || true", timeout=600)
    build_log = run_remote("cat /tmp/qwen36_dflash_build.log || true", timeout=600)
    save_text(output_root / "build" / "cmake_config.log", cmake_log)
    save_text(output_root / "build" / "build.log", build_log)
    return payload


def stop_services() -> None:
    remote_sudo(f"systemctl stop {BENCH_SERVICE} || true; systemctl stop {LIVE_SERVICE}", capture=False, timeout=300)
    time.sleep(3)


def restore_services(output_root: Path) -> dict[str, Any]:
    script = f"""
set -euo pipefail
pkill -f 'test_dflash.*--daemon' >/dev/null 2>&1 || true
pkill -f 'scripts/server.py.*18345' >/dev/null 2>&1 || true
pkill -f 'llama-server.*18344' >/dev/null 2>&1 || true
printf '%s\\n' {shlex.quote(REMOTE_PASSWORD)} | sudo -S -p '' systemctl start {LIVE_SERVICE}
sleep 15
python3 - <<'PY'
import json, subprocess, urllib.request
def run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True, check=False).stdout.strip()
payload = {{
    "live_active": run(["systemctl", "is-active", {LIVE_SERVICE!r}]),
    "bench_active": run(["systemctl", "is-active", {BENCH_SERVICE!r}]),
}}
try:
    with urllib.request.urlopen("http://127.0.0.1:18343/v1/models", timeout=20) as r:
        payload["models_status"] = r.status
        payload["models_raw"] = r.read().decode()
except Exception as exc:
    payload["models_error"] = repr(exc)
print(json.dumps(payload, ensure_ascii=False))
PY
"""
    payload = parse_last_json(run_remote(script, timeout=300))
    save_json(output_root / "summary" / "restore_status.json", payload)
    return payload


def run_dflash_smoke(output_root: Path) -> dict[str, Any]:
    script = f"""
set -euo pipefail
cd {shlex.quote(REMOTE_DFLASH)}
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${{LD_LIBRARY_PATH:-}}
export DFLASH_DRAFT={shlex.quote(REMOTE_DRAFT)}
target={shlex.quote(REMOTE_QWEN36_Q4)}
draft={shlex.quote(REMOTE_DRAFT)}
set +e
build/smoke_load_target "$target" > /tmp/qwen36_dflash_smoke_target.log 2>&1
st_target=$?
build/smoke_load_draft "$draft" > /tmp/qwen36_dflash_smoke_draft.log 2>&1
st_draft=$?
.venv/bin/python scripts/run.py --target "$target" --draft "$draft" --prompt "def fibonacci(n):" --n-gen 64 --budget 22 > /tmp/qwen36_dflash_run_stdout.log 2> /tmp/qwen36_dflash_run_stderr.log
st_run=$?
set -e
ST_TARGET="$st_target" ST_DRAFT="$st_draft" ST_RUN="$st_run" python3 - <<'PY'
import json, re
import os
from pathlib import Path
stdout = Path("/tmp/qwen36_dflash_run_stdout.log").read_text(errors="replace")
stderr = Path("/tmp/qwen36_dflash_run_stderr.log").read_text(errors="replace")
combined = stdout + "\\n" + stderr
tps = re.findall(r"→\\s+(\\d+\\.\\d+)\\s+tok/s", combined)
accept = re.findall(r"accepted=(\\d+)/(\\d+) \\((\\d+\\.\\d+)%", combined)
al = re.findall(r"avg commit/step=(\\d+\\.\\d+)", combined)
print(json.dumps({{
    "smoke_load_target_returncode": int(os.environ["ST_TARGET"]),
    "smoke_load_draft_returncode": int(os.environ["ST_DRAFT"]),
    "run_returncode": int(os.environ["ST_RUN"]),
    "stdout_preview": stdout[:2000],
    "stderr_tail": stderr[-4000:],
    "tok_s": float(tps[-1]) if tps else None,
    "accepted": accept[-1] if accept else None,
    "avg_commit_per_step": float(al[-1]) if al else None,
}}, ensure_ascii=False))
PY
"""
    payload = parse_last_json(run_remote(script, timeout=1800))
    save_json(output_root / "smoke" / "dflash_smoke.json", payload)
    for name in ["smoke_target", "smoke_draft", "run_stdout", "run_stderr"]:
        remote_file = {
            "smoke_target": "/tmp/qwen36_dflash_smoke_target.log",
            "smoke_draft": "/tmp/qwen36_dflash_smoke_draft.log",
            "run_stdout": "/tmp/qwen36_dflash_run_stdout.log",
            "run_stderr": "/tmp/qwen36_dflash_run_stderr.log",
        }[name]
        save_text(output_root / "smoke" / f"{name}.log", run_remote(f"cat {shlex.quote(remote_file)} || true", timeout=300))
    return payload


def run_dflash_bench(output_root: Path) -> dict[str, Any]:
    script = f"""
set -euo pipefail
cd {shlex.quote(REMOTE_DFLASH)}
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${{LD_LIBRARY_PATH:-}}
export DFLASH_TARGET={shlex.quote(REMOTE_QWEN36_Q4)}
export DFLASH_DRAFT={shlex.quote(REMOTE_DRAFT)}
.venv/bin/python scripts/bench_he.py --n-gen 128 --ddtree-budget 22 > /tmp/qwen36_dflash_he.log 2>&1
python3 - <<'PY'
import json, re
from pathlib import Path
text = Path("/tmp/qwen36_dflash_he.log").read_text(errors="replace")
rows = []
for line in text.splitlines():
    m = re.match(r"\\s*\\[(\\d+)\\]\\s+(.+?)\\s+(\\d+)\\s+(\\d+\\.\\d+)\\s+(\\d+\\.\\d+)\\s+(\\d+\\.\\d+)", line)
    if m:
        rows.append({{
            "index": int(m.group(1)),
            "prompt": m.group(2).strip(),
            "steps": int(m.group(3)),
            "al": float(m.group(4)),
            "accept_pct": float(m.group(5)),
            "tok_s": float(m.group(6)),
        }})
mean_tps = re.search(r"mean tok/s:\\s+(\\d+\\.\\d+)", text)
mean_al = re.search(r"mean AL:\\s+(\\d+\\.\\d+)", text)
print(json.dumps({{
    "rows": rows,
    "mean_tok_s": float(mean_tps.group(1)) if mean_tps else (sum(r["tok_s"] for r in rows) / len(rows) if rows else None),
    "mean_al": float(mean_al.group(1)) if mean_al else (sum(r["al"] for r in rows) / len(rows) if rows else None),
    "raw_tail": text[-4000:],
}}, ensure_ascii=False))
PY
"""
    payload = parse_last_json(run_remote(script, timeout=3600))
    save_json(output_root / "bench" / "dflash_he.json", payload)
    save_text(output_root / "bench" / "dflash_he.log", run_remote("cat /tmp/qwen36_dflash_he.log || true", timeout=300))
    return payload


def run_llama_baseline(output_root: Path) -> dict[str, Any]:
    bench_script = r'''
import json
import subprocess
import time
import urllib.request
from pathlib import Path

from scripts.bench_he import PROMPTS

cmd = [
    "/opt/llama.cpp/build/bin/llama-server",
    "-m", "/data/models/qwen/Qwen3.6-27B-UD-Q5_K_XL.gguf",
    "--alias", "bench/qwen36-q5-llama-baseline",
    "-ngl", "99",
    "-c", "131072",
    "-np", "1",
    "-fa", "on",
    "-ctk", "q4_0",
    "-ctv", "q4_0",
    "--temp", "0.2",
    "--top-p", "0.90",
    "--top-k", "20",
    "--min-p", "0.0",
    "--reasoning-format", "none",
    "--chat-template-kwargs", '{"enable_thinking": false}',
    "--host", "127.0.0.1",
    "--port", "18344",
]
log = open("/tmp/qwen36_llama_q5_baseline_server.log", "w")
proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)

def request_json(path, payload=None, timeout=30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"http://127.0.0.1:18344{path}", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())

result = {"cmd": " ".join(cmd), "rows": []}
try:
    deadline = time.time() + 240
    last = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited {proc.returncode}")
        try:
            status, payload = request_json("/v1/models", timeout=5)
            ids = [item.get("id") for item in payload.get("data", [])]
            if "bench/qwen36-q5-llama-baseline" in ids:
                result["models"] = payload
                break
            last = str(ids)
        except Exception as exc:
            last = repr(exc)
        time.sleep(3)
    else:
        raise RuntimeError(f"baseline model not ready: {last}")

    for i, (name, prompt) in enumerate(PROMPTS):
        t0 = time.time()
        status, payload = request_json("/v1/completions", {
            "model": "bench/qwen36-q5-llama-baseline",
            "prompt": prompt,
            "max_tokens": 128,
            "temperature": 0.2,
            "top_p": 0.9,
        }, timeout=180)
        elapsed = time.time() - t0
        usage = payload.get("usage", {})
        completion_tokens = usage.get("completion_tokens") or 0
        text = (payload.get("choices") or [{}])[0].get("text", "")
        result["rows"].append({
            "index": i,
            "prompt": name,
            "status": status,
            "elapsed_s": elapsed,
            "completion_tokens": completion_tokens,
            "tok_s": completion_tokens / elapsed if elapsed > 0 and completion_tokens else None,
            "think_polluted": "<think>" in text,
            "text_preview": text[:500],
            "usage": usage,
        })
finally:
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
    subprocess.run(["bash", "-lc", "pkill -9 -f 'llama-server.*18344' || true"], check=False)
    try:
        result["server_log_tail"] = Path("/tmp/qwen36_llama_q5_baseline_server.log").read_text(errors="replace")[-8000:]
    except Exception as exc:
        result["server_log_error"] = repr(exc)

rows = [r for r in result["rows"] if r.get("tok_s") is not None]
result["mean_tok_s"] = sum(r["tok_s"] for r in rows) / len(rows) if rows else None
result["think_polluted_count"] = sum(1 for r in result["rows"] if r.get("think_polluted"))
print(json.dumps(result, ensure_ascii=False))
'''
    remote_script = f"{REMOTE_DFLASH}/scripts/qwen36_q5_llama_baseline.py"
    scp_script_to_remote(bench_script, "/tmp/qwen36_q5_llama_baseline.py", remote_script)
    raw = run_remote(f"cd {shlex.quote(REMOTE_DFLASH)} && .venv/bin/python {shlex.quote(remote_script)}", timeout=3600)
    payload = parse_last_json(raw)
    save_json(output_root / "bench" / "llama_q5_he.json", payload)
    return payload


def run_api_smoke(output_root: Path) -> dict[str, Any]:
    smoke_script = r'''
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

env = {**os.environ, "DFLASH27B_KV_Q4": "1", "PATH": "/usr/local/cuda/bin:" + os.environ.get("PATH", ""), "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:" + os.environ.get("LD_LIBRARY_PATH", "")}
cmd = [
    ".venv/bin/python", "scripts/server.py",
    "--host", "127.0.0.1",
    "--port", "18345",
    "--target", "/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf",
    "--draft", "/data/models/qwen/dflash-draft",
    "--bin", "build/test_dflash",
    "--budget", "22",
    "--max-ctx", "131072",
]
log = open("/tmp/qwen36_dflash_api_server.log", "w")
proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, text=True, env=env)
result = {"cmd": " ".join(cmd)}

def request_json(path, payload=None, timeout=30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"http://127.0.0.1:18345{path}", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode()

try:
    deadline = time.time() + 240
    ready = False
    last = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited {proc.returncode}")
        try:
            status, raw = request_json("/v1/models", timeout=5)
            result["models"] = {"status": status, "raw": raw}
            ready = True
            break
        except Exception as exc:
            last = repr(exc)
        time.sleep(3)
    result["ready"] = ready
    result["ready_last_error"] = last
    if ready:
        t0 = time.time()
        status, raw = request_json("/v1/chat/completions", {
            "model": "luce-dflash",
            "messages": [{"role": "user", "content": "Reply READY only."}],
            "stream": False,
            "max_tokens": 16,
        }, timeout=180)
        result["non_stream"] = {"status": status, "elapsed_s": time.time() - t0, "raw": raw[:2000]}

        req = urllib.request.Request("http://127.0.0.1:18345/v1/chat/completions",
            data=json.dumps({
                "model": "luce-dflash",
                "messages": [{"role": "user", "content": "Write one Python function named add."}],
                "stream": True,
                "max_tokens": 32,
            }).encode(),
            headers={"Content-Type": "application/json"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=180) as r:
            chunks = []
            for line in r:
                chunks.append(line.decode(errors="replace"))
                if len(chunks) > 20:
                    break
        result["stream"] = {"status": 200, "elapsed_s": time.time() - t0, "preview": "".join(chunks)[:2000]}
finally:
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
    subprocess.run(["bash", "-lc", "pkill -9 -f 'scripts/server.py.*18345' || true; pkill -9 -f 'test_dflash.*--daemon' || true"], check=False)
    try:
        result["server_log_tail"] = Path("/tmp/qwen36_dflash_api_server.log").read_text(errors="replace")[-8000:]
    except Exception as exc:
        result["server_log_error"] = repr(exc)
print(json.dumps(result, ensure_ascii=False))
'''
    remote_script = f"{REMOTE_DFLASH}/scripts/qwen36_dflash_api_smoke.py"
    scp_script_to_remote(smoke_script, "/tmp/qwen36_dflash_api_smoke.py", remote_script)
    raw = run_remote(f"cd {shlex.quote(REMOTE_DFLASH)} && .venv/bin/python {shlex.quote(remote_script)}", timeout=1800)
    payload = parse_last_json(raw)
    save_json(output_root / "api" / "api_smoke.json", payload)
    return payload


def collect_gpu_sample(output_root: Path, name: str) -> None:
    raw = run_remote(
        "nvidia-smi --query-gpu=timestamp,name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader,nounits || true",
        timeout=60,
    )
    save_text(output_root / "gpu" / f"{name}.csv", raw)


def write_report(
    output_root: Path,
    cleanup: dict[str, Any],
    transfer: dict[str, Any],
    build: dict[str, Any],
    smoke: dict[str, Any] | None,
    dflash: dict[str, Any] | None,
    llama: dict[str, Any] | None,
    api: dict[str, Any] | None,
    restore: dict[str, Any],
) -> None:
    dflash_tps = dflash.get("mean_tok_s") if dflash else None
    llama_tps = llama.get("mean_tok_s") if llama else None
    speedup = (dflash_tps / llama_tps) if dflash_tps and llama_tps else None
    conclusion = "inconclusive"
    if dflash_tps and llama_tps:
        if dflash_tps >= 60 and dflash_tps > llama_tps:
            conclusion = "DFlash acceleration validated"
        elif dflash_tps < 50:
            conclusion = "DFlash did not reproduce expected throughput"
        else:
            conclusion = "DFlash ran but advantage is not decisive"
    payload = {
        "output_root": str(output_root),
        "conclusion": conclusion,
        "dflash_mean_tok_s": dflash_tps,
        "llama_q5_mean_tok_s": llama_tps,
        "speedup": speedup,
        "restore": restore,
        "api_ready": api.get("ready") if api else None,
    }
    save_json(output_root / "summary" / "comparison_summary.json", payload)
    report = f"""# Luce DFlash Qwen3.6-27B 4090 Validation

## Conclusion

{conclusion}

| Metric | Value |
|---|---:|
| DFlash Qwen3.6 Q4_K_M HumanEval mean tok/s | {dflash_tps if dflash_tps is not None else 'N/A'} |
| Qwen3.6 Q5_K_XL llama-server mean tok/s | {llama_tps if llama_tps is not None else 'N/A'} |
| DFlash / llama speedup | {round(speedup, 3) if speedup else 'N/A'} |
| DFlash smoke run returncode | {(smoke or {}).get('run_returncode', 'N/A')} |
| DFlash API ready | {(api or {}).get('ready', 'N/A')} |
| Restored live service | {restore.get('live_active')} |

## Artifacts

- cleanup/gcp_cleanup_preflight.json
- transfer/checksums.json
- build/build.log
- smoke/dflash_smoke.json
- bench/dflash_he.json
- bench/llama_q5_he.json
- api/api_smoke.json
- summary/comparison_summary.json

## Notes

- ModelScope token was read from the process environment and is not intentionally written to artifacts.
- DFlash uses Qwen3.6 Q4_K_M target plus the Qwen3.5-trained DFlash draft.
- This run validates the acceleration path only; it does not replace the production service.
"""
    save_text(output_root / "summary" / "final_report.md", report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="")
    parser.add_argument("--skip-transfer", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-bench", action="store_true")
    parser.add_argument(
        "--start-upload-job-only",
        action="store_true",
        help="Download artifacts to GCP, start detached ModelScope part upload, then exit.",
    )
    args = parser.parse_args()

    token = os.environ.get("MODELSCOPE_TOKEN", "")
    if not token and not args.skip_transfer:
        raise SystemExit("MODELSCOPE_TOKEN is required unless --skip-transfer is used")

    output_root = Path(args.output_root) if args.output_root else Path("output/qwen36-dflash-4090") / datetime.now().strftime("%Y%m%d-%H%M%S")
    output_root.mkdir(parents=True, exist_ok=True)

    cleanup = gcp_cleanup(output_root)
    transfer_result: dict[str, Any] = {}
    gcp_metas: dict[str, dict[str, Any]] = {}
    if not args.skip_transfer:
        hf_heads = {artifact.key: fetch_hf_head(artifact) for artifact in ARTIFACTS}
        save_json(output_root / "transfer" / "hf_head.json", hf_heads)
        for artifact in ARTIFACTS:
            gcp_metas[artifact.key] = gcp_download_artifact(artifact, hf_heads[artifact.key], output_root)
        if args.start_upload_job_only:
            start_modelscope_parts_upload_job(token, gcp_metas, output_root)
            return
        for artifact in ARTIFACTS:
            upload_artifact_to_modelscope(token, artifact, gcp_metas[artifact.key], output_root)
        write_and_upload_sha256s(token, gcp_metas, output_root)
        transfer_result = remote_download_artifacts(token, gcp_metas, output_root)
        cleanup_gcp_transfer_large_files(output_root)
    else:
        transfer_result = {"status": "skipped"}

    build_result = {"status": "skipped"} if args.skip_build else setup_lucebox_build(output_root)

    smoke_result = None
    dflash_result = None
    llama_result = None
    api_result = None
    restore_result: dict[str, Any] = {}
    if not args.skip_bench:
        try:
            stop_services()
            collect_gpu_sample(output_root, "after_stop")
            smoke_result = run_dflash_smoke(output_root)
            collect_gpu_sample(output_root, "after_dflash_smoke")
            dflash_result = run_dflash_bench(output_root)
            collect_gpu_sample(output_root, "after_dflash_bench")
            llama_result = run_llama_baseline(output_root)
            collect_gpu_sample(output_root, "after_llama_baseline")
            api_result = run_api_smoke(output_root)
            collect_gpu_sample(output_root, "after_api_smoke")
        finally:
            restore_result = restore_services(output_root)
    else:
        restore_result = {"status": "skipped"}

    write_report(output_root, cleanup, transfer_result, build_result, smoke_result, dflash_result, llama_result, api_result, restore_result)
    print(output_root)


if __name__ == "__main__":
    main()
