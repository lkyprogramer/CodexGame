"""Retry only F06 cancellation with a deliberately prolonged fault request.

All successful operational checks and the original inconclusive cancellation
remain immutable. min_tokens/ignore_eos below are fault injection, never OCR
quality or performance settings. Execute against the same isolated idle service.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from ocrbench.client import VLLMClient, atomic_json
from probe_runtime import Metrics, _shared_payload, cancellation_probe


PROTOCOL_SOURCES = [
    {
        "runtime": "ovis_vllm_0.22.1",
        "commit": "0decac0d96c42b49572498019f0a0e3600f50398",
        "url": "https://github.com/vllm-project/vllm/blob/0decac0d96c42b49572498019f0a0e3600f50398/vllm/entrypoints/openai/chat_completion/protocol.py",
        "request_fields": {"ignore_eos": "bool = False", "min_tokens": "int = 0"},
        "both_fields_forwarded_to_sampling_params": True,
    },
    {
        "runtime": "minicpm_pinned_vllm",
        "commit": "18343393b4da41a7e8027efbc4c7e77c28301bf0",
        "url": "https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/vllm/entrypoints/openai/chat_completion/protocol.py",
        "request_fields": {"ignore_eos": "bool = False", "min_tokens": "int = 0"},
        "both_fields_forwarded_to_sampling_params": True,
    },
]


def prepare_prior(prior_path: Path, image_override: Path | None = None) -> tuple[dict, dict, dict]:
    """Verify and reconstruct the exact earlier image request without inference."""
    prior_bytes = prior_path.read_bytes()
    prior = json.loads(prior_bytes)
    if prior.get("kind") != "OPERATIONAL_PROBE_NOT_QUALITY_BENCHMARK" or prior.get("context_expected") != 16384:
        raise ValueError("Prior is not the expected 16K operational probe")
    checks = prior["checks"]
    reused_checks = ["model_listing", "image_tokenize_completion_usage", "forced_length", "unknown_model", "context_overflow"]
    if any(checks.get(name, {}).get("status") != "PASS" for name in reused_checks):
        raise ValueError("The five prior operational checks must already be PASS")
    old_cancel = checks.get("disconnect_abort_and_drain", {})
    if old_cancel.get("status") == "PASS":
        raise ValueError("Prior cancellation already passed; do not repeat a completed gate")
    normal = checks["image_tokenize_completion_usage"]
    input_tokens = normal.get("input_tokens")
    if type(input_tokens) is not int or input_tokens <= 0 or normal.get("usage", {}).get("prompt_tokens") != input_tokens:
        raise ValueError("Prior actual input count and completion usage are not verified")
    budget = min(8192, 16384 - input_tokens - 512)
    if budget <= 0:
        raise ValueError("Prior input leaves no safe output budget")
    prior_request_path = prior_path.parent / "normal" / "01-tokenize.request.json"
    prior_request_bytes = prior_request_path.read_bytes()
    shared = json.loads(prior_request_bytes)
    if shared.get("model") != prior["model"]:
        raise ValueError("Prior request model differs from the probe model")
    content = shared["messages"][0]["content"]
    if len(shared["messages"]) != 1 or len(content) != 2 or content[0].get("type") != "image_url" or content[1].get("type") != "text":
        raise ValueError("Prior request is not one image plus the original task prompt")
    prompt = content[1]["text"]
    if hashlib.sha256(prompt.encode()).hexdigest() != prior["prompt"]["sha256"]:
        raise ValueError("Prior prompt hash mismatch")
    image = image_override or Path(prior["input"]["path"])
    if hashlib.sha256(image.read_bytes()).hexdigest() != prior["input"]["sha256"]:
        raise ValueError("Prior image hash mismatch")
    if _shared_payload(image, prompt, prior["model"]) != shared:
        raise ValueError("Prior saved image/prompt/tokenize payload does not match verified inputs")
    neutral = prior["neutral_sampling"]
    expected_neutral = {"temperature": 0.0, "top_p": 1.0, "top_k": -1,
                        "repetition_penalty": 1.0, "seed": 20261028,
                        "chat_template_kwargs": {"enable_thinking": False}}
    if neutral != expected_neutral:
        raise ValueError("Prior neutral sampling is not the frozen C0 sampling")
    payload = dict(shared, **neutral, max_tokens=budget, min_tokens=budget, ignore_eos=True, stream=False)
    provenance = {
        "prior_result": str(prior_path.resolve()),
        "prior_result_sha256": hashlib.sha256(prior_bytes).hexdigest(),
        "prior_request": str(prior_request_path.resolve()),
        "prior_request_sha256": hashlib.sha256(prior_request_bytes).hexdigest(),
        "prior_model": prior["model"], "prior_base_url": prior["base_url"],
        "input": dict(prior["input"], verified_current_path=str(image.resolve())),
        "prompt": prior["prompt"], "actual_input_tokens_reused": input_tokens,
        "output_budget": budget, "budget_formula": "min(8192,16384-actual_input_tokens-512)",
        "successful_prior_checks_reused_without_rerun": reused_checks,
        "original_cancel_status": old_cancel.get("status"),
        "original_cancel_reason": old_cancel.get("reason"),
    }
    return prior, payload, provenance


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior", type=Path, required=True, help="Original probe-result.json; never modified")
    parser.add_argument("--out", type=Path, required=True, help="New evidence directory")
    parser.add_argument("--image", type=Path, help="Optional remapped path; original file SHA must match")
    parser.add_argument("--base-url", help="Defaults to prior URL; same candidate runtime/config required")
    parser.add_argument("--disconnect-after", type=float, default=6.0)
    parser.add_argument("--drain-timeout", type=float, default=15.0)
    args = parser.parse_args(argv)
    if args.disconnect_after <= 0 or args.drain_timeout <= 0:
        parser.error("timeouts must be positive")
    prior, payload, provenance = prepare_prior(args.prior, args.image)
    base_url = (args.base_url or prior["base_url"]).rstrip("/")
    if not base_url.endswith("/v1"):
        parser.error("base-url must end in /v1")
    args.out.mkdir(parents=True, exist_ok=False)
    atomic_json(args.out / "fault-request.json", payload)
    report = {
        "kind": "F06_CANCEL_ONLY_FAULT_INJECTION", "quality_evidence": False,
        "performance_evidence": False, "formal_C0_sampling": False,
        "base_url": base_url, "model": prior["model"], "provenance": provenance,
        "fault_only_changes": {"min_tokens": payload["min_tokens"], "ignore_eos": True,
                               "max_tokens": payload["max_tokens"], "disconnect_after_seconds": args.disconnect_after},
        "protocol_support_sources": PROTOCOL_SOURCES,
        "precondition": "Same candidate runtime, weights, flags and tokenizer as prior; exclusive idle service",
        "retry_policy": "One changed fault request only; no automatic retry or loop if activity remains unobservable",
    }
    api_key = os.environ.get("OCR_API_KEY", "local-only")
    client = VLLMClient(base_url, prior["model"], api_key)
    result = cancellation_probe(client, payload, Metrics(base_url[:-3], args.out / "metrics", api_key),
                                args.out, args.disconnect_after, args.drain_timeout)
    report.update(status=result["status"], cancellation=result)
    atomic_json(args.out / "cancel-result.json", report)
    print(json.dumps({"status": report["status"], "out": str(args.out),
                      "queue_drain_status": result["queue_drain_status"],
                      "observed_active": result.get("observed_active_before_disconnect"),
                      "abort_counter_increased": result.get("abort_counter_increased"),
                      "reason": result.get("reason")}))
    return 0 if report["status"] == "PASS" else 1 if report["status"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
