"""Prepare the bounded P14 FFN replay in a new isolated tree; never starts a GPU process."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools/v027")]
import run_baseline as baseline
from lab.assets import verify as verify_assets
from lab.core import dump, gpu_inventory, gpu_lock, load_config, port_free, sha256

TASK = ROOT / "workspace/combination/oracle-replay-20261029"
TREE = ROOT / "workspace/trees/oracle-replay-20261029"
P6 = ROOT / "workspace/combination/v027-20261028"
P13 = ROOT / "workspace/combination/hc-scratch-20261028"
HC_TREE = ROOT / "workspace/trees/hc-scratch-20261028"


def prepare():
    if TASK.exists() or TREE.exists():
        raise RuntimeError("P14_DESTINATION_EXISTS: recover existing receipts, do not recreate")
    c = load_config(P13 / "config.json")
    p6c = load_config(P6 / "config.json")
    source = baseline.source_receipt(Path(p6c["deployed_repo"]), P6)
    hc = json.loads((P13 / "BUILD_COMPLETE.json").read_text())
    rel = "src/prefill/prefill.cpp"
    if sha256(HC_TREE / rel) != hc["patch"]["after_sha256"] or sha256(HC_TREE / "build-lab/strata") != hc["exe_sha256"]:
        raise RuntimeError("P13_SOURCE_OR_BINARY_DRIFT")
    assets = verify_assets(c)
    protected = baseline.combo.assert_protected(c, json.loads((P13 / "production-before.json").read_text())["file_sha256"])
    old = json.loads((P13 / "RAW_MANIFEST.json").read_text())
    for name, digest in old["files"].items():
        if sha256(P13 / name) != digest:
            raise RuntimeError("P13_RAW_DRIFT: " + name)
    tokens = next(x for x in json.loads((P13 / "tokens.json").read_text()) if x["name"] == "think-4096")
    if tokens["count"] != 4095 or sha256(Path(tokens["path"])) != tokens["sha256"]:
        raise RuntimeError("TOKEN_DRIFT")
    with gpu_lock(c["gpu_lock_workspace"]):
        service = baseline.combo.assert_service_inactive()
        gpu = gpu_inventory("0")
        port_free(18089)
        if gpu["compute_processes"]:
            raise RuntimeError("GPU_NOT_RELEASED")
        TASK.mkdir()
        dump(TASK / "HANDOFF.json", {"verified_utc": datetime.now(timezone.utc).isoformat(), "service": service,
             "gpu": gpu, "port_18089_free": True, "gpu_lock_acquired": True,
             "authorization": "user explicitly handed off GPU after stopping remaining OCR tests"})
    dump(TASK / "production-before.json", {"service": service, "file_sha256": protected})
    dump(TASK / "P6_SOURCE.json", source)
    dump(TASK / "P13_SOURCE.json", hc)
    dump(TASK / "P13_RAW_PROTECTION.json", old)
    dump(TASK / "ASSET_IDENTITY.json", {"check": "existing frozen SHA256 identities; current file set, size and mtime verified",
         "fresh_full_content_hash": False, "assets": assets})
    dump(TASK / "tokens.json", tokens)
    registration = {
        "schema": 1, "registered_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "same-process layer3 half1 FFN replay at actual p0=0,T=4090, from frozen 4095-token request",
        "source": source["native"]["source_sha"], "P13_prefill_sha256": hc["patch"]["after_sha256"],
        "tokens": tokens, "unchanged": ["original full P6 config", "CPUshare enabled and real CPU workers", "native math and MMQ reduction", "HC layout off for initial A"],
        "steps": ["capture first real FFN execution and exact CPU expert assignment",
                  "repeat same FFN in the same process with original inputs and recorded actual assignment",
                  "validate raw input, routing, resident and grouping identities before affected computation",
                  "compare effective CPU rows, GPU intermediates, Dm, shared/sg and bo byte for byte",
                  "reject deliberately changed actual input, dispatch identity and row mapping"],
        "branch_scope": "single GPU, !stream_all, !fused_l, no peer; unsupported actual branch rejects qualification",
        "coverage": "slot permutation covers T*K; CPU/GPU rows disjoint and complete; different Dm poison each pass prevents stale-output equality",
        "lifecycle": "one original HC read; each FFN pass has its own CPU future/stager lifetime; synchronize compute/copy before repeat; one original HC write",
        "identity": "memcmp/raw bytes, not digest-only proof; no padding or uninitialized GU/H CPU tail compared",
        "limits": {"native_requests_max": 6, "initial_positive_requests": 1, "negative_requests_max": 3,
                   "first_difference_localization_requests_max": 2, "max_context": 131072, "safety_tokens": 4096,
                   "gpu_abort_c": 85, "min_available_mib": 4096},
        "stop": ["any missing branch/input/dispatch identity: BLOCKED before B",
                 "same-execution A/A differs: retain first difference, at most two targeted diagnostic runs, no performance",
                 "all local checks pass: preregister expansion to complete half/chunk before additional GPU samples"],
        "not_proven_by_this_stage": ["cross-engine full logits equivalence", "complete KV/GDN/PLE state replay",
              "HC B/C equivalence", "natural C dispatch", "whole-request performance or quality"],
        "timing": "diagnostic synchronization and repeated adaptive timing change downstream dispatch; never performance samples",
        "formal_performance_samples": 0, "original_six_status": "FAIL_UNCHANGED", "production_writes": False,
    }
    dump(TASK / "PREREGISTRATION.json", registration)
    dump(TASK / "REGISTRATION_RECEIPT.json", {"registered_utc": registration["registered_utc"],
         "sha256": sha256(TASK / "PREREGISTRATION.json"), "gpu_requests_started": False})
    subprocess.run(["git", "-C", str(ROOT / "workspace/repo"), "worktree", "add", "--detach", str(TREE), baseline.TAG], check=True)
    for name, digest in source["python_port"]["files"].items():
        shutil.copy2(Path(p6c["deployed_repo"]) / name, TREE / name)
        if sha256(TREE / name) != digest:
            raise RuntimeError("PORT_COPY_DRIFT")
    shutil.copy2(HC_TREE / rel, TREE / rel)
    c["deployed_repo"] = str(TREE)
    c["request_timeout_s"] = 300
    c["gpu_monitor_interval_s"] = 1
    dump(TASK / "config.json", c)
    commands = json.loads((P13 / "build-commands.json").read_text())
    commands = [[str(x).replace(str(HC_TREE), str(TREE)) for x in cmd] for cmd in commands]
    # Keep compilation bounded while the unrelated CPU OCR service remains up.
    commands[1][-1] = "6"
    dump(TASK / "build-commands.json", commands)
    return {"state": "PREREGISTERED", "task": str(TASK), "tree": str(TREE),
            "registration_sha256": sha256(TASK / "PREREGISTRATION.json"), "old_raw_files_verified": old["count"]}


if __name__ == "__main__":
    print(json.dumps(prepare()), flush=True)
