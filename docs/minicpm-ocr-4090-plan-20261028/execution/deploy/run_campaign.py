"""Task-owned, sequential paired 4090 campaign. Defaults to a read-only plan."""
from __future__ import annotations

import argparse
from collections import Counter
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

CONTAINERS = {"mini": "ocr29-mini-20261029", "ovis": "ocr29-ovis-20261029"}
PORTS = {"mini": 18499, "ovis": 18500}
MODELS = {"mini": "minicpm-ocr", "ovis": "ovisocr3"}
PYTHONS = {"mini": "/opt/minicpm-ocr/.venv-sdk-cpu/bin/python", "ovis": "/work/releases/ovis/bin/python"}
# Frozen before observing campaign results; A=mini, B=ovis. Three AB and three BA.
PAIR_ORDER = [("mini", "ovis"), ("ovis", "mini"), ("ovis", "mini"),
              ("mini", "ovis"), ("mini", "ovis"), ("ovis", "mini")]
REGION_TASKS = frozenset({"text", "name", "seal", "formula", "display_formula",
                          "inline_formula", "table", "chart"})


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_files(expected):
    changed = []
    for path, digest in expected.items():
        try:
            unchanged = Path(path).is_file() and sha(Path(path)) == digest
        except OSError:
            unchanged = False
        if not unchanged:
            changed.append(str(path))
    return changed


def mounted(root, path):
    resolved = path.resolve()
    if resolved.is_relative_to("/work"):
        return str(resolved)
    return str(Path("/work") / resolved.relative_to(root.resolve()))


def grouped_manifest(root, manifest):
    groups = {}
    for row in json.loads(manifest.read_text())["pages"]:
        entry = dict(row)
        source = Path(entry["path"])
        if not source.is_absolute():
            source = manifest.parent / source
        entry["path"] = mounted(root, source)
        groups.setdefault(entry["document_id"], []).append(entry)
    return {"pages": [row for group in groups.values() for row in group]}


