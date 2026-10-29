"""Audit frozen inputs and compare full logits without changing original scores."""
from __future__ import annotations

import argparse
from array import array
import hashlib
import heapq
import json
import math
from pathlib import Path
import re
import struct
import sys

WIDTH = 248320
EOS = 248046
DASH = 12


def ids_bytes(ids):
    return struct.pack("<" + "i" * len(ids), *ids)


def fnv_ids(ids):
    value = 1469598103934665603
    for byte in ids_bytes(ids):
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return f"{value:016x}"


def verify_ids(record):
    data = Path(record["path"]).read_bytes()
    ids = [int(x) for x in data.decode().replace(",", " ").split()]
    actual = {"count": len(ids), "fnv64": fnv_ids(ids),
              "file_sha256": hashlib.sha256(data).hexdigest(),
              "int32_sha256": hashlib.sha256(ids_bytes(ids)).hexdigest()}
    if any(actual[key] != record[key] for key in actual):
        raise ValueError("FROZEN_ID_MISMATCH: " + str(record["path"]))
    return ids


def load_rows(path, rows, width=WIDTH):
    data = Path(path).read_bytes()
    if len(data) != rows * width * 4:
        raise ValueError("LOGITS_SHAPE_MISMATCH: " + str(path))
    values = array("f")
    values.frombytes(data)
    if sys.byteorder != "little":
        values.byteswap()
    if any(not math.isfinite(x) for x in values):
        raise ValueError("NONFINITE_LOGITS: " + str(path))
    return [values[i * width:(i + 1) * width] for i in range(rows)]


def row_summary(row, tracked, top_n=20):
    top = heapq.nlargest(min(top_n, len(row)), range(len(row)), key=lambda i: (row[i], -i))
    maximum = row[top[0]]
    log_z_shifted = math.log(math.fsum(math.exp(x - maximum) for x in row))

    def item(token):
        return {"id": token, "logit": row[token],
                "rank": 1 + sum(x > row[token] for x in row),
                "probability": math.exp(row[token] - maximum - log_z_shifted)}

    return {"top1": top[0], "top1_margin": maximum - row[top[1]] if len(top) > 1 else None,
            "top": [item(i) for i in top], "tracked": {str(i): item(i) for i in sorted(set(tracked))}}


def row_metrics(reference, native):
    if len(reference) != len(native) or not reference:
        raise ValueError("ROW_WIDTH_MISMATCH")
    differences = [b - a for a, b in zip(reference, native)]
    offset = math.fsum(differences) / len(differences)
    rmax, nmax = max(reference), max(native)
    rz = math.log(math.fsum(math.exp(x - rmax) for x in reference))
    nz = math.log(math.fsum(math.exp(x - nmax) for x in native))
    kl = math.fsum(math.exp(a - rmax - rz) * ((a - rmax - rz) - (b - nmax - nz))
                   for a, b in zip(reference, native))
    return {"native_minus_reference_mean": offset,
            "max_absolute_difference": max(map(abs, differences)),
            "centered_rmse": math.sqrt(math.fsum((x - offset) ** 2 for x in differences) / len(differences)),
            "kl_reference_to_native": kl}


def validate_native(records, case, tokens, prefix, rows, final_anchor=EOS):
    selected = [x for x in records if x["case"] == case]
    if len(selected) != len(rows):
        raise ValueError("NATIVE_REQUEST_COUNT_MISMATCH")
    for step, (record, row) in enumerate(zip(selected, rows)):
        current = tokens + prefix[:step]
        if (record["step"] != step or record["input_count"] != len(current)
                or record["input_fnv"] != fnv_ids(current)):
            raise ValueError("NATIVE_INPUT_ID_MISMATCH")
        if record["emitted"] != max(range(len(row)), key=row.__getitem__):
            raise ValueError("NATIVE_EMITTED_ARGMAX_MISMATCH")
        if record["emitted"] != (prefix[step] if step < len(prefix) else final_anchor):
            raise ValueError("NATIVE_ORIGINAL_ANCHOR_MISMATCH")


