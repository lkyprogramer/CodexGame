"""E0: one warmed worker pool, 60-minute admission window, then bounded drain.

The caller starts the fresh candidate server and captures its actual policy.
This entry point never starts or stops a container or server.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time

EXECUTION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXECUTION_ROOT))

from ocrbench.client import atomic_json
from ocrbench.core import load_manifest, run_pages


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def live_service_argv():
    return Path("/proc/1/cmdline").read_bytes().decode().strip("\0").split("\0")


def build_pool(pages, cycles):
    """Repeat identities with new operational IDs; keep original source pixels."""
    groups = {}
    for case in pages:
        groups.setdefault(case["document_id"], []).append(case)
    pool = []
    for cycle in range(1, cycles + 1):
        ordinal = 0
        for document_number, (document_id, cases) in enumerate(groups.items(), 1):
            for case in cases:
                ordinal += 1
                pool.append(dict(case, page_id=f"E0-C{cycle:04d}-P{ordinal:03d}",
                                 document_id=f"E0-C{cycle:04d}-D{document_number:03d}",
                                 source_id=case.get("source_id") or case["page_id"],
                                 original_page_id=case["page_id"], original_document_id=document_id,
                                 repetition_cycle=cycle))
    return pool


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", choices=["mini", "ovis"], required=True)
    parser.add_argument("--manifest", type=Path, required=True, help="The same frozen 40- or 49-page P0 workload for both candidates")
    parser.add_argument("--warmup-manifest", type=Path, required=True, help="Four RGB-disjoint development P0 images")
    parser.add_argument("--policy", type=Path, required=True, help="Actual capture_runtime_policy.py output")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--layout-model-dir", type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--cycles", type=int, default=200)
    args = parser.parse_args(argv)
    if args.cycles <= 0:
        parser.error("cycles must be positive")
    if args.adapter == "mini" and args.layout_model_dir is None:
        parser.error("Mini requires --layout-model-dir for CPU layout")
    pages = load_manifest(args.manifest.resolve())
    warmup = load_manifest(args.warmup_manifest.resolve())
    if len(pages) not in (40, 49) or len(warmup) != 4 or any(case["kind"] != "image" for case in pages + warmup):
        parser.error("E0 requires 40 or 49 formal P0 images and four development P0 images")
    if len({case.get("expected_pixel_hash") for case in pages}) != len(pages) or any(not case.get("expected_pixel_hash") for case in pages):
        parser.error("all base formal images must have distinct frozen RGB hashes")
    if any(case.get("split") != "development" for case in warmup):
        parser.error("warmup inputs must be marked development")
    if any(case.get("unit_kind", "page") != "page" for case in pages):
        parser.error("E0 is a repeated page workload, not a crop workload")
    policy = json.loads(args.policy.read_text())
    expected = {"dtype": "bfloat16", "max_model_len": 16384, "gpu_memory_utilization": .65,
                "max_num_seqs": 4, "max_num_batched_tokens": 8192, "cpu_cores": 8, "ram_gib": 32}
    if policy.get("policy") != expected or policy.get("cpuset") != "0-7":
        parser.error("captured policy must match the common BF16/16K/.65/seq4/CPU8/RAM32 policy and cpuset 0-7")
    if policy.get("argv") != live_service_argv():
        parser.error("captured policy argv differs from live /proc/1/cmdline")
    if args.out.exists():
        raise FileExistsError(args.out)
    state_dir = args.out.with_name(args.out.name + "-state")
    state_dir.mkdir(parents=True, exist_ok=False)
    pool = build_pool(pages, args.cycles)
    atomic_json(state_dir / "candidate-pool.json", {"pages": pool})
    atomic_json(state_dir / "runtime-policy.json", policy)
    sources = [Path(__file__).resolve(), *(EXECUTION_ROOT / "ocrbench").glob("*.py"),
               args.manifest.resolve(), args.warmup_manifest.resolve(), args.policy.resolve()]
    source_hashes = {str(path): digest(path) for path in sources}
    state = {"status": "RUNNING", "profile": "E0-endurance", "adapter": args.adapter,
             "utc_start": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "source_hashes": source_hashes, "candidate_pool_pages": len(pool), "unique_base_page_count": len(pages),
             "admission_window_seconds": 3600, "minimum_completed_pages": 300,
             "page_admission": 4, "region_limit": 4, "timing_scope": "P0",
             "worker_lifecycle": "one run_pages call; same warmed persistent worker pool",
             "quality_samples_added_by_repetition": 0, "container_lifecycle": "controlled by caller"}
    atomic_json(state_dir / "state.json", state)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "8"
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    started = time.monotonic()
    try:
        config = {"adapter": args.adapter, "out": str(args.out), "model_dir": str(args.model_dir),
                  "layout_model_dir": str(args.layout_model_dir) if args.layout_model_dir else None,
                  "base_url": args.base_url, "model": "minicpm-ocr" if args.adapter == "mini" else "ovisocr3",
                  "api_key": os.environ.get("OCR_API_KEY", "local-only"),
                  "execution_mode": "E0", "admission_window_seconds": 3600, "minimum_completed_pages": 300,
                  "timing_scope": "P0", "page_admission": 4, "region_limit": 4,
                  "page_timeout": 300, "document_timeout": 1800, "region_timeout": 120,
                  "options": {"profile": "E0-endurance", "runtime_policy": policy["policy"], "build_interference": False}}
        summary = run_pages(pool, config, warmup_pages=warmup)
        changed = [str(path) for path in sources if not path.is_file() or digest(path) != source_hashes[str(path)]]
        state.update(status="FAIL" if changed else summary["endurance_status"], changed_execution_sources=changed,
                     summary=str((args.out / "summary.json").resolve()))
        return 0 if state["status"] == "PASS" else 1
    except BaseException as error:
        state.update(status="FAIL", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        state.update(wall_seconds_including_preflight_warmup_drain=time.monotonic() - started,
                     utc_end=datetime.datetime.now(datetime.timezone.utc).isoformat())
        atomic_json(state_dir / "state.json", state)


if __name__ == "__main__":
    raise SystemExit(main())
