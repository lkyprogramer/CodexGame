"""Run one preregistered P14 phase with the existing native driver and resource guards."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools/v027"), str(Path(__file__).parent)]
import prepare
import run_reference_logits as reference
from lab.core import dump, gpu_inventory, gpu_lock, load_config, sha256
from lab.assets import verify as verify_assets
from lab.runner import make_run_config, wait_released


def run(name, negative=None):
    task = prepare.TASK
    receipt = json.loads((task / "REGISTRATION_RECEIPT.json").read_text())
    if receipt["sha256"] != sha256(task / "PREREGISTRATION.json"):
        raise RuntimeError("REGISTRATION_DRIFT")
    if len(list(task.glob("*/plan.json"))) >= 6:
        raise RuntimeError("PREREGISTERED_REQUEST_BUDGET_EXHAUSTED")
    c = load_config(task / "config.json")
    source = reference.baseline.source_receipt(Path(load_config(prepare.P6 / "config.json")["deployed_repo"]), prepare.P6)
    build = json.loads((task / "BUILD_COMPLETE.json").read_text())
    if sha256(prepare.TREE / "build-lab/strata") != build["exe_sha256"] or sha256(prepare.TREE / "src/prefill/prefill.cpp") != build["source_sha256"]:
        raise RuntimeError("P14_BUILD_DRIFT")
    before = json.loads((task / "production-before.json").read_text())
    reference.baseline.combo.assert_service_inactive()
    reference.baseline.combo.assert_protected(c, before["file_sha256"])
    verify_assets(c)
    folder = task / name
    folder.mkdir(exist_ok=False)
    selected = json.loads((task / "tokens.json").read_text())
    if sha256(Path(selected["path"])) != selected["sha256"]:
        raise RuntimeError("TOKEN_DRIFT")
    prefix = folder / "empty-prefix.ids"
    prefix.write_text("\n")
    case = {"name": selected["name"], "tokens": selected, "prefix": {"path": str(prefix)}}
    c["extra_frozen_env"].update(STRATA_LAB_HC_REGION="0", STRATA_LAB_HC_KEEP_LOAN="0",
        STRATA_LAB_HC_MANIFEST="1", STRATA_LAB_REPLAY_DIR=str(folder / "replay"))
    if negative:
        c["extra_frozen_env"]["STRATA_LAB_REPLAY_NEGATIVE"] = negative
    cfg = make_run_config(c, prepare.TREE, "cfg", {}, folder)
    for key, value in {**reference.baseline.CONSERVATIVE, **reference.baseline.combo.FROZEN_ENV}.items():
        if cfg["env"].get(key) != value:
            raise RuntimeError("FROZEN_ENV_DRIFT: " + key)
    reference.baseline.assert_kvres(cfg)
    dump(folder / "plan.json", {"started_utc": datetime.now(timezone.utc).isoformat(),
         "registration_sha256": receipt["sha256"], "tokens": selected, "negative": negative,
         "exe_sha256": build["exe_sha256"], "source_sha256": build["source_sha256"],
         "args": cfg["args"], "strata_env": {k: v for k, v in cfg["env"].items() if k.startswith("STRATA_")},
         "native_requests": 1, "performance_sample": False, "P6_source": source})
    error = None
    try:
        with gpu_lock(c["gpu_lock_workspace"]):
            reference.baseline.combo.assert_service_inactive()
            dump(folder / "cooldown.json", reference.baseline.combo.wait_cool(c))
            try:
                reference.run_native(c, folder, [case])
            except Exception as exc:
                error = str(exc)
                dump(folder / "NATIVE_ERROR.json", {"error": error, "expected_negative": negative is not None})
            wait_released(c)
        dump(folder / "RUN_RESULT.json", {"native_error": error, "negative": negative,
             "original_six_status": "FAIL_UNCHANGED", "performance_sample": False,
             "note": "phase success requires replay records and byte analysis; native completion alone is insufficient"})
    except BaseException as exc:
        dump(folder / "FAILURE.json", {"error": str(exc), "partial_files_preserved": True})
        raise
    finally:
        dump(folder / "production-after.json", {"service": reference.baseline.combo.assert_service_inactive(),
             "file_sha256": reference.baseline.combo.assert_protected(c, before["file_sha256"]), "gpu": gpu_inventory("0")})
    return json.loads((folder / "RUN_RESULT.json").read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--negative", choices=["input", "dispatch", "mapping"])
    args = parser.parse_args()
    print(json.dumps(run(args.name, args.negative)), flush=True)
