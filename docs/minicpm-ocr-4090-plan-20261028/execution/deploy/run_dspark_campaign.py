"""Mini standard/DSpark internal M1 A/B. Static by default; root authorizes execution.

Prerequisite: run_campaign.trial_command must consume plan.profile. Root must
complete standard C0/G3/G4/E0 and the initial real DSpark dev/counter gate first.
This runner does not establish quality acceptance or select a performance winner.
"""
from __future__ import annotations

import argparse
import datetime
import fcntl
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

PROFILE = "M1-DSPARK-S0"
CONTAINERS = {"standard": "ocr29-mini-20261029", "dspark": "ocr29-mini-dspark-20261029",
              "ovis": "ocr29-ovis-20261029"}
SPEC = {"method": "dspark", "model": "/models/MiniCPM-OCR-1.0-DSpark",
        "num_speculative_tokens": 15, "enable_adaptive_verification": False}
COUNTERS = ("spec_decode_num_drafts_total", "spec_decode_num_draft_tokens_total",
            "spec_decode_num_accepted_tokens_total", "spec_decode_num_accepted_tokens_per_pos_total")


def static_plan(root, name):
    prepared = root / "corpus-extra/perf-prepared"
    groups = []
    for scope, workload, pairs, page, formal, warmup, orders in [
        ("R0", "mixed100", 3, 4, "r0-mixed100", "r0-warmup4", ["AB", "BA", "AB"]),
        ("P0", "selected40", 6, 1, "p0-formal40", "p0-dev4", ["AB", "BA", "BA", "AB", "AB", "BA"]),
    ]:
        trials = []
        for pair, order in enumerate(orders, 1):
            for position, letter in enumerate(order, 1):
                variant = "standard" if letter == "A" else "dspark"
                trials.append({"trial_id": f"{name}-{scope.lower()}-p{pair:02d}-{position}-{variant}",
                               "pair": pair, "position": position, "candidate": "mini", "variant": variant,
                               "container": CONTAINERS[variant]})
        groups.append({"name": f"{name}-{scope.lower()}", "timing_scope": scope, "workload": workload,
                       "pairs": pairs, "page_admission": page, "region_limit": 4, "pair_order": orders,
                       "manifest": str(prepared / f"{formal}-manifest.json"),
                       "warmup_manifest": str(prepared / f"{warmup}-manifest.json"), "trials": trials})
    return {"version": "mini-dspark-m1-v1", "name": name, "root": str(root), "profile": PROFILE,
            "groups": groups, "trial_count": 18, "containers": CONTAINERS, "speculative_config": SPEC,
            "idle_seconds": 10, "ready_timeout": 900, "resource_sampling_hz": 1,
            "prerequisites": ["both-model C0/G3/G4/E0 terminal; root starts this phase",
                              "root completed initial real DSpark development/counter gate",
                              "run_campaign.trial_command consumes plan.profile; actual CLI profile checked"],
            "acceptance": "counter activity and protocol/performance evidence only; AI quality/reporting gates remain separate",
            "failure_policy": "ordinary data FAIL retained and continue; guard/freeze/cleanup/startup/counter/comparability failure STOP; remaining NOT_RUN"}


