#!/usr/bin/env python3
"""Schedule the reduced reference plan using the existing B29 collector unchanged."""
import argparse
import copy
import fcntl
import gzip
import json
import os
from pathlib import Path
import signal
import time
import traceback

from runner import Runner, MISSING, atomic, encode, sha, utc
from slim_plan import logical_ids, PRODUCTION


def intact(root, row):
    directory = Path(root) / "requests" / row["id"]
    try:
        if json.loads((directory / "record.json").read_text()) != row:
            return False
        if sha((directory / "raw.json.gz").read_bytes()) != row["raw_sha256"]:
            return False
        body = json.loads((directory / "request.json").read_text())
        return sha(encode(body)) == row["request_sha256"]
    except (OSError, ValueError, KeyError):
        return False


def choose_legacy_pair(root, rows, pair):
    candidates = [r for r in rows if r.get("group") == "core" and not r.get("failures")
                  and r.get("prompt_tokens") == pair["p"]
                  and r.get("target_prompt_tokens") == pair["p"]
                  and r.get("requested_output_tokens") == pair["o"]
                  and r.get("extra", {}).get("workload") == pair["workload"]
                  and r.get("extra", {}).get("track") == pair["track"]]
    candidates.sort(key=lambda r: (r["start_utc"], r["id"]))
    cold = next((r for r in candidates if r.get("cache") == "request_cold"
                 and r.get("result", {}).get("prefix_cache_hit_tokens") == 0
                 and r.get("result", {}).get("computed_prefill_tokens") == pair["p"]
                 and intact(root, r)), None)
    warm = next((r for r in candidates if cold and r.get("cache") == "warm_prefix"
                 and r.get("request_sha256") == cold["request_sha256"]
                 and r.get("result", {}).get("prefix_cache_hit_tokens", 0) > 0
                 and intact(root, r)), None)
    return cold, warm


def pi_body(private_root, case, seed):
    raw = (Path(private_root) / case["payload_file"]).read_bytes()
    if sha(raw) != case["payload_sha256"]:
        raise RuntimeError("Pi frozen payload hash mismatch")
    body = json.loads(raw)
    if body.get("max_tokens") != 32768:
        raise RuntimeError("unexpected frozen Pi output budget; no automatic reduction")
    body["stream"] = True
    body["stream_options"] = {"include_usage": True}
    body["seed"] = seed
    return body


def check_coding_handoff(root, manifest, manifest_sha):
    receipt = json.loads((Path(root) / "coding-handoff.json").read_text())
    cases = receipt.get("cases", [])
    if (receipt.get("manifest_sha256") != manifest_sha
            or receipt.get("known_completed_cases") != 8
            or receipt.get("unknown_outcomes") is not False
            or len(cases) != 8
            or {c.get("id") for c in cases} != set(manifest["coding_case_ids"])
            or any(c.get("repeat") != 1 or c.get("status") not in {"PASS", "FAIL", "OUTPUT_LIMIT"}
                   for c in cases)):
        raise RuntimeError("coding handoff is missing, incomplete, or belongs to another plan")
    return receipt


