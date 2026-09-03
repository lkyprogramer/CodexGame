#!/usr/bin/env python3
"""Decode tok/s at ~16k/32k/60k filled context. Generate >=128 tokens."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

UNIT = "The quick brown fox jumps over the lazy dog. "
# Empirically ~10.0 tokens/unit on this tokenizer (prior run: 1777 units -> 17788 tok).
TOK_PER_UNIT = 10.02


def gpu() -> str:
    try:
        return subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free", "--format=csv,noheader"],
            text=True,
        ).strip()
    except Exception:
        return "?"


def filler(target_tokens: int) -> str:
    n = max(1, int(target_tokens / TOK_PER_UNIT) - 8)
    return UNIT * n + "\nContinue the sentence with many words. Count upward in English words without stopping."


def chat(base: str, model: str, prompt: str, max_tokens: int, timeout: int) -> dict:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "min_tokens": min(128, max_tokens),
            "temperature": 0.0,
            "chat_template_kwargs": {"enable_thinking": False},
        }
    ).encode()
    req = urllib.request.Request(
        f"{base}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    wall = time.time() - t0
    usage = data.get("usage") or {}
    timings = data.get("timings") or {}
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    comp = int(usage.get("completion_tokens") or 0)
    prompt_tok = int(usage.get("prompt_tokens") or 0)
    predicted_n = timings.get("predicted_n")
    predicted_ms = timings.get("predicted_ms")
    prompt_n = timings.get("prompt_n")
    prompt_ms = timings.get("prompt_ms")
    decode_from_timings = None
    prefill_from_timings = None
    if predicted_n and predicted_ms:
        decode_from_timings = round(1000.0 * float(predicted_n) / float(predicted_ms), 2)
    if prompt_n and prompt_ms:
        prefill_from_timings = round(1000.0 * float(prompt_n) / float(prompt_ms), 2)
    return {
        "wall_s": round(wall, 2),
        "prompt_tokens": prompt_tok,
        "completion_tokens": comp,
        "decode_tok_s_wall": round((comp / wall) if wall > 0 else 0.0, 2),
        "decode_tok_s": decode_from_timings,
        "prefill_tok_s": prefill_from_timings,
        "timings": timings,
        "finish": choice.get("finish_reason"),
        "empty": not bool(content.strip()),
        "preview": content[:160],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:18443")
    ap.add_argument("--model", default="qwen38-flash-next")
    ap.add_argument("--lane", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    idle = gpu()
    rows = []
    # Stay under n_ctx=65536. 60k fill + 256 gen.
    for n in (16000, 32000, 60000):
        rec = {"id": f"fill_{n}", "gpu_idle": idle, "target_prompt_tokens": n}
        try:
            rec.update(chat(args.base, args.model, filler(n), 256, 1800))
        except Exception as e:
            rec["error"] = str(e)
        rec["gpu_after"] = gpu()
        rows.append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
    (out / "summary.json").write_text(
        json.dumps({"lane": args.lane, "idle_gpu": idle, "rows": rows}, indent=2)
    )


if __name__ == "__main__":
    main()
