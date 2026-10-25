#!/usr/bin/env python3
"""Frozen reference coverage, separate from candidate performance qualification."""
import argparse
import json
from pathlib import Path

from runner import LENGTHS, WORKLOADS, atomic, sha, utc

PRODUCTION = "production_sampling_29"
GREEDY = "research_greedy"
PRIORITY_ENTRIES = {"f89c5dcc", "97fc7be6"}
BOUNDARIES = [255, 256, 257, 511, 512, 513, 1023, 1024, 1025, 4095, 4096, 4097,
              262017, 262018, 262144, 262145]


def pair(kind, p, o, workload, track):
    return {"id": f"{kind}-P{p}-O{o}-{workload}-{track}", "kind": kind,
            "p": p, "o": o, "workload": workload, "track": track}


def measurement_pairs():
    pairs = [pair("core", p, 512, w, PRODUCTION) for p in LENGTHS for w in WORKLOADS
             if (p, w) != (256, "tool_json")]
    pairs += [pair("core", p, 512, w, GREEDY) for p in [1024, 32768, 131072, 253952]
              for w in ["copy_patch", "free_java"]]
    pairs += [pair("core", p, o, w, PRODUCTION) for p in [1024, 131072, 253952]
              for o in [128, 2048] for w in WORKLOADS]
    pairs += [pair("long", p, 8192, w, PRODUCTION) for p in [32768, 131072, 253952]
              for w in ["copy_patch", "free_java"]]
    return pairs


def state_ids():
    ids = [f"boundary-P{p}-O128" for p in BOUNDARIES]
    for stream in [False, True]:
        ids += [f"protocol-chat-{port}-{stream}" for port in [18030, 18343]]
        ids += [f"protocol-messages-{stream}", f"protocol-responses-{stream}"]
    ids += [f"queue-{n}-{i}" for n in [2, 4] for i in range(n)]
    ids += ["cancel-disconnect", "cancel-next-request", "unsupported-named-tool"]
    ids += [f"state-P{p}-append1024-{suffix}" for p in [32768, 196608]
            for suffix in ["base", "append", "branch-B", "branch-A", "system-change"]]
    ids += ["l2-P196608-A"] + [f"l2-P196608-pressure-{w}" for w in WORKLOADS[1:]]
    ids += ["l2-P196608-return-A"]
    return ids


def logical_ids(manifest):
    return ([p["id"] + "-" + cache for p in manifest["pairs"] for cache in ["cold", "warm"]]
            + ["pi-" + p["id"] for p in manifest["pi_cases"]] + manifest["state_case_ids"])


def build_manifest(pi_path, legacy_receipt, script_paths):
    raw = Path(pi_path).read_bytes()
    pi = json.loads(raw)
    cases = [{k: c[k] for k in ["id", "entry_id", "payload_file", "payload_sha256",
                               "source_sha256", "budget_provenance", "mandatory_truncation"]}
             for c in pi["cases"]]
    priority = ["pi-" + c["id"] for c in cases if c["entry_id"] in PRIORITY_ENTRIES]
    if len(cases) != 44 or len(priority) != 2:
        raise ValueError("frozen Pi corpus must contain 44 cases and the two known exception entries")
    manifest = {
        "schema_version": 2, "run_id": "b29-20261021-slim-v1", "created_utc": utc(),
        "execution_plan": "slim_reference_v1", "profile": "B29_UNCHANGED_ARGV",
        "remote_root": "/home/hhtele/ninfer-baseline-20261020/slim-v1",
        "script_root": "/home/hhtele/ninfer-baseline-20261020/slim-bin-v1",
        "legacy_root": "/home/hhtele/ninfer-baseline-20261020/formal",
        "legacy_records_count": legacy_receipt["records_count"],
        "legacy_records_sha256": legacy_receipt["records_sha256"],
        "legacy_manifest_sha256": legacy_receipt["manifest_sha256"],
        "legacy_integrity_gaps": legacy_receipt["raw_integrity_gaps"],
        "pairs": measurement_pairs(), "state_case_ids": state_ids(), "pi_cases": cases,
        "priority_ids": priority, "pi_manifest_sha256": sha(raw),
        "pi_qualification": pi["qualification"], "pi_repetitions": 1,
        "pi_output_budget_policy": "Preserve every frozen request max_tokens=32768; no reduction",
        "pi_seed": 20261020, "isolated_business_tasks": 8, "external_repository_tasks": 2,
        "closed_loop_repetitions": 1, "closed_loop_seeds": [1701],
        "coding_case_ids": ["java-agent-1-idempotency", "java-agent-2-retry-contract",
                            "java-agent-3-reconnect-loop", "qcb-BF009", "qcb-RE003",
                            "qcb-RE007", "qcb-AT005", "qcb-LC003"],
        "execution_order": ["two_pi_exceptions", "eight_engineering_tasks",
                            "external_repositories_if_ready", "remaining_reference_measurements",
                            "wait_and_run_any_pending_external_repositories"],
        "external_pending_policy": "Missing oracle/environment readiness does not block reference collection; both external judgments remain required for full completion",
        "reuse_policy": "Earliest intact compatible cold record and same-wire warm pair; never fastest/best; gaps retained",
        "sampling": {"temperature": 1, "top_p": .95, "top_k": 20, "presence_penalty": 0,
                     "reasoning_effort": "medium", "preserve_thinking": True},
        "greedy_scope": "Numerical diagnostic only; cannot qualify production sampling",
        "candidate_contract": "Future drafts greedy, target outputs sampling; no candidate/engine implementation in this run",
        "optimization_changes": False, "statistical_acceptance": "REFERENCE_ONLY_NO_P95_OR_OPTIMIZATION_PASS",
        "scripts_sha256": {Path(p).name: sha(Path(p).read_bytes()) for p in script_paths},
        "authority": "docs/ninfer-hyperqwen-v3-md-20261019/plans/05-baseline-29-execution.md",
    }
    manifest["expected_reference_requests"] = len(logical_ids(manifest))
    if manifest["expected_reference_requests"] != 278 or len(set(logical_ids(manifest))) != 278:
        raise ValueError("invalid slim reference coverage")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pi-manifest", required=True)
    parser.add_argument("--legacy-receipt", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--script", action="append", default=[])
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise RuntimeError("manifest already exists; retain it and create a versioned successor")
    atomic(output, build_manifest(args.pi_manifest, json.loads(Path(args.legacy_receipt).read_text()), args.script))


if __name__ == "__main__":
    main()
