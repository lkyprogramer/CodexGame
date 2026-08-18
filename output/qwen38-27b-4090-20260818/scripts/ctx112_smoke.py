#!/usr/bin/env python3
"""Smoke + ~90K cross-fact check after raising ctx to 112K."""
from __future__ import annotations

import json
import time
import urllib.request

BASE = "http://127.0.0.1:18343"
MODEL = "openclaw/Qwen3.8-27B-WORK"


def post(payload, timeout=1800):
    req = urllib.request.Request(
        f"{BASE}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode())


def chat(prompt, max_tokens=256):
    t0 = time.perf_counter()
    body = post({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "top_p": 0.95,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {
            "enable_thinking": True,
            "reasoning_effort": "medium",
            "preserve_thinking": False,
        },
        "stream": False,
    })
    elapsed = time.perf_counter() - t0
    msg = (body.get("choices") or [{}])[0].get("message") or {}
    usage = body.get("usage") or {}
    return {
        "content": msg.get("content") or "",
        "empty": not (msg.get("content") or "").strip(),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion": usage.get("completion_tokens"),
        "elapsed": elapsed,
        "finish": (body.get("choices") or [{}])[0].get("finish_reason"),
    }


def pack(target_tokens: int) -> str:
    block = (
        "CodexGame runtime remains authoritative. protocol owns schemas. "
        "simulation is deterministic for the same seed. client is presentation only. "
    )
    target_chars = target_tokens * 6
    body = (block * ((target_chars // len(block)) + 3))[:target_chars]
    a, b, c = len(body) // 4, len(body) // 2, (3 * len(body)) // 4
    return (
        body[:a] + "\nNEEDLE_TICK=200\n"
        + body[a:b] + "\nNEEDLE_PROTOCOL=v1\n"
        + body[b:c] + "\nNEEDLE_REPLAY=data/replay\n"
        + body[c:]
    )


def main() -> int:
    with urllib.request.urlopen(f"{BASE}/v1/models", timeout=10) as res:
        models = json.loads(res.read().decode())
    meta = (models.get("data") or [{}])[0].get("meta") or {}
    print("n_ctx", meta.get("n_ctx"))

    short = chat("Reply with OK only.", 64)
    print("short", short["content"].strip()[:40], "empty", short["empty"])

    packed = pack(90000)
    rec = chat(
        packed
        + "\n\nReturn JSON only with fields tick, protocol, replay from NEEDLE_* values.",
        512,
    )
    print(
        "long prompt_tokens", rec["prompt_tokens"],
        "elapsed", round(rec["elapsed"], 1),
        "empty", rec["empty"],
        "content", rec["content"][:200],
    )
    text = rec["content"]
    ok = "200" in text and "v1" in text and "replay" in text.lower() and not rec["empty"]
    print("CROSS", "PASS" if ok else "FAIL")
    return 0 if ok and not short["empty"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
