#!/usr/bin/env python3
"""Extreme throughput probes for Qwen3.6 MTP on an OpenAI-compatible server."""

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


def post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str, timeout: int) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


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


def build_generation_prompt(max_tokens: int, case_id: str) -> str:
    return (
        f"Write exactly {max_tokens} tokens of deterministic benchmark prose for case {case_id}. "
        "Use numbered compact sentences about RTX 4090 inference, MTP speculative decoding, "
        "KV cache pressure, prompt cache behavior, batching, latency percentiles, and throughput limits. "
        "Do not use markdown tables. Keep going until the token budget is exhausted."
    )


def build_cache_prompt(words: int, case_id: str) -> str:
    prefix = " ".join(f"cache_record_{i:05d}: stable telemetry." for i in range(words))
    return (
        f"{prefix}\n\n"
        f"Case marker: {case_id}. Summarize the prompt cache behavior in five concise Chinese bullets. "
        "Mention repeated prefix reuse, prefill time, decode time, and exact-match cleanliness."
    )


def run_chat(base_url: str, model: str, prompt: str, max_tokens: int, timeout: int, case_id: str) -> dict[str, Any]:
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
    if ok:
        choices = response.get("choices") or []
        if choices:
            choice = choices[0]
            content = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason")
        usage = response.get("usage") or {}

    completion_tokens = usage.get("completion_tokens") or 0
    prompt_tokens = usage.get("prompt_tokens") or 0
    return {
        "case_id": case_id,
        "ok": ok,
        "elapsed_s": elapsed,
        "prompt_chars": len(prompt),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tokens_per_sec": completion_tokens / elapsed if completion_tokens else None,
        "finish_reason": finish_reason,
        "think_leak": content.lstrip().startswith("<think>"),
        "content_prefix": content[:240],
        "usage": usage,
        "error": error,
        "response": response,
    }


def single_long_cases(base_url: str, model: str, lengths: list[int], repeats: int, timeout: int) -> list[dict[str, Any]]:
    results = []
    for length in lengths:
        for rep in range(1, repeats + 1):
            case_id = f"single_len{length}_rep{rep}"
            results.append(run_chat(base_url, model, build_generation_prompt(length, case_id), length, timeout, case_id))
    return results


def concurrent_cases(
    base_url: str,
    model: str,
    lengths: list[int],
    concurrency: int,
    batches: int,
    timeout: int,
) -> list[dict[str, Any]]:
    all_results = []
    for length in lengths:
        for batch in range(1, batches + 1):
            batch_started = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = []
                for worker in range(1, concurrency + 1):
                    case_id = f"conc{concurrency}_len{length}_batch{batch}_worker{worker}"
                    futures.append(
                        executor.submit(
                            run_chat,
                            base_url,
                            model,
                            build_generation_prompt(length, case_id),
                            length,
                            timeout,
                            case_id,
                        )
                    )
                results = [future.result() for future in futures]
            batch_elapsed = time.perf_counter() - batch_started
            batch_tokens = sum(r.get("completion_tokens") or 0 for r in results)
            for r in results:
                r["batch_id"] = f"conc{concurrency}_len{length}_batch{batch}"
                r["batch_elapsed_s"] = batch_elapsed
                r["batch_completion_tokens"] = batch_tokens
                r["batch_tokens_per_sec"] = batch_tokens / batch_elapsed if batch_tokens else None
            all_results.extend(results)
    return all_results


def cache_cases(base_url: str, model: str, prompt_words: int, repeats: int, max_tokens: int, timeout: int) -> list[dict[str, Any]]:
    prompt = build_cache_prompt(prompt_words, "shared-cache-prompt")
    results = []
    for rep in range(1, repeats + 1):
        case_id = f"cache_shared_rep{rep}"
        results.append(run_chat(base_url, model, prompt, max_tokens, timeout, case_id))
    for rep in range(1, repeats + 1):
        case_id = f"cache_unique_rep{rep}"
        unique_prompt = build_cache_prompt(prompt_words, case_id)
        results.append(run_chat(base_url, model, unique_prompt, max_tokens, timeout, case_id))
    return results


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((pct / 100) * (len(ordered) - 1))))
    return ordered[idx]


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in results if r["ok"]]
    tps = [r["tokens_per_sec"] for r in ok if r["tokens_per_sec"] is not None]
    batch_tps = []
    seen_batches = set()
    for r in ok:
        batch_id = r.get("batch_id")
        if batch_id and batch_id not in seen_batches and r.get("batch_tokens_per_sec") is not None:
            seen_batches.add(batch_id)
            batch_tps.append(r["batch_tokens_per_sec"])
    elapsed = [r["elapsed_s"] for r in ok]
    return {
        "case_count": len(results),
        "ok_count": len(ok),
        "error_count": len(results) - len(ok),
        "avg_tokens_per_sec": statistics.mean(tps) if tps else None,
        "median_tokens_per_sec": statistics.median(tps) if tps else None,
        "p95_elapsed_s": percentile(elapsed, 95),
        "avg_batch_tokens_per_sec": statistics.mean(batch_tps) if batch_tps else None,
        "median_batch_tokens_per_sec": statistics.median(batch_tps) if batch_tps else None,
        "think_leak_count": sum(1 for r in ok if r.get("think_leak")),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--mode", choices=["single-long", "concurrency", "cache"], required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--ready-timeout", type=int, default=300)
    parser.add_argument("--request-timeout", type=int, default=1800)
    parser.add_argument("--lengths", default="2048,4096,8192")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--batches", type=int, default=3)
    parser.add_argument("--prompt-words", type=int, default=5000)
    parser.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args()

    models = wait_ready(args.base_url, args.ready_timeout)
    lengths = [int(item) for item in args.lengths.split(",") if item]
    if args.mode == "single-long":
        results = single_long_cases(args.base_url, args.model, lengths, args.repeats, args.request_timeout)
    elif args.mode == "concurrency":
        results = concurrent_cases(args.base_url, args.model, lengths, args.concurrency, args.batches, args.request_timeout)
    else:
        results = cache_cases(args.base_url, args.model, args.prompt_words, args.repeats, args.max_tokens, args.request_timeout)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{args.lane}.jsonl"
    with raw_path.open("w", encoding="utf-8") as raw:
        for result in results:
            result["lane"] = args.lane
            raw.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(json.dumps({k: result.get(k) for k in ["case_id", "ok", "elapsed_s", "tokens_per_sec", "batch_tokens_per_sec", "think_leak"]}, ensure_ascii=False))

    summary = {
        "lane": args.lane,
        "mode": args.mode,
        "models": models,
        "summary": summarize(results),
        "results": [{k: v for k, v in r.items() if k != "response"} for r in results],
    }
    (out_dir / f"{args.lane}.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
