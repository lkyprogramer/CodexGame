"""Offline P00 plan checks. No process launch, tokenization, or live attestation."""

import re


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COLLECTION = "existing_low_overhead_logs_single_arm"
_SEQUENCE = ["prime", "append_1", "append_2"]
_STOPS = {
    "85C_gpu", "MemAvailable_below_4096MiB", "unexpected_gpu_owner",
    "identity_mismatch", "engine_failure", "request_budget_or_deadline",
}
RUNTIME_CHECKS = [
    "Reattest authorization, GPU handoff/serial lease, PID identity and actual env before start.",
    "Render full body with frozen template/tokenizer before each send; save body/token hashes.",
    "Require actual rendered input + 2048 + 4096 <= 131072 before each send.",
    "Append own unmodified generated thinking/content history under reply reuse=1/PT0.",
    "Observe actual read_tokens including PT0 content reread; no new-read target/range gate.",
    "Verify frozen Pi followup user-message hash/source without padding or rewriting.",
    "Send only when remaining wall budget covers request deadline plus cleanup reserve.",
    "Preserve short output/failure/NOT_RUN originals; stop INSUFFICIENT without replacement.",
    "Collect actual prompt/read/reused/completion tokens and full history/trajectory identity.",
    "Keep P05 BLOCKED_EVIDENCE and all six historical quality FAIL unchanged.",
]


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, low, high, field):
    _require(type(value) is int and low <= value <= high, f"{field}: integer in [{low}, {high}] required")


def _hash(value, field):
    _require(isinstance(value, str) and _SHA256.fullmatch(value), f"{field}: SHA256 required")