def analyze(task, reference, native, names):
    cases = json.loads((task / "inputs.json").read_text())
    selected = [x for x in cases if x["name"] in names]
    if {x["name"] for x in selected} != set(names):
        raise ValueError("UNKNOWN_CASE")
    records = json.loads((native / "requests.json").read_text())
    stdout = (reference / "stdout.log").read_text()
    result = {"original_six_status": "FAIL_UNCHANGED", "scoring_changed": False,
              "comparison": "same source GGUF and exact input IDs; reference F16 KV versus native int8 KV",
              "conditioning": "step s uses original prompt plus s observed Strata digits, regardless of reference argmax",
              "cases": []}
    for case in selected:
        name = case["name"]
        tokens, prefix = verify_ids(case["tokens"]), verify_ids(case["prefix"])
        count = len(prefix) + 1
        expected = (f"CASE {name} input={len(tokens)} prefix={len(prefix)} "
                    f"input_fnv={case['tokens']['fnv64']} prefix_fnv={case['prefix']['fnv64']} ")
        if expected not in stdout or f"COMPLETE {name} rows={count}\n" not in stdout:
            raise ValueError("REFERENCE_INPUT_OR_COMPLETION_MISMATCH")
        rr, nr = load_rows(reference / (name + ".f32"), count), load_rows(native / (name + ".f32"), count)
        final_anchor = DASH if case["original_status"] == "CONTROL" else EOS
        validate_native(records, name, tokens, prefix, nr, final_anchor)
        steps = []
        for step, (r, n) in enumerate(zip(rr, nr)):
            observed = prefix[step] if step < len(prefix) else final_anchor
            # After an incorrect forced digit, this is only the gold's positional ID,
            # not the next token on a gold-conditioned trajectory.
            gold_position = case["gold_digit_ids"][step] if step < len(prefix) else DASH
            tracked = [observed, gold_position, DASH, 248044, EOS]
            rs, ns = row_summary(r, tracked), row_summary(n, tracked)
            printed = re.search(rf"^ROW {re.escape(name)} {step} top=(\d+) value=(\S+) forced_next=(-?\d+)$", stdout, re.M)
            if (not printed or int(printed[1]) != rs["top1"]
                    or not math.isclose(float(printed[2]), r[rs["top1"]], abs_tol=1e-6, rel_tol=1e-8)
                    or int(printed[3]) != (prefix[step] if step < len(prefix) else -1)):
                raise ValueError("REFERENCE_PRINTED_ROW_MISMATCH")
            steps.append({"step": step, "forced_digit_ids_before_row": prefix[:step],
                          "observed_next_id": observed, "gold_positional_id": gold_position,
                          "reference": rs, "native": ns,
                          "top1_equal": rs["top1"] == ns["top1"],
                          "reference_observed_minus_gold_position": r[observed] - r[gold_position],
                          "native_observed_minus_gold_position": n[observed] - n[gold_position],
                          "reference_eos_minus_dash": r[EOS] - r[DASH],
                          "native_eos_minus_dash": n[EOS] - n[DASH],
                          "metrics": row_metrics(r, n)})
        reference_matches = all(x["reference"]["top1"] == x["observed_next_id"] for x in steps)
        result["cases"].append({"name": name, "input_count": len(tokens), "input_identity_verified": True,
                                "native_emitted_argmax_and_original_anchor_verified": True,
                                "reference_printed_rows_verified": True,
                                "observed_prefix": case["observed_prefix"], "gold": case["gold"],
                                "same_top1_rows": sum(x["top1_equal"] for x in steps),
                                "reference_greedy_matches_entire_observed_path": reference_matches,
                                "steps": steps})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--case", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; preserve prior evidence")
    result = analyze(args.task, args.reference, args.native, args.case)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"cases": [{k: v for k, v in c.items() if k != "steps"} for c in result["cases"]]}))
