"""Conservative v0.2.7 qualification and immutable P3 failure replay on lab 18089.

Quality failures are retained while other frozen failure classes run. HTTP,
resource, asset, source, or production drift stops the campaign. DEQUANT_SIDE
stays disabled; its separate campaign requires this correctness gate to pass.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools/combination"))
import run_combo as combo
import run_restore as restore
import run_boundaries as boundary
import run_chain as coding
from boundary_memory import MemorySampler
from lab import http, scoring
from lab.assets import verify as verify_assets
from lab.core import check_budget, dump, flag_value, gpu_inventory, gpu_lock, hash_obj, load_config, sha256
from lab.runner import evidence_lifecycle, make_run_config
from lab.tokenizer import StrataCounter

TAG = "5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d"
IMAGE = "sha256:ec7d6c95cd3692a2e2d228a8b1ca74e4025b54121fcc4c5da6f09cfa473315ad"
CONSERVATIVE = {"STRATA_DEFAULTS": "026", "STRATA_MMVQ_IL_89": "0",
                "STRATA_PROMPT_ATTN_IMMA": "0", "STRATA_KVA": "0",
                "STRATA_ROUTE_PRIOR": "0", "STRATA_DEQUANT_SIDE": "0",
                "STRATA_PLE_AUTO_RAM": "0"}


def source_receipt(tree, task):
    build = json.loads((task / "BUILD_COMPLETE.json").read_text())
    port = json.loads((task / "reply-pt-port.json").read_text())
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tree, text=True)
    if git("rev-parse", "HEAD").strip() != TAG or build["source_sha"] != TAG:
        raise RuntimeError("TAG_DRIFT")
    changed = set(git("diff", "--name-only").splitlines())
    if changed != set(port["files"]):
        raise RuntimeError("PORT_WRITE_SET_DRIFT")
    files = {name: sha256(tree / name) for name in port["files"]}
    if files != port["files"] or sha256(Path(build["exe"])) != build["exe_sha256"]:
        raise RuntimeError("PORT_OR_BINARY_DRIFT")
    if git("diff", "--binary") != (task / "reply-pt-v027.patch").read_text():
        raise RuntimeError("PATCH_DRIFT")
    return {"native": build, "python_port": port}


def frozen_failures(old):
    corpus = json.loads((old / "corpus.json").read_text())
    selected = restore.select_cases(corpus)
    boolean = next(case for case in corpus["cases"] if case["id"] == "schema-boolean")
    if boolean["request_sha256"] != hash_obj(boolean["body"]):
        raise ValueError("TOOL_REQUEST_DRIFT")
    originals = {}
    for line in (old / "restore/cfg/requests.jsonl").read_text().splitlines():
        row = json.loads(line)
        request = json.loads((old / "restore/cfg" / f'{row["target_tokens"]}-{row["stage"]}.request.json').read_text())
        if hash_obj(request) != row["request_sha256"]:
            raise ValueError("ORIGINAL_RESTORE_BODY_DRIFT")
        originals[(row["target_tokens"], row["stage"])] = request
    chain = json.loads((old / "live-chain/pair-01-cfg/turn-07.request.json").read_text())
    rows = [json.loads(x) for x in (old / "live-chain/pair-01-cfg/requests.jsonl").read_text().splitlines()]
    if hash_obj(chain) != rows[-1]["request_sha256"] or chain["seed"] != 43:
        raise ValueError("ORIGINAL_CODING_BODY_DRIFT")
    return selected, boolean, originals, chain


def correctness_pass(rows, error, fresh_chain):
    return (bool(rows) and error is None and fresh_chain is True
            and all(row["score"].get("pass") is True and row["restore"]["pass"] for row in rows))


def assert_kvres(cfg):
    if flag_value(cfg["args"], "--kv-resident") != "20480":
        raise ValueError("KVRES_MUST_STAY_20480")
    override = flag_value(cfg.get("user_args", []), "--kv-resident")
    if override is not None and override != "20480":
        raise ValueError("KVRES_OVERRIDE_DRIFT")


def activation_receipt(server):
    logs = "\n".join(path.read_text(errors="replace") for path in server.folder.glob("*.log"))
    required = [r"LAB_PR_1536 enabled=1", r"LAB_CFG_PT preserve_thinking default=0",
                r"prompt chunk auto: 16384 tokens",
                r"KV streaming: 20480 of 131072 cells per QSA layer in VRAM"]
    if any(re.search(pattern, logs) is None for pattern in required):
        raise RuntimeError("STARTUP_ACTIVATION_NOT_CONFIRMED")
    slots = re.findall(r"expert cache (\d+) slots", logs)
    if not slots or int(slots[-1]) <= 0:
        raise RuntimeError("AUTO_EXPERT_CACHE_NOT_AUDITABLE")
    return {"required_patterns": required, "confirmed": True, "expert_cache_slots": int(slots[-1]),
            "original_p3_slots": 10290, "policy": "preserve --expert-cache auto; record version-dependent slot count"}


def preflight(c, tree, task, out, old):
    if c["port"] != 18089 or c["max_context"] != 131072 or c.get("request_overrides"):
        raise ValueError("LAB_CONTRACT_DRIFT")
    if c["min_available_mib"] < 4096 or c["gpu_temp_abort_c"] > 85:
        raise ValueError("RESOURCE_GUARD_WEAKENED")
    cfg = make_run_config(c, tree, "cfg", {}, out)
    if Path(cfg["cwd"]).resolve() != tree or cfg["exe"] != str(tree / "build-lab/strata"):
        raise ValueError("ISOLATION_PATH_DRIFT")
    for key, value in {**combo.FROZEN_ENV, **CONSERVATIVE}.items():
        if cfg["env"].get(key) != value:
            raise ValueError("FROZEN_ENV_DRIFT: " + key)
    assert_kvres(cfg)
    original = json.loads((old / "input/production-frozen.json").read_text())
    relocated = json.loads(Path(c["deployed_config"]).read_text())
    for value in (original, relocated):
        for key in ("cwd", "exe", "log"):
            value.pop(key, None)
    if original != relocated:
        raise ValueError("ORIGINAL_CONFIG_CHANGED_BEYOND_RELOCATION")
    if json.loads((task / "python-qualification.json").read_text())["exit_code"] != 0:
        raise RuntimeError("PYTHON_QUALIFICATION_FAILED")
    if subprocess.check_output(["docker", "image", "inspect", "--format={{.Id}}", IMAGE], text=True).strip() != IMAGE:
        raise RuntimeError("GRADING_IMAGE_DRIFT")
    return source_receipt(tree, task)


class Replay:
    def __init__(self, c, server, counter, folder, memory):
        self.c, self.server, self.counter, self.folder, self.memory = c, server, counter, folder, memory
        self.rows = []

    def request(self, name, request, case=None, chain_turn=None, restore_min=None, frozen_hash=None):
        prefix = self.folder / name
        count = self.counter(request)
        check_budget(count, request["max_tokens"], self.c["max_context"], self.c["safety_tokens"])
        dump(Path(str(prefix) + ".request.json"), request)
        self.memory.stage = name
        self.memory.checkpoint(name + "-before")
        log = self.folder / "engine.log"
        offset = log.stat().st_size
        started = time.time()
        response = boundary.exchange(self.server, request, prefix, timeout=self.c["request_timeout_s"])
        dump(Path(str(prefix) + ".response.json"), response)
        with log.open("rb") as stream:
            stream.seek(offset)
            delta = stream.read().decode(errors="replace")
        Path(str(prefix) + ".engine.log").write_text(delta)
        grade_start = time.perf_counter()
        if chain_turn:
            score = coding.score_response(response, chain_turn, IMAGE)
        elif case:
            score = scoring.score(case, response)
        else:
            score = {"pass": not response.get("error") and response.get("done") is True and not response.get("tools"),
                     "reason": "protocol qualification"}
        restored = combo.restore_evidence({"expected_restore": restore_min is not None,
                                          "restore_min_tokens": restore_min or 64000}, delta)
        row = {"name": name, "started": started, "source_case_id": case["id"] if case else None,
               "request_sha256": hash_obj(request), "frozen_source_sha256": frozen_hash,
               "matches_frozen_body": hash_obj(request) == frozen_hash if frozen_hash else None,
               "local_prompt_tokens": count, "score": score, "restore": restored,
               "metrics": http.measurements(response), "grading_wall_s": time.perf_counter() - grade_start,
               "expected": case.get("expected") if case else None}
        self.rows.append(row)
        restore.append_record(self.folder / "requests.jsonl", row)
        self.memory.checkpoint(name + "-after")
        print(json.dumps(row), flush=True)
        if self.server.abort_reason or response.get("error"):
            raise RuntimeError("REQUEST_INFRASTRUCTURE: " + str(self.server.abort_reason or response.get("error")))
        if response.get("tools") and (not case or case["kind"] != "tool"):
            raise RuntimeError("UNAUTHORIZED_TOOL_OUTPUT")
        boundary.audit_usage(request, response, count, self.c)
        boundary.wait_idle(self.server, self.folder, name)
        return response, row


def qualification(replay):
    request = {"model": "strata", "messages": [{"role": "user", "content": "Remember PROBE-7319."},
               {"role": "assistant", "content": "Recorded.", "reasoning_content": "Earlier private reasoning. " * 32},
               {"role": "user", "content": "Return exactly OK."}], "max_tokens": 256,
               "temperature": 0, "seed": 20261028, "chat_template_kwargs": {"enable_thinking": True},
               "reasoning_budget_tokens": 32}
    default_count = replay.counter(request)
    disabled = copy.deepcopy(request)
    disabled["chat_template_kwargs"]["preserve_thinking"] = False
    enabled = copy.deepcopy(request)
    enabled["chat_template_kwargs"]["preserve_thinking"] = True
    if default_count != replay.counter(disabled) or replay.counter(enabled) <= default_count:
        raise RuntimeError("PT_RENDERING_NOT_QUALIFIED")
    for name, body in (("pt-default", request), ("pt-explicit-false", disabled), ("pt-request-true", enabled)):
        response, _ = replay.request(name, body)
        if response["usage"]["prompt_tokens"] != replay.counter(body):
            raise RuntimeError("PT_COUNTER_MISMATCH")
    first = {"model": "strata", "messages": [{"role": "user", "content": "Compute 17+25. Explain briefly, ending with 42."}],
             "max_tokens": 1024, "temperature": 0, "seed": 17, "reasoning_budget_tokens": 128,
             "chat_template_kwargs": {"enable_thinking": True, "preserve_thinking": True}}
    response, a = replay.request("reply-first", first)
    if not response.get("text") or response.get("finish_reason") != "stop":
        raise RuntimeError("REPLY_HISTORY_NOT_COMPLETE")
    second = copy.deepcopy(first)
    second["messages"] = restore.actual_history(first, response) + [{"role": "user", "content": "Return only the integer 42."}]
    _, b = replay.request("reply-followup", second)
    expected = a["metrics"]["prompt_tokens"] + a["metrics"]["generated_tokens"]
    reused = b["metrics"]["reused_tokens"]
    result = {"pt_default_false": True, "request_override_true": True,
              "first_prompt_plus_generated": expected, "followup_reused": reused,
              "reply_prefix_reused": type(reused) is int and reused >= expected - 4,
              "scope": "real generated history and engine cache counters; BPE split cases also covered by unit tests"}
    dump(replay.folder / "qualification.json", result)
    if not result["reply_prefix_reused"]:
        raise RuntimeError("REPLY_PREFIX_REUSE_NOT_OBSERVED")


def baseline(c, tree, task, old, out):
    selected, boolean, originals, chain = frozen_failures(old)
    receipt = preflight(c, tree, task, out, old)
    plan = {"tag": TAG, "source": receipt, "scope": "P3 immutable failures plus actual-history A/B/A lifecycle",
            "original_restore_hashes": {f"{t}-{s}": hash_obj(r) for (t, s), r in originals.items()},
            "tool_request_sha256": hash_obj(boolean["body"]), "coding_request_sha256": hash_obj(chain),
            "tool_policy": "one immutable body covers the three identical P3 failed request hashes; no statistical repair claim",
            "coding_policy": "frozen final turn first; fresh eight-turn seed43 chain required if all fixed cases pass",
            "quality_failure_policy": "retain and continue remaining original failure classes",
            "dequant_side": "0 throughout; separate run only after all correctness and lifecycle checks pass",
            "deployment_approved": False}
    out.mkdir(parents=True, exist_ok=False)
    dump(out / "campaign.json", plan)
    protected = combo.protected_hashes(c)
    dump(out / "production-before.json", {"service": combo.assert_service_inactive(), "file_sha256": protected})
    rows = []
    error = None
    fresh_chain_pass = False
    try:
        with gpu_lock(c["gpu_lock_workspace"]), evidence_lifecycle(c, out):
            verify_assets(c)
            dump(out / "cooldown-before.json", combo.wait_cool(c))
            folder = out / "cfg"
            with combo.combination_server(c, tree, "cfg", {}, folder) as server:
                activation = activation_receipt(server)
                live = Path(f'/proc/{server.engine_audit[0]["pid"]}/environ').read_bytes().split(b"\0")
                live = dict(x.decode().split("=", 1) for x in live if x.startswith(b"STRATA_"))
                if any(live.get(k) != v for k, v in {**combo.FROZEN_ENV, **CONSERVATIVE}.items()):
                    raise RuntimeError("ACTUAL_ENGINE_ENV_DRIFT")
                activation["live_strata_env"] = live
                dump(folder / "activation.json", activation)
                with MemorySampler(folder, lambda: boundary.descendants(server)) as memory:
                    counter = StrataCounter(tree, c["gguf"], c["template"])
                    replay = Replay(c, server, counter, folder, memory)
                    rows = replay.rows
                    qualification(replay)
                    for target in restore.TARGETS:
                        dump(folder / f"{target}-cooldown.json", combo.wait_cool(c, loaded=True))
                        cases = selected[target]
                        history = None
                        for stage in ("prime", "side", "restore", "sampled"):
                            frozen = originals[(target, stage)]
                            request = copy.deepcopy(cases[stage]["body"]) if stage in ("prime", "side") else restore.followup_request(history, cases[stage])
                            response, row = replay.request(f"{target}-{stage}", request, cases[stage],
                                                          restore_min=64000 if stage == "restore" else None,
                                                          frozen_hash=hash_obj(frozen))
                            if stage != "side":
                                history = restore.actual_history(request, response)
                            if not row["matches_frozen_body"]:
                                # Replay the original failed body too; do not confuse
                                # old-history accuracy with this engine's actual restore.
                                replay.request(f"{target}-{stage}-original", frozen, cases[stage], frozen_hash=hash_obj(frozen))
                    replay.request("schema-boolean", boolean["body"], boolean, frozen_hash=boolean["request_sha256"])
                    dump(folder / "coding-cooldown.json", combo.wait_cool(c, loaded=True))
                    replay.request("seed43-final-original", chain, chain_turn=8, frozen_hash=hash_obj(chain))
                    if all(r["score"].get("pass") is True and r["restore"]["pass"] for r in rows):
                        messages = [{"role": "system", "content": coding.chain.SYSTEM}]
                        start = time.perf_counter()
                        for turn, requirement in enumerate(coding.chain.REQS):
                            remaining = 2400 - (time.perf_counter() - start) - (60 * (turn + 1) + 90)
                            if remaining <= 1:
                                raise RuntimeError("FRESH_CHAIN_TASK_BUDGET")
                            replay.c = dict(c, request_timeout_s=min(c["request_timeout_s"], remaining))
                            request, _ = coding.request_for_turn(messages, requirement, 43, counter, c)
                            response, _ = replay.request(f"fresh-chain-{turn}", request, chain_turn=turn + 1)
                            messages = restore.actual_history(request, response)
                        fresh_chain_pass = (all(r["score"]["pass"] for r in rows)
                                            and time.perf_counter() - start <= 2400)
                        dump(folder / "fresh-chain-summary.json", {"wall_s": time.perf_counter() - start,
                                                                    "pass": fresh_chain_pass})
            if source_receipt(tree, task) != receipt:
                raise RuntimeError("SOURCE_RECEIPT_CHANGED")
    except BaseException as caught:
        error = f"{type(caught).__name__}: {caught}"
        raise
    finally:
        audit_error = None
        try:
            dump(out / "production-after.json", {"service": combo.assert_service_inactive(), "file_sha256": combo.assert_protected(c, protected),
                                                   "gpu": gpu_inventory(c["gpu"])})
        except Exception as caught:
            audit_error = f"FINAL_AUDIT: {caught}"
            error = error or audit_error
        passed = correctness_pass(rows, error, fresh_chain_pass)
        summary = {"state": "COMPLETE" if error is None else "BLOCKED_OR_FAILED", "error": error,
                   "requests": len(rows), "answer_failures": [r["name"] for r in rows if r["score"].get("pass") is not True],
                   "lifecycle_failures": [r["name"] for r in rows if not r["restore"]["pass"]],
                   "fresh_seed43_chain_pass": fresh_chain_pass,
                   "correctness_gate": "PASS" if passed else "FAIL", "dequant_side": "ELIGIBLE_SEPARATE_TEST" if passed else "NOT_RUN_CORRECTNESS_GATE",
                   "formal_quality_noninferiority": "NOT_ESTABLISHED", "production_changed": False, "deployment_approved": False}
        dump(out / "summary.json", summary)
        print(json.dumps(summary), flush=True)
        if audit_error:
            raise RuntimeError(audit_error)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    os.environ.update(STRATA_REPLY_REUSE="1", STRATA_PRESERVE_THINKING="0")
    result = baseline(config, args.tree.resolve(), args.config.resolve().parent, args.old.resolve(), args.out.resolve())
    raise SystemExit(0 if result["correctness_gate"] == "PASS" else 1)
