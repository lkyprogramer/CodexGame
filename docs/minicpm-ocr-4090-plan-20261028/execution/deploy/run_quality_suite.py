"""Run the same diagnostic inputs for either adapter; retain every failed job."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", choices=["mini", "ovis"], required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--root", type=Path, default=Path("/work"))
    parser.add_argument("--repair-manifest", type=Path)
    parser.add_argument("--only", help="Run only the named job; preserve prior successful jobs")
    parser.add_argument("--build-interference", action="store_true")
    args = parser.parse_args()
    root = args.root
    evidence = root / "evidence" / f"{args.adapter}-quality-{args.tag}"
    evidence.mkdir(exist_ok=False)
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (root / "ocrbench").glob("*.py")}
    (evidence / "source-hashes.json").write_text(json.dumps(hashes, indent=2))
    policy = json.loads((root / "evidence" / f"{args.adapter}-effective-runtime.json").read_text())["policy"]
    base = [sys.executable, "-m", "ocrbench.cli", "--adapter", args.adapter,
            "--base-url", f"http://127.0.0.1:{18499 if args.adapter == 'mini' else 18500}/v1",
            "--model", "minicpm-ocr" if args.adapter == "mini" else "ovisocr3",
            "--model-dir", "/models/MiniCPM-OCR-1.0" if args.adapter == "mini" else "/models/OvisOCR3",
            "--region-limit", "4", "--option", "runtime_policy=" + json.dumps(policy),
            "--option", 'profile="C0-S0-quality-diagnostic"',
            "--option", "build_interference=" + json.dumps(args.build_interference)]
    if args.adapter == "mini":
        base += ["--layout-model-dir", "/models/PP-DocLayoutV3_infer"]
    jobs = []
    if args.repair_manifest:
        jobs.append(("repair", args.repair_manifest, []))
    extra = root / "corpus-extra"
    jobs += [("controls", extra / "controls/manifest.json", []),
             ("chart-page", extra / "controls/chart-manifest.json", []),
             ("faults", extra / "controls/fault-manifest.json", []),
             ("chart-region", extra / "controls/chart-region-manifest.json",
              ["--timing-scope", "R0", "--option", "region_task=chart"])]
    region_manifest = extra / "r0-300/manifest.json"
    cases = json.loads(region_manifest.read_text())["pages"]
    # Short handwritten names use the common 2048-token short-field ceiling.
    # Keep the frozen pixels/identities; preserve the earlier text-4096 run.
    cases = [dict(case, task="name", region_task="name") if "name" in case.get("scene_tags", [])
             else case for case in cases]
    for task in sorted({case["region_task"] for case in cases}):
        # Keep each document contiguous for admission/assembly. This changes only
        # execution order, never the fixed inputs or the failed-run denominator.
        selected = sorted((dict(case, path=str((region_manifest.parent / case["path"]).resolve()))
                           for case in cases if case["region_task"] == task),
                          key=lambda case: (case["document_id"], case["page_id"]))
        manifest = evidence / f"r0-{task}-manifest.json"
        manifest.write_text(json.dumps({"pages": selected}, ensure_ascii=False, indent=2))
        jobs.append((f"r0-{task}", manifest,
                     ["--timing-scope", "R0", "--page-admission", "4", "--option", f"region_task={task}"]))
    if args.only:
        jobs = [job for job in jobs if job[0] == args.only]
        if not jobs:
            raise ValueError("Unknown --only job")
    env = dict(os.environ, PYTHONPATH=str(root), PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK="True",
               OMP_NUM_THREADS="8", OPENBLAS_NUM_THREADS="8", MKL_NUM_THREADS="8")
    records = []
    for name, manifest, options in jobs:
        out = root / "results" / f"{args.adapter}-{name}-{args.tag}"
        command = base + ["--manifest", str(manifest), "--out", str(out)] + options
        record = dict(name=name, command=command, status="RUNNING", wall_start=time.time())
        records.append(record)
        status = evidence / "jobs.json"
        status.write_text(json.dumps(records, indent=2))
        with (evidence / f"{name}.log").open("xb") as stream:
            code = subprocess.call(command, stdout=stream, stderr=subprocess.STDOUT, env=env)
        record.update(exit_code=code, status="PASS" if code == 0 else "FAIL", wall_end=time.time())
        status.write_text(json.dumps(records, indent=2))
    return 0 if all(row["exit_code"] == 0 for row in records if row["name"] != "faults") else 1


if __name__ == "__main__":
    raise SystemExit(main())