def load_helper(deploy):
    spec = importlib.util.spec_from_file_location("private_dspark_campaign_helper", deploy / "run_campaign.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def normalized_argv(argv, variant):
    """Only speculative-config may differ; require exactly the frozen config."""
    result = []
    configs = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--speculative-config":
            if index + 1 >= len(argv):
                raise RuntimeError("NOT_COMPARABLE: missing speculative-config value")
            configs.append(json.loads(argv[index + 1]))
            index += 2
        elif arg.startswith("--speculative-config="):
            configs.append(json.loads(arg.split("=", 1)[1]))
            index += 1
        else:
            result.append(arg)
            index += 1
    if configs != ([SPEC] if variant == "dspark" else []):
        raise RuntimeError("NOT_COMPARABLE: unexpected speculative configuration")
    return result


def counter_delta(before, after):
    def parse(raw, names):
        found = {}
        for line in raw.splitlines():
            match = re.match(r'^vllm:(spec_decode_[a-z_]+_total)(\{[^}]*\})?\s+(\S+)(?:\s+\S+)?$', line)
            if match and match[1] in names:
                value = float(match[3])
                if not math.isfinite(value) or value < 0:
                    raise RuntimeError("invalid speculative counter value")
                labels = match[2] or ""
                key = (match[1], labels)
                if key in found:
                    raise RuntimeError("duplicate speculative counter series")
                found[key] = value
        return found
    required = COUNTERS[:3]
    left, right = parse(before, required), parse(after, required)
    missing = [name for name in required if not any(key[0] == name for key in left)
               or not any(key[0] == name for key in right)]
    if missing:
        raise RuntimeError(f"DSpark counters missing (not zero): {missing}")
    if left.keys() != right.keys():
        raise RuntimeError("DSpark counter series changed within trial")
    deltas = {key: right[key] - value for key, value in left.items()}
    if any(value < 0 for value in deltas.values()):
        raise RuntimeError("DSpark counters reset within trial")
    totals = {name: sum(value for key, value in deltas.items() if key[0] == name) for name in required}
    if totals[COUNTERS[0]] <= 0 or totals[COUNTERS[1]] <= 0:
        raise RuntimeError(f"DSpark draft counters did not grow: {totals}")
    # Per-position series are diagnostics, outside the three-counter activity gate.
    # Missing/changed diagnostic data is never synthesized as zero.
    try:
        position_left, position_right = parse(before, COUNTERS[3:]), parse(after, COUNTERS[3:])
        if not position_left or not position_right:
            raise RuntimeError("per-position counter missing from one or both snapshots")
        if position_left.keys() != position_right.keys():
            raise RuntimeError("per-position counter series changed within trial")
        position_deltas = {key: position_right[key] - value for key, value in position_left.items()}
        if any(value < 0 for value in position_deltas.values()):
            raise RuntimeError("per-position counters reset within trial")
        per_position = {"status": "AVAILABLE", "series_deltas": [
            {"metric": key[0], "labels": key[1], "delta": value} for key, value in sorted(position_deltas.items())]}
    except (RuntimeError, ValueError) as error:
        per_position = {"status": "UNAVAILABLE", "reason": str(error)}
    return {"deltas": totals, "series_deltas": [{"metric": key[0], "labels": key[1], "delta": value}
                                                 for key, value in sorted(deltas.items())],
            "per_position": per_position,
            "acceptance_ratio": totals[COUNTERS[2]] / totals[COUNTERS[1]],
            "window": "before warmup through formal run and post idle (includes warmup)"}


def profile_check(args):
    options = [args[index + 1] for index, arg in enumerate(args[:-1]) if arg == "--option"]
    if [option for option in options if option.startswith("profile=")] != ["profile=" + json.dumps(PROFILE)]:
        raise RuntimeError("profile prerequisite unmet: helper must use plan.profile")
    if "/opt/minicpm-ocr/.venv-sdk-cpu/bin/python" not in args:
        raise RuntimeError("unexpected Mini CPU SDK interpreter")
    for flag, expected in [("--adapter", "mini"), ("--model", "minicpm-ocr"),
                           ("--base-url", "http://127.0.0.1:18499/v1"),
                           ("--layout-model-dir", "/models/PP-DocLayoutV3_infer"),
                           ("--model-dir", "/models/MiniCPM-OCR-1.0")]:
        if flag not in args or args[args.index(flag) + 1] != expected:
            raise RuntimeError(f"unexpected Mini CLI contract: {flag}")


def stop_reason(record):
    for key in ("cleanup_error", "changed_execution_sources", "changed_manifests"):
        if record.get(key):
            return f"{key}: {record[key]}"
    # Data failures reach executor and emit summaries. An exception before/after
    # that completed path is a control/startup/artifact failure, never six retries.
    if record.get("error"):
        return record["error"]
    if record.get("sampler_exit_code") != 0:
        return "resource sampler did not exit cleanly"
    if record.get("service_log_error") or record.get("service_log_exit_code") != 0:
        return "service log capture failed"
    return None


def wire_helper(helper, root, comparison):
    original_guard = helper.guard
    original_command = helper.command
    original_trial_command = helper.trial_command
    identities = {}
    active = {}
    # Existing helper now checks/stops all THREE task containers, including the
    # unselected Mini variant, with its own mount/process/queue checks.
    helper.CONTAINERS = {"mini": CONTAINERS["standard"], "other_mini": CONTAINERS["dspark"], "ovis": CONTAINERS["ovis"]}
    helper.PORTS["other_mini"] = 18499

    def guard(task_root):
        original_guard(task_root)
        running_minis = 0
        snapshots = {}
        for name in CONTAINERS.values():
            info = helper.inspect(name)
            snapshots[name] = (info["Id"], info["State"]["Pid"], info["State"]["StartedAt"], info["State"]["Running"])
            if info["State"]["Running"] and name in (CONTAINERS["standard"], CONTAINERS["dspark"]):
                running_minis += 1
        if running_minis > 1:
            raise RuntimeError("both Mini GPU instances running; refusing mutation")
        # Host controllers are not necessarily visible inside docker top.
        processes = original_command(["ps", "-eo", "pid=,args="])
        for line in processes.splitlines():
            if re.search(r'(?:^|[ /])(?:run_campaign|run_sequence|run_standard_validation|run_quality_suite|run_endurance|probe_runtime|probe_cancel)\.py(?:\s|$)', line):
                raise RuntimeError(f"active host controller/probe: {line.strip()}")
        active["guarded_container_identities"] = snapshots
        identities.clear()
        identities.update(snapshots)

    def command(args, **kwargs):
        if len(args) >= 3 and args[:2] == ["docker", "stop"]:
            name = args[-1]
            if name not in identities:
                raise RuntimeError("stop refused: no prior three-container guard")
            info = helper.inspect(name)
            current = (info["Id"], info["State"]["Pid"], info["State"]["StartedAt"], info["State"]["Running"])
            if current != identities[name]:
                raise RuntimeError("stop refused: container identity/PID changed")
            key = next(key for key, value in helper.CONTAINERS.items() if value == name)
            helper.require_idle(key)
        result = original_command(args, **kwargs)
        if len(args) == 3 and args[:2] == ["docker", "start"]:
            info = helper.inspect(args[2])
            identities[args[2]] = (info["Id"], info["State"]["Pid"], info["State"]["StartedAt"], info["State"]["Running"])
        return result

    def trial_command(task_root, plan, trial, out, policy):
        runtime = json.loads((active["directory"] / "effective-runtime.json").read_text())
        variant = trial["variant"]
        active["runtime"] = runtime
        if runtime["container"] != CONTAINERS[variant] or runtime["cpuset"] != "0-7":
            raise RuntimeError("NOT_COMPARABLE: runtime container/cpuset differs")
        expected = {"dtype": "bfloat16", "max_model_len": 16384, "gpu_memory_utilization": .65,
                    "max_num_seqs": 4, "max_num_batched_tokens": 8192, "cpu_cores": 8, "ram_gib": 32}
        if runtime["policy"] != expected:
            raise RuntimeError("NOT_COMPARABLE: effective policy differs")
        argv = runtime["argv"]
        processor = json.loads(argv[argv.index("--mm-processor-kwargs") + 1])
        if processor != {"downsample_mode": "4x", "max_slice_nums": 9}:
            raise RuntimeError("NOT_COMPARABLE: processor policy differs from 4x/9")
        normalized = normalized_argv(argv, variant)
        previous = comparison.setdefault("normalized_live_argv", normalized)
        if previous != normalized:
            raise RuntimeError("NOT_COMPARABLE: live argv differs beyond speculative-config")
        comparison.setdefault("observed", {})[variant] = runtime
        active["runtime"] = runtime
        args = original_trial_command(task_root, plan, trial, out, policy)
        profile_check(args)
        return args

    helper.guard, helper.command, helper.trial_command = guard, command, trial_command
    return active


def execute(root, deploy, plan, helper):
    if deploy != root / "deploy":
        raise ValueError("execute requires root/deploy: original helper resolves its scripts there")
    with (root / "evidence/.sequence.lock").open("a") as sequence_lock, (root / "evidence/.campaign.lock").open("a") as campaign_lock:
        fcntl.flock(sequence_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(campaign_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        directory = root / "evidence" / f"dspark-{plan['name']}"
        directory.mkdir(exist_ok=False)
        records = []
        state = {"status": "RUNNING", "trials": records, "performance_winner": "NOT_EVALUATED",
                 "quality_acceptance": "NOT_EVALUATED", "comparison": {}}
        helper.write_json(directory / "plan.json", plan)
        helper.write_json(directory / "state.json", state)
        active = wire_helper(helper, root, state["comparison"])
        try:
            helper.guard(root)
            sources = {Path(__file__).resolve(), deploy / "run_campaign.py", deploy / "run_sequence.py",
                       deploy / "serve.sh", deploy / "capture_runtime_policy.py", deploy / "sample_resources.py",
                       *(root / "ocrbench").glob("*.py")}
            sources.update(Path(group[key]) for group in plan["groups"] for key in ("manifest", "warmup_manifest"))
            frozen = {str(path): helper.sha(path) for path in sources}
            plan["source_hashes"] = frozen
            plan["frozen_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            helper.write_json(directory / "plan.json", plan)
            for group in plan["groups"]:
                child = helper.build_plan(root, Path(group["manifest"]), Path(group["warmup_manifest"]), group["name"],
                                          timing_scope=group["timing_scope"], workload=group["workload"],
                                          pairs=group["pairs"], page_admission=group["page_admission"], region_limit=4)
                child.update(profile=PROFILE, trials=group["trials"], pair_order=group["pair_order"], source_hashes=frozen)
                child_dir = root / "evidence" / f"campaign-{group['name']}"
                child_dir.mkdir(exist_ok=False)
                for filename, key in [("formal-manifest.json", "manifest"), ("warmup-manifest.json", "warmup_manifest")]:
                    helper.write_json(child_dir / filename, helper.grouped_manifest(root, Path(group[key])))
                helper.write_json(child_dir / "plan.json", child)
                for trial in group["trials"]:
                    changed = helper.changed_files(frozen)
                    if changed:
                        raise RuntimeError(f"frozen sources/manifests changed: {changed}")
                    variant = trial["variant"]
                    helper.CONTAINERS["mini"] = CONTAINERS[variant]
                    helper.CONTAINERS["other_mini"] = CONTAINERS["dspark" if variant == "standard" else "standard"]
                    active.clear()
                    active["directory"] = child_dir / trial["trial_id"]
                    try:
                        record = helper.run_trial(root, child, trial, active["directory"], 10, 900)
                    except BaseException as error:
                        path = active["directory"] / "trial.json"
                        record = json.loads(path.read_text()) if path.is_file() else dict(trial)
                        record.update(status="UNKNOWN_OR_BLOCKED", error=f"{type(error).__name__}: {error}")
                        records.append(record)
                        raise
                    records.append(record)
                    record["profile"] = PROFILE
                    record["effective_runtime"] = active.get("runtime")
                    record["guarded_container_identities"] = active.get("guarded_container_identities")
                    reason = stop_reason(record)
                    if not reason and variant == "dspark":
                        try:
                            record["speculative_counters"] = counter_delta(
                                (active["directory"] / "api-before-warmup.prom").read_text(),
                                (active["directory"] / "api-after-idle.prom").read_text())
                        except Exception as error:
                            record.update(status="FAIL", counter_error=f"{type(error).__name__}: {error}")
                            reason = record["counter_error"]
                    helper.write_json(active["directory"] / "trial.json", record)
                    helper.write_json(directory / "state.json", state)
                    if reason:
                        raise RuntimeError(reason)
            if set(state["comparison"].get("observed", {})) != {"standard", "dspark"}:
                raise RuntimeError("NOT_COMPARABLE: both live variants were not observed")
            state["status"] = "PASS" if all(record["status"] == "PASS" for record in records) else "FAIL"
        except BaseException as error:
            state.update(status="STOPPED", error=f"{type(error).__name__}: {error}")
        finally:
            done = {record["trial_id"] for record in records}
            state["not_run"] = [dict(trial, status="NOT_RUN") for group in plan["groups"] for trial in group["trials"] if trial["trial_id"] not in done]
            state["utc_end"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            helper.write_json(directory / "plan.json", plan)
            helper.write_json(directory / "state.json", state)
        return 0 if state["status"] == "PASS" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/data/ocr/dual-ocr-20261028"))
    parser.add_argument("--deploy-dir", type=Path)
    parser.add_argument("--name", default="m1-dspark-r1")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", args.name):
        parser.error("use a fresh safe name of at most 32 characters")
    root = args.root.resolve()
    plan = static_plan(root, args.name)
    if not args.execute:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0
    deploy = (args.deploy_dir or root / "deploy").resolve()
    return execute(root, deploy, plan, load_helper(deploy))


if __name__ == "__main__":
    sys.exit(main())