def build_plan(root, manifest, warmup, name, *, timing_scope="D0", workload="selected40",
               pairs=6, page_admission=1, region_limit=4):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name):
        raise ValueError("campaign name must be safe ASCII")
    pages = json.loads(manifest.read_text())["pages"]
    development = json.loads(warmup.read_text())["pages"]
    if pairs not in {1, 3, 6} or page_admission not in {1, 2, 4} or region_limit not in {1, 2, 4}:
        raise ValueError("unsupported pair count or concurrency limit")
    if workload not in {"selected40", "complete49", "mixed100"} or timing_scope not in {"D0", "P0", "R0"}:
        raise ValueError("unsupported workload or timing scope")
    if (workload == "mixed100") != (timing_scope == "R0"):
        raise ValueError("mixed100 requires R0; R0 requires mixed100")
    expected_count = {"selected40": 40, "complete49": 49, "mixed100": 100}[workload]
    if len(pages) != expected_count or len(development) != 4:
        raise ValueError(f"campaign requires exactly {expected_count} formal and four development inputs")
    expected_unit = "crop" if workload == "mixed100" else "page"
    unit_inputs = pages + development if workload == "mixed100" else pages
    if any(row.get("unit_kind", "page") != expected_unit for row in unit_inputs):
        raise ValueError(f"the formal workload must contain {expected_unit} units only")
    pixels = [row.get("expected_pixel_hash") for row in pages]
    if any(not value for value in pixels) or len(set(pixels)) != expected_count:
        raise ValueError("formal RGB hashes must be present and unique")
    if len({row["page_id"] for row in pages}) != expected_count:
        raise ValueError("formal page IDs must be unique")
    if any(row.get("split") != "development" for row in development):
        raise ValueError("warmup inputs must be marked development")
    warm_families = {row.get("source_family_id") for row in development}
    if None in warm_families:
        raise ValueError("development source families must be specified")
    if workload != "mixed100" and any(row.get("source_family_id") in warm_families for row in pages):
        raise ValueError("development/formal source families must be disjoint")
    if timing_scope in {"P0", "R0"} and any(row.get("kind") != "image" for row in pages + development):
        raise ValueError(f"{timing_scope} formal and warmup inputs must be prepared images, never PDFs")
    task_counts = None
    if workload == "mixed100":
        if any(not isinstance(row.get("task"), str) or row["task"] not in REGION_TASKS for row in pages + development):
            raise ValueError("mixed100 requires an explicit public region task on every input")
        task_counts = Counter(row["task"] for row in pages)
        if task_counts != {"text": 70, "name": 20, "formula": 6, "seal": 2, "table": 2}:
            raise ValueError("mixed100 fixed task counts must be text70/name20/formula6/seal2/table2")
        if Counter(row["task"] for row in development) != {"text": 3, "name": 1}:
            raise ValueError("mixed100 warmup requires three text crops and one name crop")
        warm_pixels = [row.get("expected_pixel_hash") for row in development]
        if any(not value for value in warm_pixels) or len(set(warm_pixels)) != 4 or set(warm_pixels) & set(pixels):
            raise ValueError("R0 warmup RGB hashes must be present, unique and disjoint from formal crops")
    if workload == "complete49":
        if timing_scope != "D0" or any(row.get("kind") != "pdf" for row in pages):
            raise ValueError("complete49 requires original PDF inputs and D0 timing")
        documents = {}
        for row in pages:
            documents.setdefault(row["document_id"], []).append(row)
        counts = {"PDF-001": 15, "PDF-002": 26, "PDF-003": 8}
        if set(documents) != set(counts):
            raise ValueError("complete49 requires all three original PDF documents")
        for document, count in counts.items():
            rows = documents[document]
            if (len(rows) != count or [row.get("page_index", -1) for row in rows] != list(range(count))
                    or len({row["path"] for row in rows}) != 1):
                raise ValueError(f"complete49 must contain every original page exactly once: {document}")
    elif workload == "selected40" and len({row["document_id"] for row in pages}) < 20:
        raise ValueError("formal workload must cover at least 20 source documents")
    grouped = grouped_manifest(root, manifest)
    encoded = json.dumps(grouped, indent=2, ensure_ascii=False) + "\n"
    grouped_warmup = grouped_manifest(root, warmup)
    encoded_warmup = json.dumps(grouped_warmup, indent=2, ensure_ascii=False) + "\n"
    orders = {1: [("mini", "ovis")], 3: [("mini", "ovis"), ("ovis", "mini"), ("mini", "ovis")],
              6: PAIR_ORDER}[pairs]
    trials = [{"trial_id": f"{name}-p{pair + 1:02d}-{position + 1}-{candidate}",
               "pair": pair + 1, "position": position + 1, "candidate": candidate,
               "container": CONTAINERS[candidate]}
              for pair, order in enumerate(orders) for position, candidate in enumerate(order)]
    return {"version": "ocr29-paired-v3", "name": name, "profile": "C0-S0", "workload": workload,
            "pair_order": [list(pair) for pair in orders], "pair_count": pairs, "trials": trials,
            "statistics_scope": "SCAN_ONLY_NO_MAIN_SPEED_INFERENCE" if pairs == 1 else "PAIRED_RUNS_WITH_QUALITY_AND_REPORTING_GATES_PENDING",
            "pair_count_allows_main_speed_inference": pairs > 1,
            "formal_manifest": str(manifest), "formal_manifest_sha256": sha(manifest),
            "warmup_manifest": str(warmup), "warmup_manifest_sha256": sha(warmup),
            "fixed_denominator_per_trial": expected_count,
            "formal_document_count": len({row["document_id"] for row in pages}), "warmup_inputs": 4,
            "page_admission": page_admission, "region_limit": region_limit, "timing_scope": timing_scope,
            "task_counts": dict(task_counts) if task_counts is not None else None,
            "warmup_family_overlap": sorted(warm_families & {row.get("source_family_id") for row in pages}),
            "reference_scope": "R0 performance crops, RGB-disjoint warmup; family overlap allowed; not holdout quality evidence" if workload == "mixed100" else "source-family-disjoint development warmup",
            "manifest_mount": mounted(root, root / "evidence" / f"campaign-{name}" / "formal-manifest.json"),
            "warmup_mount": mounted(root, root / "evidence" / f"campaign-{name}" / "warmup-manifest.json"),
            "grouped_formal_manifest_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
            "grouped_warmup_manifest_sha256": hashlib.sha256(encoded_warmup.encode()).hexdigest(),
            "execution_page_order": [row["page_id"] for row in grouped["pages"]],
            "execution_warmup_order": [row["page_id"] for row in grouped_warmup["pages"]],
            "ordering_note": f"stable document grouping; original within-document selection order, all {expected_count} identities/pixels retained",
            "cache_note": "preaccessed/uncontrolled storage; fresh model process, same-worker warmup",
            "stop_rule": f"all {pairs * 2} trials once; no retries or result-dependent stopping"}


