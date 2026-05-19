#!/usr/bin/env python3
"""Run next-round OpenAI-compatible Qwen3.6 4090 probes."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


NEEDLES = [
    "NEEDLE_ALPHA_4090_PFLASH",
    "NEEDLE_BETA_4090_PFLASH",
    "NEEDLE_GAMMA_4090_PFLASH",
]


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


def run_chat_case(base_url: str, model: str, case: dict[str, Any], timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": case["messages"],
        "temperature": case.get("temperature", 0),
        "top_p": case.get("top_p", 1),
        "max_tokens": case["max_tokens"],
        "stream": False,
    }
    if case.get("stop"):
        payload["stop"] = case["stop"]
    return run_payload(base_url, "/v1/chat/completions", payload, case, timeout)


def run_completion_case(base_url: str, model: str, case: dict[str, Any], timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": case["prompt"],
        "temperature": case.get("temperature", 0),
        "top_p": case.get("top_p", 1),
        "n_predict": case["max_tokens"],
        "max_tokens": case["max_tokens"],
        "stream": False,
    }
    if case.get("stop"):
        payload["stop"] = case["stop"]
    return run_payload(base_url, "/completion", payload, case, timeout)


def run_payload(base_url: str, path: str, payload: dict[str, Any], case: dict[str, Any], timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = post_json(f"{base_url}{path}", payload, timeout)
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
    finish_reason = None
    if ok:
        if path == "/completion":
            content = response.get("content") or response.get("response") or ""
            usage = {
                "prompt_tokens": response.get("tokens_evaluated") or response.get("prompt_tokens") or 0,
                "completion_tokens": response.get("tokens_predicted") or response.get("completion_tokens") or 0,
                "total_tokens": (response.get("tokens_evaluated") or 0) + (response.get("tokens_predicted") or 0),
            }
            finish_reason = response.get("stop_type") or response.get("stopped_eos") or response.get("stop")
        else:
            choices = response.get("choices") or []
            if choices:
                choice = choices[0]
                content = choice.get("message", {}).get("content", "")
                finish_reason = choice.get("finish_reason")
            usage = response.get("usage") or {}

    completion_tokens = usage.get("completion_tokens") or usage.get("predicted_n") or usage.get("tokens_predicted") or 0
    prompt_tokens = usage.get("prompt_tokens") or usage.get("prompt_n") or usage.get("tokens_evaluated") or 0
    expected = case.get("expected_contains")
    expected_all = case.get("expected_all") or []
    return {
        "case_id": case["id"],
        "category": case["category"],
        "endpoint": path,
        "ok": ok,
        "elapsed_s": elapsed,
        "prompt_chars": len(case.get("prompt", "") or json.dumps(case.get("messages", ""), ensure_ascii=False)),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tokens_per_sec": completion_tokens / elapsed if completion_tokens else None,
        "finish_reason": finish_reason,
        "expected_contains": expected,
        "expected_found": (expected in content) if expected else None,
        "expected_all": expected_all,
        "expected_all_found": all(item in content for item in expected_all) if expected_all else None,
        "content": content,
        "usage": usage,
        "error": error,
        "response": response,
    }


def mtp_matrix_cases(lengths: list[int], repeats: int) -> list[dict[str, Any]]:
    cases = []
    for max_tokens in lengths:
        for rep in range(1, repeats + 1):
            cases.append(
                {
                    "id": f"mtp_len{max_tokens}_rep{rep}",
                    "category": "mtp_throughput",
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                f"Write a deterministic benchmark passage of about {max_tokens} tokens. "
                                "Use numbered sentences about GPU inference bottlenecks, KV cache, batching, "
                                "speculative decoding, and long-context retrieval. Do not include code fences."
                            ),
                        }
                    ],
                    "max_tokens": max_tokens,
                }
            )
    return cases


def format_probe_cases() -> list[dict[str, Any]]:
    prompt = (
        "只输出 JSON，不要 markdown，不要解释。"
        "字段 answer 为字符串，checks 为 3 个短字符串数组。"
        "answer 说明为什么 exact-match 测试不能包含多余包装。"
    )
    return [
        {
            "id": "chat_json_baseline",
            "category": "format_probe",
            "kind": "chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 160,
        },
        {
            "id": "chat_json_system_no_think",
            "category": "format_probe",
            "kind": "chat",
            "messages": [
                {"role": "system", "content": "Return final answers only. Do not output think tags."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 160,
        },
        {
            "id": "chat_json_stop_think_close",
            "category": "format_probe",
            "kind": "chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 160,
            "stop": ["</think>"],
        },
        {
            "id": "completion_json_raw_prompt",
            "category": "format_probe",
            "kind": "completion",
            "prompt": prompt,
            "max_tokens": 160,
        },
    ]


def pflash_quality_cases(ctx_words: int) -> list[dict[str, Any]]:
    filler = " ".join(f"segment_{i:05d}: background telemetry remains stable." for i in range(ctx_words))
    multi = (
        f"{filler}\n\n"
        f"Needle A: {NEEDLES[0]}\n"
        f"Needle B: {NEEDLES[1]}\n"
        f"Needle C: {NEEDLES[2]}\n\n"
        f"{filler}\n\n"
        "Return the three needles as a JSON array in A, B, C order."
    )
    summary = (
        f"{filler}\n\n"
        "Important report: PFlash compression kept sparse retrieval anchors, reduced prefill cost, "
        "and preserved the final answer for long-context needle retrieval.\n\n"
        f"{filler}\n\n"
        "用三条中文要点总结 Important report，只输出 JSON 数组。"
    )
    fact = (
        f"{filler}\n\n"
        "Fact block: benchmark winner is MTP for raw decode speed; PFlash winner is quality under compression; "
        "DFlash no-compression failed the 32K needle test.\n\n"
        f"{filler}\n\n"
        "Answer in JSON with keys raw_speed, compressed_quality, failed_lane."
    )
    code = (
        f"{filler}\n\n"
        "Code snippet to retrieve:\n"
        "```python\n"
        "def stable_top_k(items, k):\n"
        "    return sorted(items, reverse=True)[:k]\n"
        "```\n\n"
        f"{filler}\n\n"
        "Return only the Python function body line from the snippet."
    )
    return [
        {
            "id": "pflash_multi_needle",
            "category": "pflash_quality",
            "messages": [{"role": "user", "content": multi}],
            "max_tokens": 128,
            "expected_all": NEEDLES,
        },
        {
            "id": "pflash_summary",
            "category": "pflash_quality",
            "messages": [{"role": "user", "content": summary}],
            "max_tokens": 180,
            "expected_all": ["压缩", "检索", "长上下文"],
        },
        {
            "id": "pflash_fact_qa",
            "category": "pflash_quality",
            "messages": [{"role": "user", "content": fact}],
            "max_tokens": 160,
            "expected_all": ["MTP", "PFlash", "DFlash"],
        },
        {
            "id": "pflash_code_retrieval",
            "category": "pflash_quality",
            "messages": [{"role": "user", "content": code}],
            "max_tokens": 96,
            "expected_contains": "return sorted(items, reverse=True)[:k]",
        },
    ]


def dflash_repro_cases(ctx_words: int) -> list[dict[str, Any]]:
    filler = " ".join(f"record_{i:05d}: background telemetry is normal." for i in range(ctx_words))
    needle = "NEEDLE_CODE_4090_MTP_DFLASH"
    prompt = (
        f"{filler}\n\n"
        f"Important hidden fact: the retrieval needle is {needle}.\n\n"
        f"{filler}\n\n"
        "Question: What is the exact retrieval needle? Return only the needle."
    )
    return [
        {
            "id": f"dflash_niah_{ctx_words}_words",
            "category": "dflash_repro",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 64,
            "expected_contains": needle,
        }
    ]


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    ok_results = [r for r in results if r["ok"]]
    tps = [r["tokens_per_sec"] for r in ok_results if r["tokens_per_sec"] is not None]
    elapsed = [r["elapsed_s"] for r in ok_results]
    return {
        "case_count": len(results),
        "ok_count": len(ok_results),
        "error_count": len(results) - len(ok_results),
        "avg_tokens_per_sec": statistics.mean(tps) if tps else None,
        "median_tokens_per_sec": statistics.median(tps) if tps else None,
        "p50_elapsed_s": statistics.median(elapsed) if elapsed else None,
        "p95_elapsed_s": percentile(elapsed, 95) if elapsed else None,
        "expected_all_pass": all(
            r.get("expected_found") is not False and r.get("expected_all_found") is not False for r in results
        ),
    }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((pct / 100) * (len(ordered) - 1))))
    return ordered[idx]


def write_outputs(out_dir: Path, lane: str, models: dict[str, Any], results: list[dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{lane}.jsonl"
    with raw_path.open("w", encoding="utf-8") as raw:
        for result in results:
            raw.write(json.dumps(result, ensure_ascii=False) + "\n")
    summary = {
        "lane": lane,
        "models": models,
        "summary": summarize(results),
        "results": [{k: v for k, v in r.items() if k != "response"} for r in results],
    }
    (out_dir / f"{lane}.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary["summary"], ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--mode", choices=["mtp-matrix", "format-probe", "pflash-quality", "dflash-repro"], required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--ready-timeout", type=int, default=240)
    parser.add_argument("--request-timeout", type=int, default=900)
    parser.add_argument("--lengths", default="128,512,2048")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--ctx-words", type=int, default=1200)
    args = parser.parse_args()

    models = wait_ready(args.base_url, args.ready_timeout)
    if args.mode == "mtp-matrix":
        cases = mtp_matrix_cases([int(item) for item in args.lengths.split(",") if item], args.repeats)
    elif args.mode == "format-probe":
        cases = format_probe_cases()
    elif args.mode == "pflash-quality":
        cases = pflash_quality_cases(args.ctx_words)
    else:
        cases = dflash_repro_cases(args.ctx_words)

    results = []
    for case in cases:
        if case.get("kind") == "completion":
            result = run_completion_case(args.base_url, args.model, case, args.request_timeout)
        else:
            result = run_chat_case(args.base_url, args.model, case, args.request_timeout)
        result["lane"] = args.lane
        results.append(result)
        print(json.dumps({k: result[k] for k in ["case_id", "ok", "elapsed_s", "tokens_per_sec", "finish_reason"]}, ensure_ascii=False))

    write_outputs(Path(args.out_dir), args.lane, models, results)


if __name__ == "__main__":
    main()
