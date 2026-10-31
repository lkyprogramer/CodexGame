"""Structural result schemas only; no collector, runner, or acceptance verdict.

Missing observations use null and missing_reasons[field]; they are never zeroed.
These schemas cannot establish timing, token accounting, or causal correctness.
"""


def _schema(required, properties):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object", "required": required + ["missing_reasons"],
        "properties": {**properties, "missing_reasons": {
            "type": "object", "additionalProperties": {"type": "string", "minLength": 1},
        }},
    }


_TEXT = {"type": ["string", "null"]}
_COUNT = {"type": ["integer", "null"], "minimum": 0}
_TIME = {"type": ["number", "null"], "minimum": 0}
_HASH = {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"}
_IDENTITY = {key: {"type": "string", "minLength": 1} for key in ("engine_id", "request_id")}
_EXPERTS = {"type": ["array", "null"], "items": {
    "type": "object", "required": ["expert_id", "format", "nt"],
    "properties": {"expert_id": _COUNT, "format": _TEXT, "nt": _COUNT},
}}

REQUESTS_SCHEMA = _schema(
    list(_IDENTITY) + [
        "campaign_id", "phase", "prime_or_append", "planned_order", "execution_status",
        "start_utc", "start_monotonic_ns", "end_monotonic_ns", "clock_domain",
        "request_body_sha256", "rendered_token_ids_sha256", "template_sha256",
        "tokenizer_sha256", "sampling_config_sha256", "seed", "prime_output_token_ids_sha256",
        "rendered_history_sha256", "stop_reason", "prompt_tokens", "read_tokens", "reused_tokens",
        "thinking_tokens", "content_tokens", "completion_tokens", "sse_chunks", "ttft_ms",
        "decode_ms", "wall_ms", "valid", "failure_kind", "request_recipe_sha256", "trajectory_identity",
    ],
    {
        **_IDENTITY, "campaign_id": {"type": "string", "minLength": 1}, "phase": _TEXT,
        "prime_or_append": {"enum": ["prime", "append_1", "append_2"]},
        "planned_order": {"type": "integer", "minimum": 0, "maximum": 2},
        "execution_status": {"enum": ["NOT_RUN", "RUNNING", "COMPLETED", "FAILED", "INSUFFICIENT"]},
        **{key: _HASH for key in (
            "request_body_sha256", "rendered_token_ids_sha256", "template_sha256",
            "tokenizer_sha256", "sampling_config_sha256", "prime_output_token_ids_sha256",
            "rendered_history_sha256", "request_recipe_sha256",
        )},
        **{key: _COUNT for key in (
            "start_monotonic_ns", "end_monotonic_ns", "prompt_tokens", "read_tokens", "reused_tokens",
            "thinking_tokens", "content_tokens", "completion_tokens", "sse_chunks",
        )},
        "seed": {"type": ["integer", "null"]},
        **{key: _TIME for key in ("ttft_ms", "decode_ms", "wall_ms")},
        **{key: _TEXT for key in ("start_utc", "clock_domain", "stop_reason", "failure_kind", "trajectory_identity")},
        "valid": {"type": ["boolean", "null"]},
    },
)

WINDOWS_SCHEMA = _schema(
    list(_IDENTITY) + ["window_id", "start", "end", "unit", "clock_domain", "source_event_ids",
                       "coverage", "context_tokens", "window_kind", "draft_tokens", "accepted_tokens",
                       "committed_tokens", "cpu_experts", "gpu_experts", "dispatch", "resident_mask",
                       "kernel_shape", "stream_id", "graph_id", "event_ids"],
    {
        **_IDENTITY, "window_id": {"type": "string", "minLength": 1},
        **{key: _TIME for key in ("start", "end")},
        **{key: _TEXT for key in ("unit", "clock_domain", "coverage", "stream_id", "graph_id")},
        **{key: _COUNT for key in ("context_tokens", "draft_tokens", "accepted_tokens", "committed_tokens")},
        "window_kind": {"enum": ["normal", "continuation", None]},
        **{key: {"type": ["array", "null"], "items": {"type": "string"}} for key in ("source_event_ids", "event_ids")},
        **{key: _EXPERTS for key in ("cpu_experts", "gpu_experts")},
        **{key: {"type": ["array", "null"]} for key in ("resident_mask", "kernel_shape")},
        "dispatch": {"type": ["object", "null"]},
    },
)

DEPENDENCIES_SCHEMA = _schema(
    ["campaign_id", "clock_domain", "nodes", "edges", "unknown_dependencies"],
    {
        "campaign_id": {"type": "string", "minLength": 1}, "clock_domain": _TEXT,
        "nodes": {"type": "array", "items": {
            "type": "object", "required": ["engine_id", "request_id", "window_id", "node_id"],
            "properties": {**_IDENTITY, "window_id": {"type": "string"}, "node_id": {"type": "string"}},
        }},
        "edges": {"type": "array", "items": {
            "type": "object", "required": ["from", "to", "reason", "evidence_ref", "verified"],
            "properties": {"from": {"type": "string"}, "to": {"type": "string"},
                           "reason": _TEXT, "evidence_ref": _TEXT,
                           "verified": {"enum": [True, False, "UNKNOWN"]}},
        }},
        "unknown_dependencies": {"type": "array", "items": {"type": "string"}},
    },
)