def command(args, *, timeout=60, log=None):
    result = subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    if log is not None:
        log.write(result.stdout)
        log.flush()
    return result.stdout


def inspect(container):
    return json.loads(command(["docker", "inspect", container]))[0]


def metrics(candidate, evidence_path=None):
    url = f"http://127.0.0.1:{PORTS[candidate]}/metrics"
    with urllib.request.urlopen(url, timeout=3) as response:
        raw = response.read().decode()
    if evidence_path is not None:
        Path(evidence_path).write_text(raw)
    totals = {"running": 0.0, "waiting": 0.0}
    found = set()
    for line in raw.splitlines():
        for suffix, key in [("num_requests_running", "running"), ("num_requests_waiting", "waiting")]:
            if re.match(rf"^vllm:{suffix}(?:\{{[^}}]*\}})?\s", line):
                totals[key] += float(line.split()[-1])
                found.add(key)
    if found != set(totals):
        raise RuntimeError("queue metrics unavailable; cannot establish an idle service")
    return totals


def require_idle(candidate, evidence_path=None):
    row = metrics(candidate, evidence_path=evidence_path)
    if row != {"running": 0.0, "waiting": 0.0}:
        raise RuntimeError(f"{candidate} has active/queued requests: {row}")


def external_load():
    row = {"monotonic": time.monotonic(), "host_loadavg": Path("/proc/loadavg").read_text().strip()}
    try:
        raw = command(["docker", "stats", "--no-stream", "--format", "{{json .}}",
                       "onnxocr-ppocrv6-small-cpu-compat"], timeout=10)
        row["existing_cpu_ocr"] = json.loads(raw)
    except (subprocess.SubprocessError, ValueError) as error:
        row["existing_cpu_ocr_error"] = str(error)
    return row


def guard(root):
    installed = json.loads((root / "evidence/install-mini-r3-job.json").read_text())
    if installed.get("status") != "PASS":
        raise RuntimeError("Mini install must be PASS before formal measurement")
    active = []
    for path in (root / "evidence").glob("*-job.json"):
        if json.loads(path.read_text()).get("status") == "RUNNING":
            active.append(path.name)
    if active:
        raise RuntimeError(f"other task jobs are RUNNING: {active}")
    build = "ocr29-build-20261028"
    if inspect(build)["State"]["Running"]:
        processes = command(["docker", "top", build, "-eo", "pid,comm"]).splitlines()
        names = {line.split(maxsplit=1)[1].strip() for line in processes[1:]}
        if names & {"nvcc", "ptxas", "cicc", "ninja", "cmake"}:
            raise RuntimeError("compilation is active; no formal measurement under build interference")
    for candidate, container in CONTAINERS.items():
        info = inspect(container)
        # Refuse to stop an unrelated container accidentally given this name.
        mounts = {item["Destination"]: item["Source"] for item in info["Mounts"]}
        if mounts.get("/work") != str(root.resolve()):
            raise RuntimeError(f"unexpected /work mount for {container}")
        if info["State"]["Running"]:
            names = command(["docker", "top", container, "-eo", "pid,args"])
            if re.search(r"(?:ocrbench\.(?:cli|extra_cli)|probe_(?:runtime|cancel)\.py|run_(?:quality_suite|endurance|standard_validation)\.py)", names):
                raise RuntimeError(f"an execution/probe process is active in {container}")
            require_idle(candidate)


