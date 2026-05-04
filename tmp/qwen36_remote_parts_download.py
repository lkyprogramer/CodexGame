#!/usr/bin/env python3
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


REPO = "wuniansky/Qwen3.6-27B-Q4_K_M"
MANIFEST = Path("/tmp/qwen36_dflash_modelscope_parts_manifest.json")
DOWNLOAD_DIR = Path("/data/models/qwen/.downloads/qwen36-dflash")
PARTS_DIR = DOWNLOAD_DIR / "parts"
TARGETS = {
    "Qwen3.6-27B-Q4_K_M.gguf": Path("/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf"),
    "draft/model.safetensors": Path("/data/models/qwen/dflash-draft/model.safetensors"),
}
PROGRESS = DOWNLOAD_DIR / "remote_parts_download_progress.jsonl"
STATE = DOWNLOAD_DIR / "remote_parts_download_state.json"
BASE_URL = f"https://www.modelscope.cn/models/{REPO}/resolve/master"


DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
PARTS_DIR.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(event: str, **fields) -> None:
    payload = {"ts": now(), "event": event, **fields}
    with PROGRESS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def write_state(status: str, **fields) -> None:
    STATE.write_text(
        json.dumps({"ts": now(), "status": status, **fields}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_part(part: dict) -> Path:
    destination = PARTS_DIR / Path(part["path"]).name
    expected_size = int(part["size"])
    expected_sha = part.get("sha256")
    if (
        destination.exists()
        and destination.stat().st_size == expected_size
        and (not expected_sha or sha256_of(destination).lower() == expected_sha.lower())
    ):
        emit("part_skip", path=part["path"], size=expected_size)
        return destination

    url = f"{BASE_URL}/{part['path']}"
    partial = destination.with_suffix(destination.suffix + ".partial")
    log = destination.with_suffix(destination.suffix + ".download.log")
    cmd = [
        "aria2c",
        "--continue=true",
        "--file-allocation=none",
        "--max-connection-per-server=8",
        "--split=8",
        "--min-split-size=16M",
        "--dir",
        str(PARTS_DIR),
        "--out",
        partial.name,
        url,
    ]
    emit("part_download_start", path=part["path"], size=expected_size, url=url)
    started = time.time()
    with log.open("w", encoding="utf-8") as handle:
        result = subprocess.run(cmd, text=True, stdout=handle, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        with log.open("a", encoding="utf-8") as handle:
            handle.write("\n--- curl fallback ---\n")
            result = subprocess.run(
                ["curl", "-L", "--retry", "5", "--retry-delay", "5", "-o", str(partial), url],
                text=True,
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
    if result.returncode != 0:
        raise RuntimeError(f"download failed: {part['path']} log={log}")
    if partial.stat().st_size != expected_size:
        raise RuntimeError(f"size mismatch: {part['path']} got={partial.stat().st_size} expected={expected_size}")
    if expected_sha and sha256_of(partial).lower() != expected_sha.lower():
        raise RuntimeError(f"sha mismatch: {part['path']}")
    os.replace(partial, destination)
    emit("part_download_done", path=part["path"], size=expected_size, elapsed_s=round(time.time() - started, 3))
    return destination


def main() -> None:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        emit("remote_download_job_start", artifacts=len(manifest["artifacts"]))
        results = []
        for artifact in manifest["artifacts"]:
            target = TARGETS[artifact["path"]]
            target.parent.mkdir(parents=True, exist_ok=True)
            if (
                target.exists()
                and target.stat().st_size == int(artifact["size"])
                and sha256_of(target).lower() == artifact["sha256"].lower()
            ):
                emit("artifact_skip", path=artifact["path"], target=str(target), status="already_present")
                results.append(
                    {
                        "path": artifact["path"],
                        "target": str(target),
                        "status": "already_present",
                        "sha256": artifact["sha256"],
                    }
                )
                continue
            parts = [download_part(part) for part in sorted(artifact["parts"], key=lambda item: int(item["index"]))]
            assembled = DOWNLOAD_DIR / artifact["source_name"]
            emit("artifact_assemble_start", path=artifact["path"], target=str(target), part_count=len(parts))
            with assembled.open("wb") as out:
                for part_path in parts:
                    with part_path.open("rb") as src:
                        for chunk in iter(lambda: src.read(16 * 1024 * 1024), b""):
                            out.write(chunk)
            actual_size = assembled.stat().st_size
            actual_sha = sha256_of(assembled)
            if actual_size != int(artifact["size"]) or actual_sha.lower() != artifact["sha256"].lower():
                raise RuntimeError(f"assembled mismatch: {artifact['path']} got size={actual_size} sha={actual_sha}")
            os.replace(assembled, target)
            emit("artifact_assemble_done", path=artifact["path"], target=str(target), size=actual_size, sha256=actual_sha)
            results.append(
                {
                    "path": artifact["path"],
                    "target": str(target),
                    "status": "downloaded",
                    "size": actual_size,
                    "sha256": actual_sha,
                }
            )
        write_state("done", results=results)
        emit("remote_download_job_done", results=results)
    except Exception as exc:
        write_state("failed", error=repr(exc))
        emit("remote_download_job_failed", error=repr(exc))
        raise


if __name__ == "__main__":
    main()
