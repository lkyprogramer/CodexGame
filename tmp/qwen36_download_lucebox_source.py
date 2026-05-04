#!/usr/bin/env python3
import hashlib
import json
import subprocess
from pathlib import Path


WORK = Path("/tmp/lucebox-source-ms")
MANIFEST = WORK / "manifest.json"
BASE_URL = "https://www.modelscope.cn/models/wuniansky/Qwen3.6-27B-Q4_K_M/resolve/master"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "parts").mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        subprocess.run(
            ["curl", "-L", "--retry", "5", "--retry-delay", "2", "-o", str(MANIFEST), f"{BASE_URL}/source/manifest.json"],
            check=True,
        )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    part_paths = []
    for part in sorted(manifest["parts"], key=lambda item: item["index"]):
        destination = WORK / "parts" / Path(part["path"]).name
        url = f"{BASE_URL}/{part['path']}"
        print(json.dumps({"event": "source_part_download_start", "path": part["path"], "size": part["size"]}), flush=True)
        subprocess.run(["curl", "-L", "--retry", "5", "--retry-delay", "2", "-o", str(destination), url], check=True)
        if destination.stat().st_size != int(part["size"]):
            raise SystemExit(f"size mismatch: {destination}")
        actual_sha = sha256_of(destination)
        if actual_sha.lower() != part["sha256"].lower():
            raise SystemExit(f"sha mismatch: {destination}")
        print(json.dumps({"event": "source_part_download_done", "path": part["path"]}), flush=True)
        part_paths.append(destination)
    output = WORK / "lucebox-hub-dflash-qwen36-src.tgz"
    with output.open("wb") as handle:
        for part_path in part_paths:
            with part_path.open("rb") as part_handle:
                for chunk in iter(lambda: part_handle.read(8 * 1024 * 1024), b""):
                    handle.write(chunk)
    actual_sha = sha256_of(output)
    if output.stat().st_size != int(manifest["size"]) or actual_sha.lower() != manifest["sha256"].lower():
        raise SystemExit(f"assembled mismatch: size={output.stat().st_size} sha={actual_sha}")
    print(
        json.dumps(
            {"event": "source_assembled", "path": str(output), "size": output.stat().st_size, "sha256": actual_sha},
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