def wait_ready(candidate, deadline):
    while time.monotonic() < deadline:
        if not inspect(CONTAINERS[candidate])["State"]["Running"]:
            raise RuntimeError("candidate container exited during startup")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORTS[candidate]}/v1/models", timeout=2) as response:
                data = json.load(response)
            if MODELS[candidate] in {row.get("id") for row in data.get("data", [])}:
                require_idle(candidate)
                return
        except (OSError, ValueError, RuntimeError):
            pass
        time.sleep(1)
    raise TimeoutError("candidate readiness deadline exceeded")


def trial_command(root, plan, trial, out, policy):
    candidate = trial["candidate"]
    args = ["docker", "exec", "-e", "PYTHONPATH=/work", "-e", "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True",
            "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "-e", "MKL_NUM_THREADS=8",
            CONTAINERS[candidate], PYTHONS[candidate], "-m", "ocrbench.cli",
            "--adapter", candidate, "--manifest", plan["manifest_mount"],
            "--warmup-manifest", plan["warmup_mount"], "--out", mounted(root, out),
            "--base-url", f"http://127.0.0.1:{PORTS[candidate]}/v1", "--model", MODELS[candidate],
            "--model-dir", "/models/MiniCPM-OCR-1.0" if candidate == "mini" else "/models/OvisOCR3",
            "--page-admission", str(plan["page_admission"]), "--region-limit", str(plan["region_limit"]),
            "--timing-scope", plan["timing_scope"],
            "--option", "profile=" + json.dumps(plan["profile"]), "--option", "build_interference=false",
            "--option", "runtime_policy=" + json.dumps(policy)]
    if candidate == "mini":
        args += ["--layout-model-dir", "/models/PP-DocLayoutV3_infer"]
    return args


