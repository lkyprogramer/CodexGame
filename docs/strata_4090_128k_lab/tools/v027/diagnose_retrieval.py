"""Bounded diagnosis of the immutable P3 retrieval failures; no engine edits.

The six original judgments remain exact string comparisons. Modified prompts
are labelled diagnostic controls and never replace an original acceptance row.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_baseline as baseline
from lab.core import dump, flag_value, gpu_inventory, gpu_lock, hash_obj, load_config
from lab.assets import verify as verify_assets
from lab.runner import evidence_lifecycle, make_run_config
from lab.tokenizer import StrataCounter

RECORD = re.compile(r"^config-entry id=(R\d+); immutable_value=([^;]+);", re.M)
QUERY = re.compile(r"immutable_value of (R\d+)\.")


def inspect_case(case, request, response):
    if hash_obj(request) != case["actual_request_sha256"]:
        raise ValueError("FROZEN_BODY_CHANGED")
    records = RECORD.findall(request["messages"][1]["content"])
    values = dict(records)
    if len(values) != len(records):
        raise ValueError("DUPLICATE_RECORD_ID")
    key = QUERY.findall(request["messages"][-1]["content"])[-1]
    if values.get(key) != case["expected"] or sum(value == case["expected"] for _, value in records) != 1:
        raise ValueError("GOLD_NOT_UNIQUE_LITERAL_INPUT_VALUE")
    return {"case": case["id"], "query": key, "gold": case["expected"], "records": len(records),
            "gold_unique_and_present": True, "actual": response["text"],
            "actual_prefix_matches": [{"id": k, "value": v, "row_delta": int(k[1:]) - int(key[1:])}
                                      for k, v in records if v.split("-")[0] == response["text"]],
            "finish_reason": response["finish_reason"], "generated_tokens": response["usage"]["completion_tokens"],
            "max_tokens": request["max_tokens"], "request_stop": request.get("stop"),
            "request_sha256": hash_obj(request)}


def controls(original):
    """Same full-string gold; distinguish literal copying, context and thinking."""
    request = original["body"]
    key = QUERY.findall(request["messages"][-1]["content"])[-1]
    short = copy.deepcopy(request)
    text = short["messages"][1]["content"]
    lines = text.splitlines()
    referenced = set(re.findall(r"R\d+", "\n".join(line for line in lines if not line.startswith("config-entry "))))
    # Keep all named records and their immediate neighbours, without changing
    # the original final question or injecting the gold into an instruction.
    wanted = {f"R{int(k[1:]) + d:06d}" for k in referenced for d in (-2, -1, 0, 1, 2)}
    short["messages"][1]["content"] = "\n".join(line for line in lines
        if not line.startswith("config-entry ") or line.split("id=", 1)[1].split(";", 1)[0] in wanted)
    literal = copy.deepcopy(request)
    literal["messages"][-1]["content"] = "Return exactly this complete literal string: " + original["expected"]
    explicit = copy.deepcopy(request)
    explicit["messages"][-1]["content"] += ("\nCopy the entire literal immutable_value string for " + key
        + ", including the hyphen and all six trailing digits. Do not omit any characters.")
    thinking = copy.deepcopy(request)
    thinking.update(reasoning_effort="low", chat_template_kwargs={"enable_thinking": True},
                    reasoning_budget_tokens=512, max_tokens=1536)
    return {"literal-copy": literal, "short-same-question": short,
            "long-explicit-format": explicit, "long-thinking": thinking}


def originals(old, prior):
    corpus = json.loads((old / "corpus.json").read_text())
    selected = baseline.restore.select_cases(corpus)
    result = []
    for target in baseline.restore.TARGETS:
        for stage in ("prime", "side", "restore", "sampled"):
            request = json.loads((prior / "baseline-v2/cfg" / f"{target}-{stage}.request.json").read_text())
            response = json.loads((prior / "baseline-v2/cfg" / f"{target}-{stage}.response.json").read_text())
            case = copy.deepcopy(selected[target][stage])
            case.update(body=request, actual_request_sha256=hash_obj(request), name=f"{target}-{stage}")
            # P6's literal actual history can differ from the canonical corpus.
            # Verify its identity against the retained P6 request ledger too.
            row = next(json.loads(line) for line in (prior / "baseline-v2/cfg/requests.jsonl").read_text().splitlines()
                       if json.loads(line)["name"] == case["name"])
            if row["request_sha256"] != case["actual_request_sha256"]:
                raise ValueError("P6_SOURCE_BODY_DRIFT")
            result.append((case, response))
    return result


def rendering_audit(counter, cases, folder):
    tok, frontend = counter.tokenizer, counter.frontend
    stop_ids = set(tok.encode("<|im_end|>", parse_special=True) + tok.encode("<|endoftext|>", parse_special=True))
    result = []
    for case, _ in cases:
        if case["name"].endswith("side"):
            continue
        request = case["body"]
        messages, tools, kwargs = frontend.openai_to_messages(copy.deepcopy(request))
        text = counter.template.render(messages, tools=tools, **kwargs)
        ids = tok.encode(text, parse_special=True)
        decoded = tok.decode(ids)
        if decoded != text or case["expected"] not in decoded:
            raise RuntimeError("PROMPT_TOKENIZATION_LOST_TEXT")
        gold_ids = tok.encode(case["expected"])
        if tok.decode(gold_ids) != case["expected"] or set(gold_ids) & stop_ids:
            raise RuntimeError("VALUE_TOKENIZATION_OR_STOP_COLLISION")
        (folder / (case["name"] + ".rendered.txt")).write_text(text)
        result.append({"name": case["name"], "rendered_sha256": hash_obj(text), "roundtrip_exact": True,
                       "gold_present": True, "gold_ids": gold_ids, "stop_ids": sorted(stop_ids),
                       "hyphen_ids": tok.encode("-"), "kwargs": kwargs, "prompt_tokens": len(ids)})
    dump(folder / "rendering-audit.json", result)
    return stop_ids


def run(c, task, prior, old, phase, name):
    tree = Path(c["deployed_repo"])
    source = baseline.source_receipt(tree, prior)
    cases = originals(old, prior)
    indexed = {case["name"]: case for case, _ in cases}
    audits = [inspect_case(case, case["body"], response) for case, response in cases if not case["name"].endswith("side")]
    dump(task / "original-case-audit.json", audits)
    # Native mixed blobs turn N into a byte budget and then size actual slots.
    # Keep this budget below both arms' free VRAM; audit equal actual counts.
    common = {"--expert-cache": "6000"}
    ready = {"common": {"args": common, "env": {"STRATA_DEBUG": "1"}}}
    if phase == "no-mtp":
        ready["cfg"] = {"args": {"--suffix-draft": "0"}}
    folder = task / name
    preview = make_run_config(c, tree, "cfg", ready, folder)
    if phase == "no-mtp" and any(flag_value(preview.get(key, []), "--mtp") is not None for key in ("args", "user_args")):
        raise RuntimeError("NO_MTP_REQUIRES_SEPARATE_FROZEN_INPUT_CONFIG")
    if c["port"] != 18089 or c["max_context"] != 131072 or c["min_available_mib"] < 4096 or c["gpu_temp_abort_c"] > 85:
        raise RuntimeError("LAB_GUARD_DRIFT")
    if preview["env"]["STRATA_DEQUANT_SIDE"] != "0" or preview["env"]["STRATA_ROUTE_PRIOR"] != "0":
        raise RuntimeError("APPROXIMATE_OR_DEQUANT_PATH_ENABLED")
    folder.mkdir(parents=True, exist_ok=False)
    dump(folder / "campaign.json", {"source": source, "phase": phase, "ready": ready,
         "original_cases": {case["name"]: case["actual_request_sha256"] for case, _ in cases},
         "policy": "exact original gold; synthetic prompt controls never replace original judgments",
         "old_P3_and_P6_immutable": True, "production_writes": False})
    protected = baseline.combo.protected_hashes(c)
    dump(folder / "production-before.json", {"service": baseline.combo.assert_service_inactive(), "file_sha256": protected})
    rows = []
    raw_rows = []
    try:
        with gpu_lock(c["gpu_lock_workspace"]), evidence_lifecycle(c, folder):
            verify_assets(c)
            dump(folder / "cooldown.json", baseline.combo.wait_cool(c))
            counter = StrataCounter(tree, c["gguf"], c["template"])
            stop_ids = rendering_audit(counter, cases, folder)
            with baseline.combo.combination_server(c, tree, "cfg", ready, folder) as server:
                log = (folder / "engine.log").read_text()
                slots = re.findall(r"expert cache (\d+) slots", log)
                if not slots:
                    raise RuntimeError("CACHE_CAPACITY_NOT_AUDITABLE")
                slots = int(slots[-1])
                if phase == "no-mtp":
                    previous = json.loads((task / "trace-v2/activation.json").read_text())
                    if slots != previous["slots"]:
                        raise RuntimeError("ACTUAL_CACHE_CAPACITY_DIFFERS_BETWEEN_ARMS")
                dump(folder / "activation.json", {"slots": slots, "cache_budget_argument": 6000, "engine_argv": server.engine_audit,
                                                   "env": preview["env"], "mtp": phase != "no-mtp"})
                with baseline.MemorySampler(folder, lambda: baseline.boundary.descendants(server)) as memory:
                    replay = baseline.Replay(c, server, counter, folder, memory)
                    rows = replay.rows
                    def request(name, body, case, kind):
                        server_log = folder / "server.log"
                        offset = server_log.stat().st_size
                        response, row = replay.request(name, body, case=case, frozen_hash=case["actual_request_sha256"] if kind == "original" else None)
                        with server_log.open("rb") as stream:
                            stream.seek(offset)
                            delta = stream.read().decode(errors="replace")
                        matches = re.findall(r"^\[strata\] raw ids: (\[.*\])$", delta, re.M)
                        if not matches:
                            raise RuntimeError("RAW_TOKEN_TRACE_MISSING")
                        ids = json.loads(matches[-1])
                        raw = counter.tokenizer.decode(ids)
                        record = {"name": name, "kind": kind, "raw_ids": ids, "raw_text": raw,
                                  "ends_in_eos": ids[-1] in stop_ids, "gold": case["expected"],
                                  "body_sha256": hash_obj(body), "score": row["score"],
                                  "raw_matches_visible_plus_eos": raw == response["text"] + counter.tokenizer.decode([ids[-1]])}
                        dump(folder / (name + ".raw-tokens.json"), record)
                        raw_rows.append(record)
                        if phase == "no-mtp" and row["metrics"].get("drafts_offered") != 0:
                            raise RuntimeError("NO_MTP_CONTROL_STILL_OFFERS_DRAFTS")
                        return response
                    first = indexed["69632-prime"]
                    variants = controls(first)
                    # First short request qualifies the exact real tokenizer count.
                    r = request("control-literal-copy", variants["literal-copy"], first, "control")
                    if r["usage"]["prompt_tokens"] != counter(variants["literal-copy"]):
                        raise RuntimeError("COUNTER_NOT_QUALIFIED")
                    if phase == "format-cold":
                        for target in baseline.restore.TARGETS:
                            case = indexed[f"{target}-prime"]
                            dump(folder / (str(target) + "-cooldown.json"), baseline.combo.wait_cool(c, loaded=True))
                            request(f"control-cold-explicit-{target}", controls(case)["long-explicit-format"], case, "control")
                            if replay.rows[-1]["metrics"]["reused_tokens"] > 128:
                                raise RuntimeError("COLD_FORMAT_CONTROL_REUSED_LEDGER")
                            request(f"original-warm-{target}-prime", case["body"], case, "original")
                    else:
                        for case, _ in cases:
                            if case["name"].endswith("prime"):
                                dump(folder / (case["name"] + "-cooldown.json"), baseline.combo.wait_cool(c, loaded=True))
                            request("original-" + case["name"], case["body"], case, "original")
                    if phase == "trace":
                        for name in ("short-same-question", "long-explicit-format", "long-thinking"):
                            dump(folder / (name + "-cooldown.json"), baseline.combo.wait_cool(c, loaded=True))
                            request("control-" + name, variants[name], first, "control")
                        second = indexed["102400-prime"]
                        dump(folder / "think100-cooldown.json", baseline.combo.wait_cool(c, loaded=True))
                        request("control-long-thinking-100k", controls(second)["long-thinking"], second, "control")
        if baseline.source_receipt(tree, prior) != source:
            raise RuntimeError("SOURCE_OR_BINARY_CHANGED")
    finally:
        dump(folder / "rows.json", rows)
        dump(folder / "raw-token-summary.json", raw_rows)
        dump(folder / "production-after.json", {"service": baseline.combo.assert_service_inactive(),
                                               "file_sha256": baseline.combo.assert_protected(c, protected),
                                               "gpu": gpu_inventory(c["gpu"])})
    summary = {"phase": phase, "requests": len(rows),
               "original_pass": [row["name"] for row in rows if row["name"].startswith("original-") and row["score"]["pass"]],
               "original_fail": [row["name"] for row in rows if row["name"].startswith("original-") and not row["score"]["pass"]],
               "controls": {row["name"]: row["score"] for row in rows if row["name"].startswith("control-")},
               "adoption_claim": False}
    dump(folder / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--phase", choices=["trace", "no-mtp", "format-cold"], required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    os.environ.update(STRATA_REPLY_REUSE="1", STRATA_PRESERVE_THINKING="0")
    print(json.dumps(run(load_config(args.config), args.config.resolve().parent,
                         args.prior.resolve(), args.old.resolve(), args.phase, args.name)), flush=True)
