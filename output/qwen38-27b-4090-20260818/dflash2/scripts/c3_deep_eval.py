#!/usr/bin/env python3
"""Deeper MTP knob eval: fixed-length fill, junk, tools, needles."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

NEEDLE_A = "FACT_A_RUNTIME_TICK_MS=200"
NEEDLE_B = "FACT_B_PROTOCOL_VERSION=v1"
NEEDLE_C = "FACT_C_REPLAY_DIR=data/replay"
FILL_OFF = (
    "Write a dense, commented C++ red-black tree with insert, erase, and find. "
    "Keep going with more methods and tests until the token budget is exhausted. "
    "Do not summarize. Do not stop early."
)
FILL_MED = (
    "Implement a production-quality Python async connection pool with retries, "
    "backpressure, and metrics. Keep expanding helpers and tests until the budget ends."
)
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
    }
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


def detect_junk(text: str) -> dict[str, Any]:
    if not text:
        return {"junk_repeat": False, "reason": None}
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) >= 6:
        for window in (1, 2, 4):
            if len(lines) < window * 4:
                continue
            gram = tuple(lines[:window])
            repeats = 1
            idx = window
            while idx + window <= len(lines) and tuple(lines[idx : idx + window]) == gram:
                repeats += 1
                idx += window
            if repeats >= 6:
                return {"junk_repeat": True, "reason": f"line_gram_{window}_x{repeats}"}
    words = text.split()
    if len(words) >= 64:
        for n in (8, 16, 32):
            gram = tuple(words[:n])
            if not any(gram):
                continue
            repeats = 1
            idx = n
            while idx + n <= len(words) and tuple(words[idx : idx + n]) == gram:
                repeats += 1
                idx += n
            if repeats >= 4:
                return {"junk_repeat": True, "reason": f"word_gram_{n}_x{repeats}"}
    if re.search(r"(.)\1{40,}", text):
        return {"junk_repeat": True, "reason": "char_run"}
    return {"junk_repeat": False, "reason": None}


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


def pad_prompt(target_tokens: int) -> str:
    unit = (
        "OpenClaw keeps simulation authority in apps/game-runtime. "
        "The client is presentation-only. tickMs is 200. protocol is v1. "
        "Replay lives under data/replay. "
    )
    return (unit * max(1, target_tokens // 16))[: target_tokens * 4]


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
    decode_tps = timings.get("predicted_per_second")
    if decode_tps is None and predicted_ms:
        decode_tps = completion / (predicted_ms / 1000) if predicted_ms else None
    if decode_tps is None and completion and elapsed:
        decode_tps = completion / elapsed
    draft_n = timings.get("draft_n") or 0
    draft_acc = timings.get("draft_n_accepted") or 0
    junk = detect_junk(str(content) + "\n" + str(reasoning))
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
        "prompt_tokens_per_s": timings.get("prompt_per_second"),
        "draft_n": draft_n,
        "draft_n_accepted": draft_acc,
        "accept_rate": (draft_acc / draft_n) if draft_n else None,
        "timings": timings,
        "tool_calls": msg.get("tool_calls") or [],
        "junk_repeat": junk["junk_repeat"],
        "junk_reason": junk["reason"],
        "error": body.get("error") or body.get("error_text"),
        "gpu_after": gpu(),
    }


OFF = {"enable_thinking": False, "reasoning_effort": "low", "preserve_thinking": False}
MED = {"enable_thinking": True, "reasoning_effort": "medium", "preserve_thinking": False}


def cases() -> list[dict[str, Any]]:
    long_ctx = (
        pad_prompt(28000)
        + f"\n{NEEDLE_A}\n{NEEDLE_B}\n{NEEDLE_C}\n"
        + 'Return JSON only: {"tick":...,"protocol":"...","replay":"..."}\n'
    )
    out: list[dict[str, Any]] = []
    for i in (1, 2, 3):
        out.append(
            {
                "id": f"F_off_1024_r{i}",
                "class": "F_off",
                "temperature": 0.7,
                "max_tokens": 1024,
                "timeout": 180,
                "kwargs": OFF,
                "messages": [{"role": "user", "content": FILL_OFF}],
            }
        )
    for i in (1, 2):
        out.append(
            {
                "id": f"F_med_1024_r{i}",
                "class": "F_med",
                "temperature": 1.0,
                "max_tokens": 1024,
                "timeout": 240,
                "kwargs": MED,
                "messages": [{"role": "user", "content": FILL_MED}],
            }
        )
    out.extend(
        [
            {
                "id": "S_short_code",
                "class": "S",
                "temperature": 0.7,
                "max_tokens": 512,
                "timeout": 120,
                "kwargs": OFF,
                "messages": [
                    {"role": "system", "content": "Return only Python. No markdown."},
                    {
                        "role": "user",
                        "content": "Write merge_sorted(a, b) merging two sorted int lists.",
                    },
                ],
            },
            {
                "id": "T_empty_2048",
                "class": "T",
                "temperature": 1.0,
                "max_tokens": 2048,
                "timeout": 300,
                "kwargs": MED,
                "messages": [
                    {
                        "role": "user",
                        "content": "Explain InnoDB isolation levels in Chinese, then one DDL example.",
                    }
                ],
            },
            {
                "id": "A_tools",
                "class": "A",
                "temperature": 1.0,
                "max_tokens": 2048,
                "timeout": 240,
                "kwargs": MED,
                "tools": TOOLS,
                "messages": [
                    {
                        "role": "system",
                        "content": "You may call tools. Do not invent rm or ssh. Project is CodexGame.",
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
                "kwargs": MED,
                "messages": [
                    {"role": "user", "content": "用三句话说明为什么单卡 4090 不该同时跑两个 27B。"}
                ],
            },
            {
                "id": "L_28k_needles",
                "class": "L",
                "temperature": 1.0,
                "max_tokens": 256,
                "timeout": 600,
                "kwargs": MED,
                "messages": [{"role": "user", "content": long_ctx}],
            },
        ]
    )
    return out


def median(values: list[float]) -> float | None:
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    mid = n // 2
    if n % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by: dict[str, list[float]] = {}
    acc: dict[str, list[float]] = {}
    empty = junk = 0
    for item in results:
        tps = item.get("decode_tokens_per_s")
        if isinstance(tps, (int, float)):
            by.setdefault(item["class"], []).append(float(tps))
        ar = item.get("accept_rate")
        if isinstance(ar, (int, float)):
            acc.setdefault(item["class"], []).append(float(ar))
        if item.get("empty"):
            empty += 1
        if item.get("junk_repeat"):
            junk += 1

    def avg(xs: list[float]) -> float | None:
        return sum(xs) / len(xs) if xs else None

    return {
        "n": len(results),
        "empty": empty,
        "junk": junk,
        "fill_off_median_tps": median(by.get("F_off", [])),
        "fill_off_avg_tps": avg(by.get("F_off", [])),
        "fill_med_median_tps": median(by.get("F_med", [])),
        "fill_med_avg_tps": avg(by.get("F_med", [])),
        "short_code_tps": avg(by.get("S", [])),
        "tools_chat_avg_tps": avg(by.get("A", [])),
        "long_tps": avg(by.get("L", [])),
        "fill_off_accept": avg(acc.get("F_off", [])),
        "fill_med_accept": avg(acc.get("F_med", [])),
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
        deadline = time.monotonic() + 240
        last = ""
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"{args.base}/v1/models", timeout=5) as res:
                    if json.loads(res.read().decode()).get("data"):
                        break
            except Exception as exc:  # noqa: BLE001
                last = repr(exc)
            time.sleep(2)
        else:
            raise RuntimeError(f"not ready: {last}")
    idle = gpu()
    results = []
    for spec in cases():
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
        if spec["id"] == "L_28k_needles":
            text = (result.get("content") or "") + (result.get("reasoning") or "")
            result["needles"] = {
                "tick": "200" in text,
                "protocol": "v1" in text,
                "replay": "data/replay" in text,
            }
        slim = {k: result[k] for k in result if k not in {"content", "reasoning"}}
        slim["content_preview"] = (result.get("content") or "")[:300]
        slim["content_len"] = len(result.get("content") or "")
        slim["reason_len"] = len(result.get("reasoning") or "")
        (out / f"{spec['id']}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        results.append(slim)
        print(
            json.dumps(
                {
                    "id": spec["id"],
                    "tps": result.get("decode_tokens_per_s"),
                    "ar": result.get("accept_rate"),
                    "empty": result.get("empty"),
                    "junk": result.get("junk_repeat"),
                    "tok": result.get("completion_tokens"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    summary = {
        "lane": args.lane,
        "base": args.base,
        "model": args.model,
        "idle_gpu": idle,
        "summary": summarize(results),
        "results": results,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
