#!/usr/bin/env python3
"""Reproduce three upstream input-boundary examples without importing Engine.

Only the three pure statistical function ASTs from one exact audited source hash
are compiled. No upstream imports, main(), Engine, gen or score are executed.
This is not a security sandbox and is not a general source execution tool.
"""
import argparse
import ast
import hashlib
import json
import math
import pathlib
import random
import sys

AUDITED_SHA256 = "ee7755e2d9610fad40648889d2ffe62e5014d0167b5e8decd18aa5fad1104f63"
FUNCTIONS = {"ceil8", "binom_tail_ge", "check"}


def load_audited_check(path):
    path = pathlib.Path(path)
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("SOURCE_MISSING_OR_TOO_LARGE")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != AUDITED_SHA256:
        raise ValueError("SOURCE_HASH_MISMATCH: refuses all other source versions")
    parsed = ast.parse(raw.decode("utf-8"), filename=str(path))
    nodes = [n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name in FUNCTIONS]
    if len(nodes) != 3 or {n.name for n in nodes} != FUNCTIONS:
        raise ValueError("AUDITED_FUNCTION_SET_MISMATCH")
    namespace = {"math": math, "random": random}
    module = ast.Module(body=nodes, type_ignores=[])
    exec(compile(module, "<audited-pure-force-check-functions>", "exec"), namespace)
    return namespace["check"]


def probe(check):
    def arm(count=8):
        return {"r1": [(False, 0.0, 0.2)] * count,
                "r2": [(False, 0.0, 0.2)] * count}

    cases = [
        ("missing_request", [arm(), arm()], {"r1": arm()["r1"]},
         {"requests": 1, "tokens_cand": 8, "tokens_stock_arms": [8, 8]}),
        ("short_coverage", [arm(), arm()], arm(2),
         {"requests": 2, "tokens_cand": 4, "tokens_stock_arms": [16, 16]}),
        ("one_stock_arm", [arm()], arm(),
         {"requests": 2, "tokens_cand": 16, "tokens_stock_arms": [16]}),
    ]
    results = []
    for name, stock, candidate, expected in cases:
        result = check(stock, candidate, seed=1, boots=100)
        observed = {k: result[k] for k in ("verdict", "requests", "tokens_cand", "tokens_stock_arms")}
        reproduced = result["verdict"] == "PASS" and all(result[k] == v for k, v in expected.items())
        results.append({"case": name, "observed": observed, "boundary_reproduced": reproduced})
    return {"source_sha256": AUDITED_SHA256, "provenance": "SYNTHETIC",
            "method": "Exact-source pure-function AST extraction; no module import or engine code.",
            "engine_starts": 0, "generation_requests": 0, "gpu_runs": 0,
            "bootstrap_draws_for_toy_example": 100,
            "cases": results, "all_boundaries_reproduced": all(r["boundary_reproduced"] for r in results),
            "limitations": "Shows input precondition gaps only; not real-model correctness or performance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = probe(load_audited_check(args.source))
    except (OSError, ValueError, SyntaxError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["all_boundaries_reproduced"] else 1


if __name__ == "__main__":
    sys.exit(main())
