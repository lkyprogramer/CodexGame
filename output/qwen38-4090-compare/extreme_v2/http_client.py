"""Real Chat Completions + /metrics client used by extreme_v2 tests."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


def metrics_snapshot(url: str, timeout: float = 8.0) -> dict[str, float]:
    keys = (
        "llamacpp:prompt_tokens_total",
        "ninfer:prefix_cache_hit_tokens_total",
        "ninfer:requests_total",
        "ninfer:continuation_stable_prefix_restores_total",
    )
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = r.read().decode("utf-8", "replace")
    out: dict[str, float] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] in keys:
            out[parts[0]] = float(parts[1])
    return out


def metrics_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    if after.get("ninfer:requests_total", 0) < before.get("ninfer:requests_total", 0):
        raise RuntimeError("ninfer:requests_total went backwards (engine restart)")
    return {k: after.get(k, 0.0) - before.get(k, 0.0) for k in before.keys() | after.keys()}


def chat_completion(
    base: str,
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int = 64,
    stream: bool = True,
    include_usage: bool = True,
    reasoning_effort: str = "medium",
    timeout: float = 180.0,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": stream,
        "reasoning_effort": reasoning_effort,
        "enable_thinking": reasoning_effort not in {"none", "off"},
    }
    if stream and include_usage:
        body["stream_options"] = {"include_usage": True}
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.monotonic()
    first = None
    text_parts: list[str] = []
    usage: dict[str, Any] = {}
    timings: dict[str, Any] = {}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if not stream:
                obj = json.loads(resp.read().decode())
                usage = obj.get("usage") or {}
                timings = obj.get("timings") or {}
                msg = ((obj.get("choices") or [{}])[0].get("message") or {})
                text_parts.append(str(msg.get("content") or ""))
                wall = time.monotonic() - t0
                return _pack(usage, timings, "".join(text_parts), None, wall, True, None)
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                dat = line[5:].strip()
                if dat == "[DONE]":
                    break
                try:
                    obj = json.loads(dat)
                except json.JSONDecodeError:
                    continue
                if obj.get("usage"):
                    usage = obj["usage"]
                if obj.get("timings"):
                    timings = obj["timings"]
                for ch in obj.get("choices") or []:
                    d = ch.get("delta") or {}
                    s = str(d.get("content") or "") + str(d.get("reasoning_content") or "")
                    if s:
                        if first is None:
                            first = time.monotonic()
                        text_parts.append(s)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:800]
        return _pack({}, {}, "", None, time.monotonic() - t0, False, f"HTTP {e.code}: {detail}")
    except Exception as e:
        return _pack({}, {}, "", None, time.monotonic() - t0, False, repr(e))
    wall = time.monotonic() - t0
    ttft = (first - t0) if first else None
    return _pack(usage, timings, "".join(text_parts), ttft, wall, True, None)


def _pack(usage, timings, text, ttft, wall, ok, err) -> dict[str, Any]:
    details = usage.get("prompt_tokens_details") if isinstance(usage, dict) else None
    cached = None
    if isinstance(details, dict):
        cached = details.get("cached_tokens")
    if cached is None and isinstance(timings, dict):
        cached = timings.get("cache_n")
    prompt_n = None
    if isinstance(usage, dict):
        prompt_n = usage.get("prompt_tokens")
    if prompt_n is None and isinstance(timings, dict):
        prompt_n = timings.get("prompt_n")
    pred_n = None
    if isinstance(usage, dict):
        pred_n = usage.get("completion_tokens")
    if pred_n is None and isinstance(timings, dict):
        pred_n = timings.get("predicted_n")
    decode_tps = None
    if isinstance(timings, dict) and timings.get("predicted_per_second"):
        decode_tps = float(timings["predicted_per_second"])
    elif pred_n and ttft is not None and wall > ttft:
        decode_tps = float(pred_n) / (wall - ttft)
    return {
        "ok": ok,
        "error": err,
        "prompt_tokens": prompt_n,
        "completion_tokens": pred_n,
        "cached_tokens": cached,
        "ttft_s": round(ttft, 4) if ttft is not None else None,
        "wall_s": round(wall, 4),
        "decode_tps": decode_tps,
        "usage": usage,
        "timings": timings,
        "text": text[:400],
    }
