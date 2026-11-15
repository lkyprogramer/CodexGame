"""Small pure-data teaching guard; NOT the planned real TSV/meta validator.

No subprocess, network, model, CUDA, timing, statistical scorer or adoption logic.
The result can only qualify this deliberately reduced synthetic input contract.
"""
import math


def _finite_score(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False  # Not representable in this illustrative IEEE score domain.


def guard_fixed_text_fixture(data):
    reasons = set()

    def finish():
        return {
            "status": "INPUT_INVALID_FIXTURE_ONLY" if reasons else "INPUT_ADMISSIBLE_FIXTURE_ONLY",
            "reasons": sorted(reasons), "engine_starts": 0,
            "limitations": ["Synthetic reduced JSON only; no TSV/meta parser.",
                            "Identity strings and completeness flags are NOT authenticated.",
                            "No logits, state, model, timing or task-quality validation."],
        }

    if not isinstance(data, dict):
        reasons.add("MALFORMED_FIXTURE")
        return finish()
    if data.get("provenance") != "SYNTHETIC":
        reasons.add("NOT_A_SYNTHETIC_FIXTURE")
    expected = data.get("expected")
    arms = data.get("arms")
    if not isinstance(expected, dict) or not isinstance(arms, list):
        reasons.add("MALFORMED_FIXTURE")
        return finish()
    if expected.get("contract") != "fixed-text-decode/v1":
        reasons.add("UNSUPPORTED_TEXT_CONTRACT")
    items = expected.get("requests")
    scorers = expected.get("scorer_by_role")
    if not isinstance(scorers, dict) or any(not isinstance(scorers.get(k), str) or not scorers[k]
                                           for k in ("stock", "candidate")):
        reasons.add("INVALID_EXPECTED_SET")
        return finish()
    if not isinstance(expected.get("set_digest"), str) or not expected["set_digest"]:
        reasons.add("INVALID_EXPECTED_SET")
        return finish()
    vocab = expected.get("vocabulary_size")
    tol = expected.get("score_format_tolerance")
    if type(vocab) is not int or vocab < 2 or type(tol) not in (int, float) or tol != 1e-9:
        reasons.add("INVALID_EXPECTED_SET")
        return finish()
    if not isinstance(items, list) or not items:
        reasons.add("INVALID_EXPECTED_SET")
        return finish()
    mapping = {}
    for it in items:
        if not isinstance(it, dict) or not isinstance(it.get("id"), str) or not it["id"]:
            reasons.add("INVALID_EXPECTED_SET")
            return finish()
        if it["id"] in mapping:
            reasons.add("INVALID_EXPECTED_SET")
            return finish()
        p, cont = it.get("prompt_length"), it.get("continuation")
        if type(p) is not int or p < 1 or not isinstance(cont, list) or not cont or any(
                type(t) is not int or not 0 <= t < vocab for t in cont):
            reasons.add("INVALID_EXPECTED_SET")
            return finish()
        mapping[it["id"]] = it
    if any(not isinstance(a, dict) for a in arms):
        reasons.add("MALFORMED_FIXTURE")
        return finish()
    roles = [a.get("role") for a in arms]
    if any(not isinstance(r, str) for r in roles):
        reasons.add("INVALID_ARM_ROLES")
        return finish()
    if roles.count("stock") < 2:
        reasons.add("INSUFFICIENT_STOCK_ARMS")
    if roles.count("candidate") != 1 or any(r not in ("stock", "candidate") for r in roles):
        reasons.add("INVALID_ARM_ROLES")
    run_ids = [a.get("run_id") for a in arms]
    if any(not isinstance(r, str) or not r for r in run_ids):
        reasons.add("INVALID_RUN_ID")
    elif len(set(run_ids)) != len(run_ids):
        reasons.add("DUPLICATE_RUN_ID")
    for arm in arms:
        if arm.get("set_digest") != expected["set_digest"]:
            reasons.add("SET_DIGEST_MISMATCH")
        if arm.get("scorer_digest") != scorers.get(arm.get("role")):
            reasons.add("SCORER_IDENTITY_MISMATCH")
        if arm.get("path") != "decode":
            reasons.add("WRONG_SCORER_PATH")
        if arm.get("complete") is not True:
            reasons.add("INCOMPLETE_COLLECTOR")
        requests = arm.get("requests")
        if not isinstance(requests, list) or any(not isinstance(r, dict) for r in requests):
            reasons.add("MALFORMED_FIXTURE")
            continue
        ids = [r.get("id") for r in requests]
        if any(not isinstance(i, str) for i in ids):
            reasons.add("INPUT_SET_MISMATCH")
            continue
        if len(set(ids)) != len(ids):
            reasons.add("DUPLICATE_REQUEST_ID")
        if set(ids) != set(mapping):
            reasons.add("INPUT_SET_MISMATCH")
        for request in requests:
            if request["id"] not in mapping:
                continue
            exp = mapping[request["id"]]
            p, cont = exp["prompt_length"], exp["continuation"]
            wanted = dict(zip(range(p - 1, p + len(cont) - 1), cont))
            if "emitted" not in request:
                reasons.add("FORCED_OUTPUT_UNPROVEN")
            elif not isinstance(request["emitted"], list) or any(type(t) is not int or not 0 <= t < vocab
                                                                for t in request["emitted"]):
                reasons.add("INVALID_EMITTED_TOKENS")
            elif request["emitted"] != cont:
                reasons.add("FORCED_OUTPUT_MISMATCH")
            rows = request.get("rows")
            if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
                reasons.add("INVALID_ROW")
                continue
            seen = []
            for row in rows:
                pos, target = row.get("pos"), row.get("target")
                if type(pos) is not int or type(target) is not int or not 0 <= target < vocab:
                    reasons.add("INVALID_ROW")
                    continue
                seen.append(pos)
                if pos in wanted and target != wanted[pos]:
                    reasons.add("TARGET_MISMATCH")
                values = [row.get(k) for k in ("logp", "argmax_logp", "top2_logp", "top2_margin")]
                if any(not _finite_score(v) for v in values):
                    reasons.add("NONFINITE_SCORE")
                    continue
                lp, am_lp, top2_lp, margin = values
                am, second = row.get("argmax"), row.get("top2_id")
                if any(type(i) is not int or not 0 <= i < vocab for i in (am, second)):
                    reasons.add("INVALID_ROW")
                    continue
                if any(v > tol for v in (lp, am_lp, top2_lp)) or margin < -tol:
                    reasons.add("INVALID_SCORE_DOMAIN")
                if am_lp + tol < max(lp, top2_lp) or (target not in (am, second) and lp > top2_lp + tol):
                    reasons.add("SCORE_ORDER_MISMATCH")
                if am == second:
                    reasons.add("TOP2_ID_DUPLICATE")
                if (target == am and abs(lp - am_lp) > tol) or (target == second and abs(lp - top2_lp) > tol):
                    reasons.add("INCONSISTENT_TOKEN_LOGP")
                if abs(margin - (am_lp - top2_lp)) > tol:
                    reasons.add("MARGIN_MISMATCH")
            if len(seen) != len(set(seen)):
                reasons.add("DUPLICATE_POSITION")
            if set(seen) != set(wanted) or len(rows) != len(wanted):
                reasons.add("POSITION_COVERAGE_MISMATCH")
            elif seen != sorted(wanted):
                reasons.add("POSITION_ORDER_MISMATCH")
    return finish()
