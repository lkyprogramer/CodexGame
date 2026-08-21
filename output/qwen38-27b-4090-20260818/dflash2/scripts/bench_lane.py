#!/usr/bin/env python3
"""Four-class lane bench for the DFlash2 trial. Runs against a live llama-server."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

NEEDLE_A = "FACT_A_RUNTIME_TICK_MS=200"
NEEDLE_B = "FACT_B_PROTOCOL_VERSION=v1"
NEEDLE_C = "FACT_C_REPLAY_DIR=data/replay"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Run a short Python snippet in a sandbox.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    },
]


def gpu() -> dict[str, Any]:
    try:
        raw = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.free,utilization.gpu,power.draw,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=5,
        ).strip()
        used, free, util, power, temp = [p.strip() for p in raw.split(",")]
        return {
            "memory_used_mib": float(used),
            "memory_free_mib": float(free),
            "utilization_gpu_pct": float(util),
            "power_w": float(power),
            "temperature_c": float(temp),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


def get_json(url: str, timeout: int = 10) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as res:
        return json.loads(res.read().decode())


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"error_text": body}
        return exc.code, parsed


def wait_ready(base: str, timeout_s: int = 900) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last = ""
    while time.monotonic() < deadline:
        try:
            value = get_json(f"{base}/v1/models", timeout=5)
            if value.get("data") or value.get("models"):
                return value
        except Exception as exc:  # noqa: BLE001
            last = repr(exc)
        time.sleep(2)
    raise RuntimeError(f"server not ready: {last}")


def pad_prompt(target_tokens: int) -> str:
    unit = (
        "OpenClaw keeps simulation authority in apps/game-runtime. "
        "The client is presentation-only. tickMs is 200. protocol is v1. "
        "Replay lives under data/replay. "
    )
    # ~16 tokens per unit at 4 chars/token heuristic; overshoot then slice.
    reps = max(1, target_tokens // 16)
    text = unit * reps
    return text[: target_tokens * 4]


def chat(
    base: str,
    model: str,
    messages: list[dict[str, Any]],
    *,
    max_tokens: int,
    timeout: int,
    temperature: float,
    kwargs: dict[str, Any] | None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.95,
        "top_k": 20,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if kwargs is not None:
        payload["chat_template_kwargs"] = kwargs
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    t0 = time.perf_counter()
    status, body = post_json(f"{base}/v1/chat/completions", payload, timeout)
    elapsed = time.perf_counter() - t0
    msg = ((body.get("choices") or [{}])[0].get("message") or {})
    usage = body.get("usage") or {}
    timings = body.get("timings") or {}
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    completion = usage.get("completion_tokens") or 0
    predicted_ms = timings.get("predicted_ms")
    prompt_ms = timings.get("prompt_ms")
    decode_tps = timings.get("predicted_per_second")
    if decode_tps is None and predicted_ms:
        decode_tps = completion / (predicted_ms / 1000) if predicted_ms else None
    if decode_tps is None and completion and elapsed:
        decode_tps = completion / elapsed
    prompt_tps = timings.get("prompt_per_second")
    if prompt_tps is None and prompt_ms and usage.get("prompt_tokens"):
        prompt_tps = usage["prompt_tokens"] / (prompt_ms / 1000) if prompt_ms else None
    draft_n = timings.get("draft_n") or timings.get("n_draft")
    draft_accepted = timings.get("draft_n_accepted") or timings.get("n_draft_accepted")
    accept_rate = None
    if draft_n:
        accept_rate = (draft_accepted or 0) / draft_n
    return {
        "http": status,
        "elapsed_s": elapsed,
        "content": content,
        "reasoning": reasoning,
        "empty": not str(content).strip() and not msg.get("tool_calls"),
        "finish": ((body.get("choices") or [{}])[0].get("finish_reason")),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": completion,
        "decode_tokens_per_s": decode_tps,
        "prompt_tokens_per_s": prompt_tps,
        "draft_n": draft_n,
        "draft_n_accepted": draft_accepted,
        "accept_rate": accept_rate,
        "accept_length": timings.get("draft_mean_len") or timings.get("predicted_per_token"),
        "timings": timings,
        "tool_calls": msg.get("tool_calls") or [],
        "error": body.get("error") or body.get("error_text"),
        "gpu_after": gpu(),
    }


def cases() -> list[dict[str, Any]]:
    long_ctx = (
        pad_prompt(28000)
        + f"\n{NEEDLE_A}\n{NEEDLE_B}\n{NEEDLE_C}\n"
        + "Return JSON only: {\"tick\":...,\"protocol\":\"...\",\"replay\":\"...\"}\n"
    )
    return [
        {
            "id": "S_off_code",
            "class": "S",
            "temperature": 0.7,
            "max_tokens": 1024,
            "timeout": 180,
            "kwargs": {"enable_thinking": False, "reasoning_effort": "low", "preserve_thinking": False},
            "messages": [
                {"role": "system", "content": "Return only Python. No markdown."},
                {
                    "role": "user",
                    "content": "Write a Python function merge_sorted(a, b) that merges two sorted lists of ints.",
                },
            ],
        },
        {
            "id": "T_medium_code",
            "class": "T",
            "temperature": 1.0,
            "max_tokens": 8192,
            "timeout": 600,
            "kwargs": {"enable_thinking": True, "reasoning_effort": "medium", "preserve_thinking": False},
            "messages": [
                {"role": "system", "content": "You are a careful coding agent."},
                {
                    "role": "user",
                    "content": "Implement Dijkstra shortest path in Python. Return only the function.",
                },
            ],
        },
        {
            "id": "T_empty_budget",
            "class": "T",
            "temperature": 1.0,
            "max_tokens": 2048,
            "timeout": 300,
            "kwargs": {"enable_thinking": True, "reasoning_effort": "medium", "preserve_thinking": False},
            "messages": [
                {"role": "user", "content": "Explain isolation levels in InnoDB in Chinese, then give one DDL example."},
            ],
        },
        {
            "id": "A_tools",
            "class": "A",
            "temperature": 1.0,
            "max_tokens": 2048,
            "timeout": 300,
            "kwargs": {"enable_thinking": True, "reasoning_effort": "medium", "preserve_thinking": False},
            "tools": TOOLS,
            "messages": [
                {
                    "role": "system",
                    "content": "You may call tools. Do not invent rm, git_push, or ssh. Project root is CodexGame.",
                },
                {
                    "role": "user",
                    "content": "Read Agents.md and tell me the runtime tickMs. Use tools if needed.",
                },
            ],
        },
        {
            "id": "A_chat",
            "class": "A",
            "temperature": 1.0,
            "max_tokens": 1024,
            "timeout": 180,
            "kwargs": {"enable_thinking": True, "reasoning_effort": "medium", "preserve_thinking": False},
            "messages": [
                {"role": "user", "content": "用三句话说明为什么单卡 4090 不该同时跑两个 27B。"},
            ],
        },
        {
            "id": "L_28k_needles",
            "class": "L",
            "temperature": 1.0,
            "max_tokens": 256,
            "timeout": 600,
            "kwargs": {"enable_thinking": True, "reasoning_effort": "medium", "preserve_thinking": False},
            "messages": [{"role": "user", "content": long_ctx}],
        },
    ]


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_class: dict[str, list[float]] = {}
    empty = 0
    for item in results:
        tps = item.get("decode_tokens_per_s")
        if isinstance(tps, (int, float)):
            by_class.setdefault(item["class"], []).append(float(tps))
        if item.get("empty"):
            empty += 1

    def avg(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    return {
        "n": len(results),
        "empty": empty,
        "avg_decode_S": avg(by_class.get("S", [])),
        "avg_decode_T": avg(by_class.get("T", [])),
        "avg_decode_A": avg(by_class.get("A", [])),
        "avg_decode_L": avg(by_class.get("L", [])),
        "gpu": gpu(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:18443")
    parser.add_argument("--model", default="openclaw/Qwen3.8-27B-DFLASH2")
    parser.add_argument("--lane", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--skip-wait", action="store_true")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not args.skip_wait:
        wait_ready(args.base)
    idle_gpu = gpu()
    results = []
    for spec in cases():
        t0 = gpu()
        result = chat(
            args.base,
            args.model,
            spec["messages"],
            max_tokens=spec["max_tokens"],
            timeout=spec["timeout"],
            temperature=spec["temperature"],
            kwargs=spec.get("kwargs"),
            tools=spec.get("tools"),
        )
        result["id"] = spec["id"]
        result["class"] = spec["class"]
        result["gpu_before"] = t0
        if spec["id"] == "L_28k_needles":
            text = (result.get("content") or "") + (result.get("reasoning") or "")
            result["needles"] = {
                "tick": "200" in text,
                "protocol": "v1" in text,
                "replay": "data/replay" in text,
            }
        (out / f"{spec['id']}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        slim = {k: result[k] for k in result if k not in {"content", "reasoning"}}
        slim["content_preview"] = (result.get("content") or "")[:400]
        results.append({**slim, "content_len": len(result.get("content") or ""), "reason_len": len(result.get("reasoning") or "")})
        print(json.dumps({"id": spec["id"], "tps": result.get("decode_tokens_per_s"), "empty": result.get("empty"), "http": result.get("http")}, ensure_ascii=False), flush=True)
    summary = {
        "lane": args.lane,
        "base": args.base,
        "model": args.model,
        "idle_gpu": idle_gpu,
        "summary": summarize(results),
        "results": results,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
