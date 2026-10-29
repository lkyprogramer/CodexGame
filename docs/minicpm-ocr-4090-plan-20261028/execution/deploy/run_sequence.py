"""Sequential G3/G4 campaigns plus two E0 runs. Default: print a static plan.

Run on host 29 only after both standard validations have terminal evidence.
The seven paired groups are unchanged run_campaign.py child processes. E0
reuses that module's guards, readiness, policy and Docker command helpers.
"""
from __future__ import annotations

import argparse
import datetime
import fcntl
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def build_plan(root, deploy, name):
    prepared = root / "corpus-extra/perf-prepared"
    groups = []
    for region in (1, 2, 4):
        groups.append((f"g3-r0-c{region}", "R0", "mixed100", 3, 4, region,
                       prepared / "r0-mixed100-manifest.json", prepared / "r0-warmup4-manifest.json"))
    for page in (1, 2, 4):
        groups.append((f"g4-d0-p{page}", "D0", "complete49", 6, page, 4,
                       prepared / "d0-complete3-49-manifest.json", prepared / "p0-dev4-manifest.json"))
    groups.append(("g4-p0-p1", "P0", "selected40", 6, 1, 4,
                   prepared / "p0-formal40-manifest.json", prepared / "p0-dev4-manifest.json"))
    campaigns = []
    for suffix, scope, workload, pairs, page, region, manifest, warmup in groups:
        group_name = f"{name}-{suffix}"
        args = ["python3", str(deploy / "run_campaign.py"), "--root", str(root), "--name", group_name,
                "--timing-scope", scope, "--workload", workload, "--pairs", str(pairs),
                "--page-admission", str(page), "--region-limit", str(region),
                "--manifest", str(manifest), "--warmup-manifest", str(warmup),
                "--idle-seconds", "10", "--ready-timeout", "900"]
        campaigns.append({"name": group_name, "timing_scope": scope, "workload": workload,
                          "pairs": pairs, "trials": pairs * 2, "page_admission": page, "region_limit": region,
                          "manifest": str(manifest), "warmup_manifest": str(warmup),
                          "command": args + ["--execute"], "plan_command": args + ["--plan-only"]})
    endurance = [{"name": f"{name}-e0-{candidate}", "candidate": candidate,
                  "manifest": str(root / "corpus-extra/endurance49/manifest.json"),
                  "warmup_manifest": str(prepared / "p0-dev4-manifest.json"),
                  "admission_window_seconds": 3600, "minimum_completed_pages": 300,
                  "page_admission": 4, "region_limit": 4, "cycles": 200}
                 for candidate in ("mini", "ovis")]
    assert len(campaigns) == 7 and sum(row["trials"] for row in campaigns) == 66
    assert sum(row["trials"] for row in campaigns if row["timing_scope"] == "R0") == 18
    return {"version": "ocr29-sequence-v1", "name": name, "root": str(root), "deploy": str(deploy),
            "campaign_group_count": 7, "paired_trial_count": 66, "endurance_run_count": 2,
            "campaigns": campaigns, "endurance": endurance,
            "warmup_note": "D0 and P0 groups use the same prepared development images; D0 formal inputs remain all 49 native PDF pages",
            "static_check": "PASS: R0 3x3 pairs=18 trials; D0 3x6 pairs=36; P0 6 pairs=12; no reduced rounds",
            "input_validation": "Static plan does not claim file/model validation; execution delegates campaign validation to build_plan",
            "failure_policy": "ordinary group failure retained, then continue; shared guard, lease or frozen-source failure stops the sequence"}


