#!/usr/bin/env python3
"""Run small OpenAI-compatible perf and quality probes against a llama.cpp server."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


QUALITY_CASES = [
    {
        "id": "math_reasoning_cn",
        "category": "quality",
        "prompt": (
            "请用简洁但完整的推理回答：一个 3 位数的各位数字之和为 18，"
            "百位比个位小 2，十位是个位的 2 倍。这个三位数是多少？"
        ),
        "max_tokens": 220,
    },
    {
        "id": "code_review",
        "category": "quality",
        "prompt": (
            "Review this Python function and return the corrected code plus one sentence explaining the bug:\n"
            "```python\n"
            "def top_k(items, k):\n"
            "    items.sort(reverse=True)\n"
            "    return items[:k]\n"
            "```\n"
            "Constraint: do not mutate the caller's list."
        ),
        "max_tokens": 220,
    },
    {
        "id": "instruction_following",
        "category": "quality",
        "prompt": (
            "只输出 JSON，不要 markdown。字段为 answer 和 checks。"
            "answer 用一句话说明为什么长上下文推理测试需要同时测 TTFT 和输出质量；"
            "checks 是 3 个短字符串数组。"
        ),
        "max_tokens": 180,
    },
]


PERF_CASES = [
    {
        "id": "perf_short_cn",
        "category": "perf",
        "prompt": "用中文给出 5 条 4090 上 GGUF 推理压测时最容易误判的性能指标，每条不超过 20 字。",
        "max_tokens": 160,
    },
    {
        "id": "perf_code",
        "category": "perf",
        "prompt": "Write a compact Python function that computes rolling p50/p95 latency from a list of floats.",
        "max_tokens": 180,
    },
]


def make_niah_case(ctx_words: int) -> dict[str, Any]:
    filler = " ".join(f"record_{i:05d}: background telemetry is normal." for i in range(ctx_words))
    needle = "NEEDLE_CODE_4090_MTP_DFLASH"
    prompt = (
        f"{filler}\n\n"
        f"Important hidden fact: the retrieval needle is {needle}.\n\n"
        f"{filler}\n\n"
        "Question: What is the exact retrieval needle? Return only the needle."
    )
    return {
        "id": f"niah_{ctx_words}_words",
        "category": "quality_long_context",
        "prompt": prompt,
        "expected_contains": needle,
        "max_tokens": 64,
    }


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
            return get_json(f"{base_url}/v1/models", 5)
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            time.sleep(2)
    raise RuntimeError(f"server not ready after {timeout_s}s: {last_error}")


def run_case(base_url: str, model: str, case: dict[str, Any], timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": case["prompt"]}],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": case["max_tokens"],
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
    usage = {}
    if ok:
        choices = response.get("choices") or []
        if choices:
            content = choices[0].get("message", {}).get("content", "")
        usage = response.get("usage") or {}
    completion_tokens = usage.get("completion_tokens") or usage.get("predicted_n") or 0
    prompt_tokens = usage.get("prompt_tokens") or 0
    tokens_per_sec = completion_tokens / elapsed if completion_tokens else None
    expected = case.get("expected_contains")
    return {
        "case_id": case["id"],
        "category": case["category"],
        "ok": ok,
        "elapsed_s": elapsed,
        "prompt_chars": len(case["prompt"]),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tokens_per_sec": tokens_per_sec,
        "expected_contains": expected,
        "expected_found": (expected in content) if expected else None,
        "content": content,
        "usage": usage,
        "error": error,
        "response": response,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    ok_results = [r for r in results if r["ok"]]
    perf_tps = [r["tokens_per_sec"] for r in ok_results if r["tokens_per_sec"] is not None]
    elapsed = [r["elapsed_s"] for r in ok_results]
    return {
        "case_count": len(results),
        "ok_count": len(ok_results),
        "error_count": len(results) - len(ok_results),
        "avg_tokens_per_sec": statistics.mean(perf_tps) if perf_tps else None,
        "median_tokens_per_sec": statistics.median(perf_tps) if perf_tps else None,
        "avg_elapsed_s": statistics.mean(elapsed) if elapsed else None,
        "quality_long_context_pass": all(
            r.get("expected_found") is not False for r in results if r["category"] == "quality_long_context"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", default="test-model")
    parser.add_argument("--lane", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--ready-timeout", type=int, default=180)
    parser.add_argument("--request-timeout", type=int, default=240)
    parser.add_argument("--niah-words", type=int, default=1200)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    models = wait_ready(args.base_url, args.ready_timeout)
    cases = PERF_CASES + QUALITY_CASES + [make_niah_case(args.niah_words)]
    results = []
    raw_path = out_dir / f"{args.lane}.jsonl"
    with raw_path.open("w", encoding="utf-8") as raw:
        for case in cases:
            result = run_case(args.base_url, args.model, case, args.request_timeout)
            result["lane"] = args.lane
            raw.write(json.dumps(result, ensure_ascii=False) + "\n")
            raw.flush()
            results.append(result)
    summary = {
        "lane": args.lane,
        "base_url": args.base_url,
        "models": models,
        "summary": summarize(results),
        "results": [
            {k: v for k, v in r.items() if k not in {"response"}}
            for r in results
        ],
    }
    (out_dir / f"{args.lane}.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