class SlimRunner(Runner):
    def __init__(self, root, stage):
        super().__init__(root)
        raw = (self.root / "manifest.json").read_bytes()
        self.manifest = json.loads(raw)
        if self.manifest["execution_plan"] != "slim_reference_v1":
            raise RuntimeError("not the authorized slim execution plan")
        self.stage = stage
        self.status.update(stage=stage, manifest_sha256=sha(raw),
                           execution_plan=self.manifest["execution_plan"])
        self.legacy = Path(self.manifest["legacy_root"])
        legacy_raw = (self.legacy / "records.jsonl").read_bytes()
        if sha(legacy_raw) != self.manifest["legacy_records_sha256"]:
            raise RuntimeError("legacy evidence changed since the stopped snapshot")
        if sha((self.legacy / "manifest.json").read_bytes()) != self.manifest["legacy_manifest_sha256"]:
            raise RuntimeError("legacy manifest changed")
        self.legacy_rows = [json.loads(line) for line in legacy_raw.splitlines()]
        if len(self.legacy_rows) != self.manifest["legacy_records_count"]:
            raise RuntimeError("legacy record count changed")
        if sha((self.root / "pi-private/manifest.json").read_bytes()) != self.manifest["pi_manifest_sha256"]:
            raise RuntimeError("Pi corpus manifest changed")
        for name, digest in self.manifest["scripts_sha256"].items():
            if sha((Path(__file__).parent / name).read_bytes()) != digest:
                raise RuntimeError(f"collector bundle changed: {name}")
        self.resolutions = {}
        ledger = self.root / "resolutions.json"
        if ledger.exists():
            previous = json.loads(ledger.read_text())
            if previous["manifest_sha256"] != self.status["manifest_sha256"]:
                raise RuntimeError("resolution ledger belongs to another plan")
            self.resolutions = previous["slots"]
        for ident in self.resolutions:
            self.resolved_row(ident)
        for pair in self.manifest["pairs"]:
            if pair["kind"] != "core" or pair["id"]+"-cold" in self.resolutions:
                continue
            cold, warm = choose_legacy_pair(self.legacy, self.legacy_rows, pair)
            for suffix, row in [("cold", cold), ("warm", warm)]:
                if row:
                    self.resolve(pair["id"]+"-"+suffix, self.legacy, row, "REUSED")
        self.update(state="PREPARING", resolved_reference_slots=len(self.resolutions))

    def resolved_row(self, ident):
        resolution = self.resolutions[ident]
        root = Path(resolution["source_root"])
        path = root / "requests" / resolution["source_id"] / "record.json"
        row = json.loads(path.read_text())
        if sha(encode(row)) != resolution["record_sha256"] or not intact(root, row):
            raise RuntimeError(f"resolved evidence lost integrity: {ident}")
        return row

    def resolve(self, ident, root, row, mode="COLLECTED"):
        if not intact(root, row):
            raise RuntimeError(f"cannot resolve corrupt evidence: {ident}")
        self.resolutions[ident] = {"mode": mode, "source_root": str(root), "source_id": row["id"],
                                   "record_sha256": sha(encode(row)), "request_sha256": row["request_sha256"],
                                   "raw_sha256": row["raw_sha256"]}
        atomic(self.root / "resolutions.json", {"manifest_sha256": self.status["manifest_sha256"],
                                                "slots": self.resolutions})

    def collect_pair(self, pair):
        cold_id, warm_id = pair["id"]+"-cold", pair["id"]+"-warm"
        if cold_id in self.resolutions and warm_id in self.resolutions:
            return
        if cold_id in self.resolutions:
            ref = self.resolutions[cold_id]
            body = json.loads((Path(ref["source_root"]) / "requests" / ref["source_id"] / "request.json").read_text())
        elif cold_id in self.results:
            body = json.loads((self.root / "requests" / cold_id / "request.json").read_text())
        else:
            original, _ = self.calibrate(pair["workload"], pair["p"])
            body = copy.deepcopy(original)
            nonce = f"{int(sha(pair['id'].encode())[:16], 16) % 10**16:016d}"
            body["messages"][0]["content"] = body["messages"][0]["content"].replace("0000000000000000", nonce)
            body.update(max_tokens=pair["o"], seed=20261020,
                        temperature=1 if pair["track"] == PRODUCTION else 0)
            body, _ = self.align_final_count(body, pair["p"], pair["id"])
        extra = {"track": pair["track"], "workload": pair["workload"], "block": 0,
                 "repetition": 0, "sample_role": "REFERENCE_ONLY", "p95_bucket": None}
        group = "core" if pair["kind"] == "core" else "long_output_8192"
        if cold_id not in self.resolutions:
            cold = self.request(cold_id, body, group=group, cache="request_cold",
                                expected_count=pair["p"], target=pair["p"], extra=extra)
            self.resolve(cold_id, self.root, cold)
        if warm_id not in self.resolutions:
            if self.status.get("last_completed_case") != cold_id and warm_id not in self.results:
                # This is an explicit priming observation, never a replacement for old cold evidence.
                self.request(pair["id"]+"-prime-"+str(time.time_ns()), body, group="resume_priming",
                             expected_count=pair["p"])
            warm = self.request(warm_id, body, group=group, cache="warm_prefix",
                                expected_count=pair["p"], target=pair["p"], extra=extra)
            self.resolve(warm_id, self.root, warm)

    def collect_pi(self, priority):
        for case in self.manifest["pi_cases"]:
            ident = "pi-"+case["id"]
            if (ident in self.manifest["priority_ids"]) != priority or ident in self.resolutions:
                continue
            body = pi_body(self.root / "pi-private", case, self.manifest["pi_seed"])
            counted, projection_error = None, None
            try:
                counted = self.count(body, ident)
            except (ValueError, KeyError, RuntimeError) as exc:
                projection_error = type(exc).__name__+": "+str(exc)[:200]
            row = self.request(ident, body, group="pi_teacher_forced", timeout=2400, port=18343,
                               extra={"source_sha256": case["source_sha256"], "entry_id": case["entry_id"],
                                      "qualification": self.manifest["pi_qualification"], "block": 0,
                                      "historical_budget_provenance": case["budget_provenance"],
                                      "mandatory_truncation": case["mandatory_truncation"],
                                      "projected_count": counted, "count_projection_error": projection_error,
                                      "cache_condition": "OBSERVED_SEQUENCE_WITH_GAPS_NOT_ASSUMED_APPEND"})
            self.resolve(ident, self.root, row)
            self.report()

    def selected_state(self):
        for p in [32768, 196608]:
            base, _ = self.calibrate("tool_json", p)
            base = copy.deepcopy(base)
            base.update(max_tokens=512, temperature=1, seed=20261020)
            name = f"state-P{p}-append1024"
            self.request(name+"-base", base, group="S3_append", target=p)
            appended = copy.deepcopy(base)
            assistant = self.assistant(name+"-base")
            appended["messages"].append(assistant)
            for tool in assistant.get("tool_calls", []):
                appended["messages"].append({"role": "tool", "tool_call_id": tool["id"],
                                             "content": json.dumps({"ok": True, "value": "fixture"})})
            appended["messages"].append({"role": "user", "content":
                ("Additional fixture constraint. "*1024)[:1024]+" Report the retry limit."})
            self.request(name+"-append", appended, group="S3_append", target=p,
                         extra={"append_characters": 1024, "actual_increment_tokens": "derive from server P"})
            changed = copy.deepcopy(appended)
            changed["messages"][-1]["content"] = "Correction: report retry limit 4."
            self.request(name+"-branch-B", changed, group="S4_S5_branch")
            self.request(name+"-branch-A", appended, group="S4_S5_branch")
            changed_system = copy.deepcopy(appended)
            changed_system["messages"][0]["content"] = "Updated system: report only verified records."
            self.request(name+"-system-change", changed_system, group="S4_system")
        base, _ = self.calibrate("copy_patch", 196608)
        base = copy.deepcopy(base)
        base.update(max_tokens=128, seed=20261020)
        self.request("l2-P196608-A", base, group="S6_L2")
        for workload in ["free_java", "chinese_analysis", "tool_json"]:
            body, _ = self.calibrate(workload, 196608)
            body = copy.deepcopy(body)
            body.update(max_tokens=128, seed=20261020)
            self.request("l2-P196608-pressure-"+workload, body, group="S6_L2")
        self.request("l2-P196608-return-A", base, group="S6_L2",
                     extra={"required_cache_source": "l2", "source_must_be_observed": True})

    def report(self):
        planned = logical_ids(self.manifest)
        observations, gaps = [], []
        for ident in planned:
            if ident not in self.resolutions:
                continue
            row = self.resolved_row(ident)
            observations.append({"logical_id": ident, "evidence": self.resolutions[ident], "record": row})
            if row["failures"]:
                gaps.append({"logical_id": ident, "failures": row["failures"]})
        pending = [ident for ident in planned if ident not in self.resolutions]
        result = {"schema_version": 2, "execution_plan": self.manifest["execution_plan"],
                  "manifest_sha256": self.status["manifest_sha256"], "updated_utc": utc(),
                  "planned": len(planned), "resolved": len(observations), "pending": pending,
                  "reused": sum(x["evidence"]["mode"] == "REUSED" for x in observations),
                  "collected": sum(x["evidence"]["mode"] == "COLLECTED" for x in observations),
                  "observations_with_gaps": gaps,
                  "state": "INCOMPLETE" if pending else "COLLECTED_WITH_GAPS" if gaps else "REFERENCE_COLLECTED",
                  "legacy_records_retained": self.manifest["legacy_records_count"],
                  "legacy_integrity_gaps": self.manifest["legacy_integrity_gaps"],
                  "optimization_qualification": False, "p95": None,
                  "p95_reason": "This reduced reference has no qualified p95 buckets or A/B confidence intervals",
                  "unavailable_metrics": MISSING, "observations": observations}
        atomic(self.root / "reference-report.json", result)
        self.update(resolved_reference_slots=len(observations), reused_reference_slots=result["reused"],
                    reference_pending=len(pending), reference_gap_count=len(gaps))
        self.summarize()
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--stage", choices=["priority", "remaining"], required=True)
    args = parser.parse_args()
    os.umask(0o077)
    root = Path(args.root).resolve()
    with (root.parent / "baseline-gpu.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner = SlimRunner(root, args.stage)
        runner.start_monitor()
        def stop(signum, _):
            runner.stop.set()
            runner.update(state="STOPPING", signal=signum)
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        try:
            runner.idle()
            runner.fingerprint(args.stage+"-startup-"+str(int(time.time())), full=True)
            if args.stage == "priority":
                runner.collect_pi(priority=True)
            else:
                if not all(ident in runner.resolutions for ident in runner.manifest["priority_ids"]):
                    raise RuntimeError("priority exception records must be completed first")
                check_coding_handoff(root, runner.manifest, runner.status["manifest_sha256"])
                runner.collect_pi(priority=False)
                for pair in runner.manifest["pairs"]:
                    runner.collect_pair(pair)
                    runner.report()
                runner.capacity_boundaries()
                runner.selected_state()
                runner.protocols_and_queue()
                for ident in runner.manifest["state_case_ids"]:
                    runner.resolve(ident, runner.root, runner.results[ident])
            runner.fingerprint(args.stage+"-end-"+str(int(time.time())))
            result = runner.report()
            if args.stage == "remaining" and result["pending"]:
                raise RuntimeError("required reference observations missing")
            runner.update(state="MEASUREMENT_STAGES_FINISHED", current_case=None,
                          request_deadline_utc=None, finished_utc=utc(),
                          qualification="REFERENCE_ONLY_NO_OPTIMIZATION_PASS")
            runner.report()
        except BaseException as exc:
            runner.update(state="NEEDS_ATTENTION", error=type(exc).__name__+": "+str(exc), finished_utc=utc())
            (root / "failure.txt").write_text(traceback.format_exc())
            runner.report()
            raise
        finally:
            runner.stop.set()


if __name__ == "__main__":
    main()