def load_helper(deploy):
    spec = importlib.util.spec_from_file_location("ocr_campaign_helpers", deploy / "run_campaign.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shared_refusal(group_state):
    if group_state.get("cleanup_error"):
        return str(group_state["cleanup_error"])
    messages = ("other task jobs are RUNNING", "compilation is active", "an execution/probe process is active",
                "unexpected /work mount", "Mini install must be PASS", "has active/queued requests",
                "queue metrics unavailable")
    for trial in group_state.get("trials", []):
        if trial.get("cleanup_error"):
            return str(trial["cleanup_error"])
        text = str(trial.get("error", ""))
        if any(message in text for message in messages):
            return text
        if trial.get("changed_execution_sources") or trial.get("changed_manifests"):
            return "campaign frozen sources/manifests changed"
    return None


def run_e0(helper, root, deploy, step, directory, frozen):
    candidate = step["candidate"]
    container = helper.CONTAINERS[candidate]
    directory.mkdir()
    out = root / "results" / step["name"]
    record = dict(step, status="RUNNING", wall_start=time.time(), monotonic_start=time.monotonic())
    sampler = None
    sampler_log = None
    owned = False
    with (directory / "commands.log").open("x") as log:
        try:
            helper.guard(root)
            changed = helper.changed_files(frozen)
            if changed:
                raise RuntimeError(f"sequence frozen files changed: {changed}")
            record["external_load_before"] = helper.external_load()
            for other in helper.CONTAINERS.values():
                if helper.inspect(other)["State"]["Running"]:
                    helper.command(["docker", "stop", "--time", "30", other], log=log)
            started = time.monotonic()
            helper.command(["docker", "start", container], log=log)
            owned = True
            info = helper.inspect(container)
            record["fresh_process"] = {"host_pid": info["State"]["Pid"], "started_at": info["State"]["StartedAt"]}
            sampler_log = (directory / "sampler.log").open("x")
            sampler = subprocess.Popen([sys.executable, str(deploy / "sample_resources.py"), "--container", container,
                                        "--out", str(directory / "resources.jsonl")], stdout=sampler_log, stderr=subprocess.STDOUT)
            helper.wait_ready(candidate, started + 900)
            record["load_to_api_ready_seconds"] = time.monotonic() - started
            policy_path = directory / "effective-runtime.json"
            helper.command([sys.executable, str(deploy / "capture_runtime_policy.py"), "--container", container,
                            "--out", str(policy_path)], log=log)
            runtime = json.loads(policy_path.read_text())
            if runtime["cpuset"] != "0-7":
                raise RuntimeError("E0 candidate cpuset differs from common 0-7")
            record["pre_idle"] = {"start_monotonic": time.monotonic()}
            helper.require_idle(candidate)
            time.sleep(10)
            helper.require_idle(candidate, evidence_path=directory / "api-before-warmup.prom")
            record["pre_idle"]["end_monotonic"] = time.monotonic()
            args = ["docker", "exec", "-e", "PYTHONPATH=/work", "-e", "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True",
                    "-e", "OMP_NUM_THREADS=8", "-e", "OPENBLAS_NUM_THREADS=8", "-e", "MKL_NUM_THREADS=8",
                    container, helper.PYTHONS[candidate], helper.mounted(root, deploy / "run_endurance.py"),
                    "--adapter", candidate, "--manifest", helper.mounted(root, Path(step["manifest"])),
                    "--warmup-manifest", helper.mounted(root, Path(step["warmup_manifest"])),
                    "--policy", helper.mounted(root, policy_path), "--out", helper.mounted(root, out),
                    "--model-dir", "/models/MiniCPM-OCR-1.0" if candidate == "mini" else "/models/OvisOCR3",
                    "--base-url", f"http://127.0.0.1:{helper.PORTS[candidate]}/v1", "--cycles", "200"]
            if candidate == "mini":
                args += ["--layout-model-dir", "/models/PP-DocLayoutV3_infer"]
            record["command"] = args
            helper.write_json(directory / "state.json", record)
            with (directory / "executor.log").open("x") as stream:
                result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, check=False)
            record["executor_exit_code"] = result.returncode
            summary = json.loads((out / "summary.json").read_text())
            state = json.loads(out.with_name(out.name + "-state").joinpath("state.json").read_text())
            record["endurance"] = {key: summary.get(key) for key in
                ("run_status", "endurance_status", "submitted_pages", "terminal_pages", "pass_pages", "not_admitted_pages",
                 "admission_window_seconds", "admission_stop_reason", "admission_elapsed_seconds", "drain_seconds",
                 "minimum_completed_pages_met", "admitted_workload_drained", "primary_performance_eligible")}
            record["entry_state_status"] = state["status"]
            record["post_idle"] = {"start_monotonic": time.monotonic()}
            helper.require_idle(candidate)
            time.sleep(10)
            helper.require_idle(candidate, evidence_path=directory / "api-after-idle.prom")
            record["post_idle"]["end_monotonic"] = time.monotonic()
            record["external_load_after"] = helper.external_load()
            record["status"] = "PASS" if result.returncode == 0 and state["status"] == "PASS" and summary.get("endurance_status") == "PASS" else "FAIL"
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
                if sampler.returncode != 0:
                    record.update(status="FAIL", resource_sampler_error="sampler did not exit cleanly")
            if sampler_log is not None:
                sampler_log.close()
            if record.get("fresh_process"):
                with (directory / "service.log").open("x") as stream:
                    try:
                        result = subprocess.run(["docker", "logs", "--timestamps", "--since", record["fresh_process"]["started_at"], container],
                                                stdout=stream, stderr=subprocess.STDOUT, timeout=30, check=False)
                        record["service_log_exit_code"] = result.returncode
                    except subprocess.SubprocessError as error:
                        record["service_log_error"] = str(error)
            try:
                if owned:
                    info = helper.inspect(container)
                    if info["State"]["Running"]:
                        if (info["State"]["Pid"] != record["fresh_process"]["host_pid"]
                                or info["State"]["StartedAt"] != record["fresh_process"]["started_at"]):
                            raise RuntimeError("candidate instance changed; leave the replacement untouched")
                        helper.require_idle(candidate)
                        helper.command(["docker", "stop", "--time", "30", container], log=log)
            except Exception as error:
                record.update(status="FAIL", cleanup_error=f"{type(error).__name__}: {error}")
            record["changed_execution_sources"] = helper.changed_files(frozen)
            if record["changed_execution_sources"]:
                record["status"] = "FAIL"
            record.update(wall_end=time.time(), wall_seconds=time.monotonic() - record["monotonic_start"])
            helper.write_json(directory / "state.json", record)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/data/ocr/dual-ocr-20261028"))
    parser.add_argument("--deploy-dir", type=Path)
    parser.add_argument("--name", default="g3g4-e0-r1")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", args.name):
        parser.error("use a fresh safe sequence name of at most 32 characters")
    root = args.root.resolve()
    deploy = (args.deploy_dir or root / "deploy").resolve()
    plan = build_plan(root, deploy, args.name)
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    helper = load_helper(deploy)
    with (root / "evidence/.sequence.lock").open("a") as sequence_lock:
        fcntl.flock(sequence_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        helper.guard(root)
        for group in plan["campaigns"]:
            helper.build_plan(root, Path(group["manifest"]), Path(group["warmup_manifest"]), group["name"],
                              timing_scope=group["timing_scope"], workload=group["workload"], pairs=group["pairs"],
                              page_admission=group["page_admission"], region_limit=group["region_limit"])
        e0_pages = json.loads(Path(plan["endurance"][0]["manifest"]).read_text())["pages"]
        if (len(e0_pages) != 49 or any(row.get("kind") != "image" or not row.get("expected_pixel_hash") for row in e0_pages)
                or len({row.get("expected_pixel_hash") for row in e0_pages}) != 49):
            raise ValueError("E0 requires the frozen 49 unique prepared page images")
        directory = root / "evidence" / f"sequence-{args.name}"
        directory.mkdir(exist_ok=False)
        paths = {Path(__file__).resolve(), deploy / "run_campaign.py", deploy / "run_endurance.py",
                 deploy / "capture_runtime_policy.py", deploy / "sample_resources.py", deploy / "serve.sh",
                 *(root / "ocrbench").glob("*.py")}
        for row in plan["campaigns"] + plan["endurance"]:
            paths.update((Path(row["manifest"]), Path(row["warmup_manifest"])))
        frozen = {str(path): helper.sha(path) for path in paths}
        plan["source_hashes"] = frozen
        plan["frozen_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        helper.write_json(directory / "plan.json", plan)
        records = []
        state = {"status": "RUNNING", "paired_trials_planned": 66, "endurance_runs_planned": 2, "steps": records}
        helper.write_json(directory / "state.json", state)
        try:
            for group in plan["campaigns"]:
                helper.guard(root)
                changed = helper.changed_files(frozen)
                if changed:
                    raise RuntimeError(f"sequence frozen files changed: {changed}")
                record = {"name": group["name"], "kind": "paired_campaign", "status": "RUNNING", "command": group["command"]}
                records.append(record)
                helper.write_json(directory / "state.json", state)
                with (directory / f"{group['name']}.log").open("x") as stream:
                    result = subprocess.run(group["command"], stdout=stream, stderr=subprocess.STDOUT, check=False)
                record["exit_code"] = result.returncode
                child_state = root / "evidence" / f"campaign-{group['name']}" / "state.json"
                if not child_state.is_file():
                    raise RuntimeError(f"campaign did not produce a terminal state: {group['name']}")
                observed = json.loads(child_state.read_text())
                record.update(status=observed["status"], completed_trials=len(observed.get("trials", [])), state=str(child_state))
                helper.write_json(directory / "state.json", state)
                if observed["status"] not in ("PASS", "FAIL") or len(observed.get("trials", [])) != group["trials"]:
                    raise RuntimeError(f"campaign has incomplete/unknown outcome: {group['name']}")
                refused = shared_refusal(observed)
                if refused:
                    raise RuntimeError(f"shared guard/freeze refused during campaign: {refused}")
                helper.guard(root)
            for step in plan["endurance"]:
                helper.guard(root)
                with (root / "evidence/.campaign.lock").open("a") as campaign_lock:
                    fcntl.flock(campaign_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    record = run_e0(helper, root, deploy, step, directory / step["name"], frozen)
                record["kind"] = "E0"
                records.append(record)
                helper.write_json(directory / "state.json", state)
                if record.get("cleanup_error") or record.get("changed_execution_sources"):
                    raise RuntimeError("E0 cleanup/frozen-source state requires attention; sequence stopped")
                refused = shared_refusal({"trials": [record]})
                if refused:
                    raise RuntimeError(f"shared guard refused during E0: {refused}")
                helper.guard(root)
            state["status"] = "PASS" if all(record["status"] == "PASS" and record.get("exit_code", 0) == 0 for record in records) else "FAIL"
        except BaseException as error:
            state.update(status="STOPPED", error=f"{type(error).__name__}: {error}")
            if records and records[-1]["status"] == "RUNNING":
                records[-1]["status"] = "UNKNOWN_OR_BLOCKED"
        finally:
            state["steps_not_run"] = 9 - len(records)
            state["utc_end"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            helper.write_json(directory / "state.json", state)
        return 0 if state["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