def run_trial(root, plan, trial, directory, idle_seconds, ready_timeout):
    candidate, container = trial["candidate"], trial["container"]
    directory.mkdir()
    record = dict(trial, timing_scope=plan["timing_scope"], workload=plan["workload"],
                  fixed_denominator=plan["fixed_denominator_per_trial"],
                  page_admission=plan["page_admission"], region_limit=plan["region_limit"],
                  pair_count=plan["pair_count"], statistics_scope=plan["statistics_scope"],
                  status="RUNNING", wall_start=time.time(), monotonic_start=time.monotonic())
    sampler = None
    sampler_log = None
    started_by_this_trial = False
    out = root / "results" / trial["trial_id"]
    with (directory / "commands.log").open("x") as log:
        try:
            guard(root)
            for path_key, hash_key in [("formal_manifest", "formal_manifest_sha256"),
                                       ("warmup_manifest", "warmup_manifest_sha256")]:
                if sha(Path(plan[path_key])) != plan[hash_key]:
                    raise RuntimeError(f"campaign input manifest changed after freeze: {path_key}")
            for mount_key, hash_key in [("manifest_mount", "grouped_formal_manifest_sha256"),
                                        ("warmup_mount", "grouped_warmup_manifest_sha256")]:
                execution_manifest = root / Path(plan[mount_key]).relative_to("/work")
                if sha(execution_manifest) != plan[hash_key]:
                    raise RuntimeError(f"campaign execution manifest changed after freeze: {mount_key}")
            for source, digest in plan.get("source_hashes", {}).items():
                if sha(Path(source)) != digest:
                    raise RuntimeError(f"campaign software changed after freeze: {source}")
            record["external_load_before"] = external_load()
            for other in CONTAINERS.values():
                if inspect(other)["State"]["Running"]:
                    command(["docker", "stop", "--time", "30", other], log=log)
            start = time.monotonic()
            command(["docker", "start", container], log=log)
            started_by_this_trial = True
            info = inspect(container)
            record["fresh_process"] = {"host_pid": info["State"]["Pid"], "started_at": info["State"]["StartedAt"]}
            sampler_log = (directory / "sampler.log").open("x")
            sampler = subprocess.Popen([sys.executable, str(root / "deploy/sample_resources.py"),
                                        "--container", container, "--out", str(directory / "resources.jsonl")],
                                       stdout=sampler_log, stderr=subprocess.STDOUT)
            wait_ready(candidate, start + ready_timeout)
            record["load_to_api_ready_seconds"] = time.monotonic() - start
            policy_path = directory / "effective-runtime.json"
            command([sys.executable, str(root / "deploy/capture_runtime_policy.py"),
                     "--container", container, "--out", str(policy_path)], log=log)
            runtime = json.loads(policy_path.read_text())
            if runtime["cpuset"] != "0-7":
                raise RuntimeError("candidate cpuset differs from common 0-7")
            record["pre_idle"] = {"start_monotonic": time.monotonic()}
            require_idle(candidate)
            time.sleep(idle_seconds)
            require_idle(candidate, evidence_path=directory / "api-before-warmup.prom")
            record["pre_idle"]["end_monotonic"] = time.monotonic()
            args = trial_command(root, plan, trial, out, runtime["policy"])
            record["command"] = args
            write_json(directory / "trial.json", record)
            with (directory / "executor.log").open("x") as stream:
                # The executor enforces page/document/request deadlines and fixed denominator.
                result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, check=False)
            record["executor_exit_code"] = result.returncode
            summary = json.loads((out / "summary.json").read_text())
            warmup = json.loads((out / "warmup/summary.json").read_text())
            record["formal"] = {key: summary.get(key) for key in
                ("run_status", "timing_scope", "planned_pages", "submitted_pages", "terminal_pages", "pass_pages",
                 "batch_wall_seconds", "primary_performance_eligible", "performance_ineligibility_reason",
                 "pass_documents", "all_document_artifacts_pass", "job_wall_seconds_including_preflight_cold_warmup_shutdown")}
            record["warmup"] = {key: warmup.get(key) for key in
                ("status", "completed_warmup_inputs", "initial_warmup_wall_seconds", "total_warmup_worker_seconds")}
            record["post_idle"] = {"start_monotonic": time.monotonic()}
            require_idle(candidate)
            time.sleep(idle_seconds)
            require_idle(candidate, evidence_path=directory / "api-after-idle.prom")
            record["post_idle"]["end_monotonic"] = time.monotonic()
            record["external_load_after"] = external_load()
            record["status"] = "PASS" if (result.returncode == 0
                                            and summary.get("planned_pages") == plan["fixed_denominator_per_trial"]
                                            and summary.get("terminal_pages") == plan["fixed_denominator_per_trial"]
                                            and summary.get("timing_scope") == plan["timing_scope"]
                                            and summary.get("primary_performance_eligible")) else "FAIL"
        except Exception as error:
            record.update(status="FAIL", error=f"{type(error).__name__}: {error}")
        finally:
            if sampler is not None:
                sampler.terminate()
                try:
                    sampler.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    sampler.kill()
                    sampler.wait()
                record["sampler_exit_code"] = sampler.returncode
            if sampler_log is not None:
                sampler_log.close()
            if record.get("fresh_process"):
                try:
                    with (directory / "service.log").open("x") as stream:
                        result = subprocess.run(["docker", "logs", "--timestamps", "--since", record["fresh_process"]["started_at"],
                                                 container], stdout=stream, stderr=subprocess.STDOUT, check=False, timeout=30)
                    record["service_log_exit_code"] = result.returncode
                except subprocess.SubprocessError as error:
                    record["service_log_error"] = str(error)
            # Only the current task-owned model container; never the build or CPU OCR container.
            try:
                if started_by_this_trial and inspect(container)["State"]["Running"]:
                    require_idle(candidate)
                    command(["docker", "stop", "--time", "30", container], log=log)
            except Exception as error:
                record.update(status="FAIL", cleanup_error=f"{type(error).__name__}: {error}")
            record["changed_execution_sources"] = changed_files(plan.get("source_hashes", {}))
            manifests = {plan["formal_manifest"]: plan["formal_manifest_sha256"],
                         plan["warmup_manifest"]: plan["warmup_manifest_sha256"],
                         str(root / Path(plan["manifest_mount"]).relative_to("/work")): plan["grouped_formal_manifest_sha256"],
                         str(root / Path(plan["warmup_mount"]).relative_to("/work")): plan["grouped_warmup_manifest_sha256"]}
            record["changed_manifests"] = changed_files(manifests)
            if record["changed_execution_sources"] or record["changed_manifests"]:
                record["status"] = "FAIL"
            record.update(wall_end=time.time(), wall_seconds=time.monotonic() - record["monotonic_start"])
            write_json(directory / "trial.json", record)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/data/ocr/dual-ocr-20261028"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--warmup-manifest", type=Path)
    parser.add_argument("--timing-scope", choices=["D0", "P0", "R0"], default="D0")
    parser.add_argument("--workload", choices=["selected40", "complete49", "mixed100"], default="selected40")
    parser.add_argument("--pairs", type=int, choices=[1, 3, 6], default=6)
    parser.add_argument("--page-admission", type=int, choices=[1, 2, 4], default=1)
    parser.add_argument("--region-limit", type=int, choices=[1, 2, 4], default=4)
    parser.add_argument("--name", default="perf40-r1")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan-only", action="store_true", help="default; reads input manifests, does not invoke Docker")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--idle-seconds", type=float, default=10)
    parser.add_argument("--ready-timeout", type=float, default=900)
    args = parser.parse_args(argv)
    if args.idle_seconds < 5 or args.ready_timeout <= 0:
        parser.error("idle window must be at least five seconds and readiness timeout positive")
    root = args.root.resolve()
    manifest = (args.manifest or root / "corpus-extra/perf40/manifest.json").resolve()
    warmup = (args.warmup_manifest or root / "corpus/development-manifest.json").resolve()
    plan = build_plan(root, manifest, warmup, args.name, timing_scope=args.timing_scope, workload=args.workload,
                      pairs=args.pairs, page_admission=args.page_admission, region_limit=args.region_limit)
    if not args.execute:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0
    with (root / "evidence/.campaign.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        guard(root)
        directory = root / "evidence" / f"campaign-{args.name}"
        directory.mkdir(exist_ok=False)
        formal = grouped_manifest(root, manifest)
        write_json(directory / "formal-manifest.json", formal)
        write_json(directory / "warmup-manifest.json", grouped_manifest(root, warmup))
        if sha(directory / "formal-manifest.json") != plan["grouped_formal_manifest_sha256"]:
            raise RuntimeError("formal manifest changed after plan preparation")
        if sha(directory / "warmup-manifest.json") != plan["grouped_warmup_manifest_sha256"]:
            raise RuntimeError("warmup manifest changed after plan preparation")
        sources = [Path(__file__), root / "deploy/serve.sh", root / "deploy/capture_runtime_policy.py",
                   root / "deploy/sample_resources.py", *(root / "ocrbench").glob("*.py")]
        plan["source_hashes"] = {str(path): sha(path) for path in sources}
        plan["frozen_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_json(directory / "plan.json", plan)
        records = []
        write_json(directory / "state.json", {"status": "RUNNING", "trials": records})
        for trial in plan["trials"]:
            # Each trial rechecks active jobs/compilation and starts a new model process.
            record = run_trial(root, plan, trial, directory / trial["trial_id"], args.idle_seconds, args.ready_timeout)
            records.append(record)
            write_json(directory / "state.json", {"status": "RUNNING", "trials": records})
        passed = all(record["status"] == "PASS" for record in records)
        write_json(directory / "state.json", {"status": "PASS" if passed else "FAIL", "trials": records})
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