def validate_warm_plan(plan, policy) -> dict:
    """Return preparation readiness or raise ValueError on an invalid frozen plan.

    Reference receipts are supplied by the caller; this function does not read files
    or prove that a reference grants permission. Runtime checks remain mandatory.
    Append recipes can be frozen before the engine generates its real history.
    """
    _require(isinstance(plan, dict) and isinstance(policy, dict), "plan/policy must be objects")
    limits = policy.get("limits", {})
    # A caller cannot relax the diagnostic contract by changing its policy copy.
    fixed = {
        "context_ceiling_tokens": 131072, "context_safety_tokens": 4096,
        "max_initial_diagnostic_engine_starts": 1,
        "max_initial_diagnostic_work_requests": 3,
        "max_initial_diagnostic_wall_seconds": 3600,
        "diagnostic_cleanup_reserve_seconds": 120,
        "diagnostic_request_deadline_seconds": 600, "diagnostic_output_tokens": 2048,
    }
    for key, value in fixed.items():
        _require(type(limits.get(key)) is int and limits[key] == value, f"policy.{key}: frozen limit mismatch")
    diagnostic = policy.get("diagnostic", {})
    _require(diagnostic.get("append_new_read_policy") == "observe_actual_pi_followup", "policy: actual Pi followup observation required")
    _require("append_new_read_target_tokens" in diagnostic and diagnostic["append_new_read_target_tokens"] is None, "policy: new-read target forbidden")
    _require(plan.get("schema_version") == 1, "schema_version must be 1")
    _require(plan.get("template_only") is False, "unbound template is not executable preparation")
    for field in ("campaign_id", "frozen_at_utc"):
        _require(isinstance(plan.get(field), str) and bool(plan[field].strip()), f"{field} required")
    receipts = plan.get("reference_evidence", {})
    _require(isinstance(receipts, dict), "reference_evidence must be an object")
    planning_only = plan.get("planning_only", False)
    _require(type(planning_only) is bool, "planning_only must be boolean")
    fields = ["execution_instruction_reference", "baseline_identity_path"]
    if planning_only:
        _require(plan.get("gpu_handoff_reference") is None, "planning_only must not claim GPU handoff")
    else:
        fields.append("gpu_handoff_reference")
    for field in fields:
        ref = plan.get(field)
        _require(isinstance(ref, str) and bool(ref.strip()), f"{field} required")
        receipt = receipts.get(ref)
        _require(isinstance(receipt, dict) and receipt.get("status") == "AVAILABLE", f"{field}: unavailable reference")
        _hash(receipt.get("sha256"), field)
        if field == "execution_instruction_reference":
            expected_scope = "p00_readonly_cpu" if planning_only else "p01_diagnostic"
            _require(receipt.get("scope") == expected_scope, "execution instruction scope mismatch")
    _integer(plan.get("max_engine_starts"), 1, 1, "max_engine_starts")
    _integer(plan.get("max_work_requests"), 3, 3, "max_work_requests")
    _integer(plan.get("wall_budget_seconds"), 1, 3600, "wall_budget_seconds")
    _integer(plan.get("cleanup_reserve_seconds"), 120, 3600, "cleanup_reserve_seconds")
    for field, expected in {
        "context_total_ceiling": 131072, "context_safety_tokens": 4096,
        "target_output_tokens_per_request": 2048, "max_output_tokens_per_request": 2048,
        "short_output_status": "INSUFFICIENT", "collection": _COLLECTION,
    }.items():
        _require(plan.get(field) == expected and not isinstance(plan.get(field), bool), f"{field}: frozen contract mismatch")
    _integer(plan.get("request_deadline_seconds"), 1, 600, "request_deadline_seconds")
    for field in ("retry_or_replace_failed_sample", "deployment_approved", "allow_extra_control_or_profiler"):
        _require(plan.get(field) is False, f"{field} must be false")
    stops = plan.get("hard_stop")
    _require(isinstance(stops, list) and all(isinstance(stop, str) for stop in stops), "hard_stop must contain strings")
    _require(_STOPS <= set(stops), "hard stops missing")
    forbidden = set(policy.get("forbidden_env", [])) | {
        "STRATA_STAGE_PIN", "STRATA_ROUTE_RESIDENT", "STRATA_VERIFY_PROFILE",
    }
    matrix = plan.get("matrix")
    _require(isinstance(matrix, list) and len(matrix) == 1, "exactly one engine/arm required")
    engine = matrix[0]
    _require(isinstance(engine, dict), "engine must be an object")
    _require(isinstance(engine.get("engine_label"), str) and engine["engine_label"].strip(), "known engine_label required")
    _require(engine.get("collection") == _COLLECTION, "extra control/profiler collection forbidden")
    _require(engine.get("append_new_read_includes_pt0_history_reread") is True, "actual new read must include PT0 reread")
    _require(type(engine.get("sampling_seed")) is int, "sampling_seed required")
    _require(isinstance(engine.get("template_tokenizer_identity"), dict), "template_tokenizer_identity required")
    for key in ("template_sha256", "tokenizer_sha256"):
        _hash(engine["template_tokenizer_identity"].get(key), key)
    for owner in (plan, engine):
        env = owner.get("env", {})
        _require(isinstance(env, dict), "env must be an object")
        _require(not forbidden.intersection(env), "forbidden env key present (even value 0)")
        for key in ("profiler", "profiles", "extra_arms", "control_arms"):
            _require(owner.get(key) in (None, False, [], {}), f"{key}: additional arms/profiling forbidden")
    requests = engine.get("requests")
    _require(isinstance(requests, list) and len(requests) == 3, "prime and two appends required")
    deadlines = []
    bounds = []
    for index, request in enumerate(requests):
        _require(isinstance(request, dict), "request must be an object")
        label = _SEQUENCE[index]
        request_env = request.get("env", {})
        _require(isinstance(request_env, dict) and not forbidden.intersection(request_env), "forbidden request env")
        for key in ("profiler", "profiles", "extra_arms", "control_arms"):
            _require(request.get(key) in (None, False, [], {}), f"{label}.{key}: forbidden")
        _require(request.get("request_label") == label, "unknown/duplicate request or order")
        _require(request.get("engine_label", engine["engine_label"]) == engine["engine_label"], "unknown request engine")
        _integer(request.get("target_output_tokens"), 2048, 2048, label + ".target_output_tokens")
        _integer(request.get("max_output_tokens"), 2048, 2048, label + ".max_output_tokens")
        _integer(request.get("request_deadline_seconds"), 1, plan["request_deadline_seconds"], label + ".deadline")
        deadlines.append(request["request_deadline_seconds"])
        _integer(request.get("prompt_tokens_upper_bound"), 1, 131072 - 2048 - 4096, label + ".prompt_tokens_upper_bound")
        bounds.append(request["prompt_tokens_upper_bound"])
        _hash(request.get("body_or_recipe_sha256"), label + ".body_or_recipe_sha256")
        _require(request.get("actual_history_hash_policy") == "own_generated_history_no_rewrite", "history rewrite forbidden")
        _require(request.get("history_status") == "RUNTIME_PENDING", "unexecuted history must remain RUNTIME_PENDING")
        for field in ("actual_read_tokens", "actual_reused_tokens", "actual_completion_tokens", "rendered_history_sha256", "prime_output_token_ids_sha256"):
            _require(request.get(field) is None, f"{label}.{field}: cannot prefill runtime observations")
        if index == 0:
            _integer(request.get("context_target_tokens"), 102400, 102400, "prime.context_target_tokens")
            _require(bounds[-1] >= 102400, "prime budget below 100K target")
            prompt = request.get("actual_prompt_tokens")
            token_hash = request.get("rendered_token_ids_sha256")
            _require((prompt is None) == (token_hash is None), "prime rendered count/hash must be paired")
            if prompt is not None:
                _integer(prompt, 1, bounds[-1], "prime.actual_prompt_tokens")
                _hash(token_hash, "prime.rendered_token_ids_sha256")
        else:
            _require(request.get("actual_prompt_tokens") is None and request.get("rendered_token_ids_sha256") is None, "append render depends on real generated history")
            _require(request.get("new_read_policy") == "observe_actual_pi_followup", "observe real Pi followup without a new-read gate")
            for field in ("new_read_target_tokens", "new_read_allowed_range_tokens"):
                _require(field in request and request[field] is None, "new-read target/range forbidden")
            _require(request.get("new_read_range_rationale") is None, "obsolete read-range rationale forbidden")
            _require(isinstance(request.get("new_read_rationale"), str) and request["new_read_rationale"].strip(), "explain actual PT0 new-read observation")
            _hash(request.get("append_user_message_sha256"), label + ".append_user_message_sha256")
            source = request.get("append_user_message_source_reference")
            _require(isinstance(source, str) and source.strip(), "frozen Pi user-message source required")
            _require(request.get("append_padding_allowed") is False, "padding real followup forbidden")
            _integer(request.get("append_user_tokens_upper_bound"), 1, 124928, label + ".append_user_tokens_upper_bound")
            _require(bounds[-1] >= bounds[-2] + 2048 + request["append_user_tokens_upper_bound"] + 64, "append bound must cover real history output, user tokens and 64-token template/BPE margin")
    _require(sum(deadlines) + plan["cleanup_reserve_seconds"] <= plan["wall_budget_seconds"], "deadlines and cleanup exceed wall budget")
    return {
        "status": "PLAN_VALID_PENDING_GPU_HANDOFF" if planning_only else "READY_FOR_P01_PREPARATION",
        "validation_scope": "OFFLINE_PLAN_ONLY",
        "execution_result": "NOT_RUN", "live_ready": False,
        "authorization_verified": False, "tokenizer_verified": False,
        "runtime_checks": list(RUNTIME_CHECKS), "p05_status": "BLOCKED_EVIDENCE",
        "historical_quality_failures": {"count": 6, "status": "UNRESOLVED"},
    }
