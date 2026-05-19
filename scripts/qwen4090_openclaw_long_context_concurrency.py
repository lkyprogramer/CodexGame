#!/usr/bin/env python3
"""Long-context concurrency probes for Qwen MTP OpenClaw serving."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


MARKER_PREFIX = "OPENCLAW_LONG_CTX_CONCURRENCY_4090_MTP4"


def post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str, timeout: int) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_ready(base_url: str, timeout_s: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last_error = ""
    while time.monotonic() < deadline:
        try:
            models = get_json(f"{base_url}/v1/models", 5)
            if "error" not in models:
                return models
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
        time.sleep(2)
    raise RuntimeError(f"server not ready after {timeout_s}s: {last_error}")


def build_prompt(words: int, marker: str, worker: int) -> str:
    front = " ".join(
        f"repo_file_{worker}_{i:05d}: OpenClaw scheduler trace, patch queue, harmless telemetry, "
        f"tool result, dependency graph, retry budget, context window note."
        for i in range(words)
    )
    back = " ".join(
        f"runtime_log_{worker}_{i:05d}: gateway healthy, upstream slow, gpu memory stable, "
        f"executor should preserve exact markers and avoid destructive commands."
        for i in range(words)
    )
    return (
        "You are evaluating OpenClaw long-context retrieval under concurrent load.\n"
        "Return only the exact marker string. Do not add explanation, quotes, markdown, or whitespace.\n\n"
        f"{front}\n\n"
        f"CRITICAL_EXACT_MARKER_FOR_WORKER_{worker}: {marker}\n\n"
        f"{back}\n\n"
        "Return only the exact marker string."
    )


def run_case(
    base_url: str,
    model: str,
    lane: str,
    words: int,
    worker: int,
    timeout: int,
    max_tokens: int,
) -> dict[str, Any]:
    marker = f"{MARKER_PREFIX}_{lane}_W{worker}_WORDS{words}".replace("-", "_").replace(".", "_")
    prompt = build_prompt(words, marker, worker)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": max_tokens,
        "stream": False,
    }

    started = time.perf_counter()
    try:
        response = post_json(f"{base_url}/v1/chat/completions", payload, timeout)
        ok = True
        error = None
    except urllib.error.HTTPError as exc:
        ok = False
        response = {"status": exc.code, "body": exc.read().decode("utf-8", errors="replace")}
        error = repr(exc)
    except Exception as exc:  # noqa: BLE001
        ok = False
        response = {}
        error = repr(exc)
    elapsed = time.perf_counter() - started

    content = ""
    finish_reason = None
    usage: dict[str, Any] = {}
    timings: dict[str, Any] = {}
    if ok:
        choices = response.get("choices") or []
        if choices:
            choice = choices[0]
            message = choice.get("message") or {}
            content = message.get("content") or ""
            finish_reason = choice.get("finish_reason")
        usage = response.get("usage") or {}
        timings = response.get("timings") or {}

    completion_tokens = usage.get("completion_tokens") or 0
    prompt_tokens = usage.get("prompt_tokens") or 0
    prompt_ms = timings.get("prompt_ms") or 0
    predicted_ms = timings.get("predicted_ms") or 0
    draft_n = timings.get("draft_n") or 0
    draft_accepted = timings.get("draft_n_accepted") or 0
    body = response.get("body") if isinstance(response, dict) else None
    return {
        "lane": lane,
        "case_id": f"long_ctx_w{worker}_words{words}",
        "worker": worker,
        "words": words,
        "ok": ok,
        "elapsed_s": elapsed,
        "prompt_chars": len(prompt),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tokens_per_sec": completion_tokens / elapsed if completion_tokens else None,
        "finish_reason": finish_reason,
        "expected_marker": marker,
        "content": content,
        "exact_match": content.strip() == marker if ok else False,
        "think_leak": content.lstrip().startswith("<think>") if ok else False,
        "prompt_tokens_per_sec": prompt_tokens / (prompt_ms / 1000) if prompt_ms else None,
        "decode_tokens_per_sec": completion_tokens / (predicted_ms / 1000) if predicted_ms else None,
        "draft_n": draft_n,
        "draft_n_accepted": draft_accepted,
        "draft_accept_rate": draft_accepted / draft_n if draft_n else None,
        "error": error,
        "error_body": body,
        "usage": usage,
        "timings": timings,
    }


def run_batch(
    base_url: str,
    model: str,
    lane: str,
    words: int,
    concurrency: int,
    timeout: int,
    max_tokens: int,
) -> list[dict[str, Any]]:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(run_case, base_url, model, lane, words, worker + 1, timeout, max_tokens)
            for worker in range(concurrency)
        ]
        results = [future.result() for future in futures]
    batch_elapsed = time.perf_counter() - started
    total_prompt_tokens = sum(result.get("prompt_tokens") or 0 for result in results)
    total_completion_tokens = sum(result.get("completion_tokens") or 0 for result in results)
    for result in results:
        result["batch_elapsed_s"] = batch_elapsed
        result["batch_prompt_tokens_per_sec"] = total_prompt_tokens / batch_elapsed if batch_elapsed else None
        result["batch_completion_tokens_per_sec"] = total_completion_tokens / batch_elapsed if batch_elapsed else None
    return results


def summarize(results: list[dict[str, Any]], models: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    ok = [result for result in results if result["ok"]]
    exact = [result for result in results if result.get("exact_match")]
    errors = [result for result in results if not result["ok"]]
    prompt_tps = [result["prompt_tokens_per_sec"] for result in ok if result.get("prompt_tokens_per_sec")]
    decode_tps = [result["decode_tokens_per_sec"] for result in ok if result.get("decode_tokens_per_sec")]
    accept_rates = [result["draft_accept_rate"] for result in ok if result.get("draft_accept_rate") is not None]
    return {
        "lane": args.lane,
        "words": args.words,
        "concurrency": args.concurrency,
        "models": models,
        "summary": {
            "case_count": len(results),
            "ok_count": len(ok),
            "exact_match_count": len(exact),
            "error_count": len(errors),
            "think_leak_count": sum(1 for result in ok if result.get("think_leak")),
            "avg_prompt_tokens": statistics.mean([r["prompt_tokens"] for r in ok]) if ok else None,
            "max_prompt_tokens": max([r["prompt_tokens"] for r in ok], default=None),
            "avg_elapsed_s": statistics.mean([r["elapsed_s"] for r in ok]) if ok else None,
            "max_elapsed_s": max([r["elapsed_s"] for r in ok], default=None),
            "avg_prompt_tokens_per_sec": statistics.mean(prompt_tps) if prompt_tps else None,
            "avg_decode_tokens_per_sec": statistics.mean(decode_tps) if decode_tps else None,
            "avg_draft_accept_rate": statistics.mean(accept_rates) if accept_rates else None,
            "batch_elapsed_s": results[0].get("batch_elapsed_s") if results else None,
            "batch_prompt_tokens_per_sec": results[0].get("batch_prompt_tokens_per_sec") if results else None,
            "batch_completion_tokens_per_sec": results[0].get("batch_completion_tokens_per_sec") if results else None,
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--words", type=int, required=True)
    parser.add_argument("--concurrency", type=int, required=True)
    parser.add_argument("--ready-timeout", type=int, default=300)
    parser.add_argument("--request-timeout", type=int, default=1800)
    parser.add_argument("--max-tokens", type=int, default=64)
    args = parser.parse_args()

    models = wait_ready(args.base_url, args.ready_timeout)
    results = run_batch(
        args.base_url,
        args.model,
        args.lane,
        args.words,
        args.concurrency,
        args.request_timeout,
        args.max_tokens,
    )
    summary = summarize(results, models, args)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{args.lane}.jsonl"
    with raw_path.open("w", encoding="utf-8") as raw:
        for result in results:
            raw.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(
                json.dumps(
                    {
                        "case_id": result["case_id"],
                        "ok": result["ok"],
                        "exact_match": result["exact_match"],
                        "elapsed_s": result["elapsed_s"],
                        "prompt_tokens": result["prompt_tokens"],
                        "prompt_tokens_per_sec": result["prompt_tokens_per_sec"],
                        "decode_tokens_per_sec": result["decode_tokens_per_sec"],
                        "error_body": result["error_body"],
                    },
                    ensure_ascii=False,
                )
            )
    (out_dir / f"{args.lane}.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
