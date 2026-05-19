#!/usr/bin/env python3
"""Fixed-concurrency long-context and prompt-cache evaluation for OpenClaw."""

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


MARKER_PREFIX = "OPENCLAW_FIXED_C2_CACHE_4090_MTP4"


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


def build_prompt(words: int, marker: str, worker: int) -> str:
    front = " ".join(
        f"repo_scan_worker_{worker}_{i:05d}: OpenClaw agent trace, source file summary, tool schema, "
        f"build log fragment, dependency edge, harmless context filler, retry policy."
        for i in range(words)
    )
    back = " ".join(
        f"ci_log_worker_{worker}_{i:05d}: executor queue event, gateway response, upstream timing, "
        f"patch review note, file ownership clue, context retention check."
        for i in range(words)
    )
    return (
        "You are testing OpenClaw fixed-concurrency long-context retrieval.\n"
        "Return only the exact marker string. No markdown, no quotes, no explanation.\n\n"
        f"{front}\n\n"
        f"EXACT_MARKER_FOR_WORKER_{worker}: {marker}\n\n"
        f"{back}\n\n"
        "Return only the exact marker string."
    )


def run_case(
    base_url: str,
    model: str,
    lane: str,
    words: int,
    worker: int,
    round_name: str,
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
    usage: dict[str, Any] = {}
    timings: dict[str, Any] = {}
    finish_reason = None
    if ok:
        choices = response.get("choices") or []
        if choices:
            choice = choices[0]
            finish_reason = choice.get("finish_reason")
            message = choice.get("message") or {}
            content = message.get("content") or ""
        usage = response.get("usage") or {}
        timings = response.get("timings") or {}

    prompt_tokens = usage.get("prompt_tokens") or 0
    completion_tokens = usage.get("completion_tokens") or 0
    prompt_ms = timings.get("prompt_ms") or 0
    predicted_ms = timings.get("predicted_ms") or 0
    cache_n = timings.get("cache_n")
    draft_n = timings.get("draft_n") or 0
    draft_accepted = timings.get("draft_n_accepted") or 0
    body = response.get("body") if isinstance(response, dict) else None
    return {
        "lane": lane,
        "round": round_name,
        "case_id": f"{round_name}_w{worker}_words{words}",
        "worker": worker,
        "words": words,
        "ok": ok,
        "elapsed_s": elapsed,
        "prompt_chars": len(prompt),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "finish_reason": finish_reason,
        "expected_marker": marker,
        "content": content,
        "exact_match": content.strip() == marker if ok else False,
        "think_leak": content.lstrip().startswith("<think>") if ok else False,
        "cache_n": cache_n,
        "prompt_ms": prompt_ms,
        "predicted_ms": predicted_ms,
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
    round_name: str,
    timeout: int,
    max_tokens: int,
) -> list[dict[str, Any]]:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(run_case, base_url, model, lane, words, worker + 1, round_name, timeout, max_tokens)
            for worker in range(concurrency)
        ]
        results = [future.result() for future in futures]
    batch_elapsed = time.perf_counter() - started
    total_prompt_tokens = sum(r.get("prompt_tokens") or 0 for r in results)
    total_completion_tokens = sum(r.get("completion_tokens") or 0 for r in results)
    for result in results:
        result["batch_elapsed_s"] = batch_elapsed
        result["batch_prompt_tokens_per_sec"] = total_prompt_tokens / batch_elapsed if batch_elapsed else None
        result["batch_completion_tokens_per_sec"] = total_completion_tokens / batch_elapsed if batch_elapsed else None
    return results


def summarize_round(results: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in results if r["ok"]]
    prompt_tps = [r["prompt_tokens_per_sec"] for r in ok if r.get("prompt_tokens_per_sec")]
    decode_tps = [r["decode_tokens_per_sec"] for r in ok if r.get("decode_tokens_per_sec")]
    cache_ns = [r["cache_n"] for r in ok if r.get("cache_n") is not None]
    return {
        "case_count": len(results),
        "ok_count": len(ok),
        "exact_match_count": sum(1 for r in ok if r.get("exact_match")),
        "error_count": len(results) - len(ok),
        "think_leak_count": sum(1 for r in ok if r.get("think_leak")),
        "avg_prompt_tokens": statistics.mean([r["prompt_tokens"] for r in ok]) if ok else None,
        "max_prompt_tokens": max([r["prompt_tokens"] for r in ok], default=None),
        "avg_elapsed_s": statistics.mean([r["elapsed_s"] for r in ok]) if ok else None,
        "max_elapsed_s": max([r["elapsed_s"] for r in ok], default=None),
        "avg_cache_n": statistics.mean(cache_ns) if cache_ns else None,
        "max_cache_n": max(cache_ns, default=None),
        "avg_prompt_tokens_per_sec": statistics.mean(prompt_tps) if prompt_tps else None,
        "avg_decode_tokens_per_sec": statistics.mean(decode_tps) if decode_tps else None,
        "batch_elapsed_s": results[0].get("batch_elapsed_s") if results else None,
        "batch_prompt_tokens_per_sec": results[0].get("batch_prompt_tokens_per_sec") if results else None,
        "batch_completion_tokens_per_sec": results[0].get("batch_completion_tokens_per_sec") if results else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--words", type=int, required=True)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--rounds", default="cold,warm")
    parser.add_argument("--ready-timeout", type=int, default=420)
    parser.add_argument("--request-timeout", type=int, default=2400)
    parser.add_argument("--max-tokens", type=int, default=64)
    args = parser.parse_args()

    models = wait_ready(args.base_url, args.ready_timeout)
    all_results: list[dict[str, Any]] = []
    round_names = [part.strip() for part in args.rounds.split(",") if part.strip()]
    for round_name in round_names:
        batch = run_batch(
            args.base_url,
            args.model,
            args.lane,
            args.words,
            args.concurrency,
            round_name,
            args.request_timeout,
            args.max_tokens,
        )
        all_results.extend(batch)
        time.sleep(2)

    by_round = {
        round_name: summarize_round([r for r in all_results if r["round"] == round_name])
        for round_name in round_names
    }
    summary = {
        "lane": args.lane,
        "words": args.words,
        "concurrency": args.concurrency,
        "rounds": round_names,
        "models": models,
        "summary_by_round": by_round,
        "results": all_results,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{args.lane}.jsonl"
    with raw_path.open("w", encoding="utf-8") as raw:
        for result in all_results:
            raw.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(
                json.dumps(
                    {
                        "case_id": result["case_id"],
                        "ok": result["ok"],
                        "exact_match": result["exact_match"],
                        "elapsed_s": result["elapsed_s"],
                        "prompt_tokens": result["prompt_tokens"],
                        "cache_n": result["cache_n"],
                        "prompt_ms": result["prompt_ms"],
                        "batch_elapsed_s": result["batch_elapsed_s"],
                        "error_body": result["error_body"],
                    },
                    ensure_ascii=False,
                )
            )
    (out_dir / f"{args.lane}.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(by_round, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
