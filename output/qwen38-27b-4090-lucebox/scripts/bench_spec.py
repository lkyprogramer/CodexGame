#!/usr/bin/env python3
"""Short-code completions; report HTTP timings. Server log is the spec/AR source of truth."""
from __future__ import annotations

import json
import sys
import time
import urllib.request

PROMPTS = [
    "Write a Python merge_sorted(a, b) that merges two sorted lists. Code only.",
    "Write a Python LRU cache class with get and put. Code only.",
    "Write Dijkstra in Python using heapq. Code only.",
]


def chat(base: str, model: str, prompt: str, temperature: float, max_tokens: int) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if temperature <= 0:
        body["top_p"] = 1.0
        body["top_k"] = 0
    else:
        body["top_p"] = 0.95
        body["top_k"] = 20
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.loads(resp.read().decode())
    wall = time.time() - t0
    ch = (payload.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    usage = payload.get("usage") or {}
    timings = payload.get("timings") or {}
    content = msg.get("content") or ""
    return {
        "wall_s": round(wall, 2),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "finish": ch.get("finish_reason"),
        "empty": not bool(content.strip()),
        "preview": content[:160].replace("\n", " / "),
        "timings": timings,
        "predicted_per_second": timings.get("predicted_per_second"),
    }


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:18343"
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen38-lucebox"
    temp = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    max_tokens = int(sys.argv[4]) if len(sys.argv) > 4 else 256
    rows = []
    for p in PROMPTS:
        try:
            rec = {"prompt": p[:60], **chat(base, model, p, temp, max_tokens)}
        except Exception as e:
            rec = {"prompt": p[:60], "error": str(e)}
        rows.append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
    json.dump({"temperature": temp, "max_tokens": max_tokens, "rows": rows}, sys.stdout)
    print()


if __name__ == "__main__":
    main()
