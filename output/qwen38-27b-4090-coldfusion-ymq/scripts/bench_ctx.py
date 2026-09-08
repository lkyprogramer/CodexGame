#!/usr/bin/env python3
"""Needle + decode timings against llama-server. Prompt token targeting ~10 tok/unit."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

UNIT = "The quick brown fox jumps over the lazy dog. "
TOK_PER_UNIT = 10.02
NEEDLE_A = "NEEDLE_TICK=1847"
NEEDLE_B = "NEEDLE_PROTOCOL=delta-net-ok"
NEEDLE_C = "NEEDLE_REPLAY=seed-42"


def gpu() -> str:
    try:
        return subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free", "--format=csv,noheader"],
            text=True,
        ).strip()
    except Exception:
        return "?"


def pad(target: int) -> str:
    n = max(1, int(target / TOK_PER_UNIT) - 16)
    return UNIT * n


def chat(base: str, model: str, messages: list, max_tokens: int, timeout: int, kwargs: dict, min_tokens: int = 0) -> dict:
    body_obj = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "chat_template_kwargs": kwargs,
    }
    if min_tokens:
        body_obj["min_tokens"] = min_tokens
    body = json.dumps(body_obj).encode()
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
    reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
    tc = msg.get("tool_calls") or []
    pred_n, pred_ms = timings.get("predicted_n"), timings.get("predicted_ms")
    p_n, p_ms = timings.get("prompt_n"), timings.get("prompt_ms")
    decode = round(1000.0 * float(pred_n) / float(pred_ms), 2) if pred_n and pred_ms else None
    prefill = round(1000.0 * float(p_n) / float(p_ms), 2) if p_n and p_ms else None
    return {
        "wall_s": round(wall, 2),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "decode_tok_s": decode,
        "prefill_tok_s": prefill,
        "draft_n": timings.get("draft_n"),
        "draft_n_accepted": timings.get("draft_n_accepted"),
        "finish": choice.get("finish_reason"),
        "empty": not bool(content.strip() or tc),
        "content_len": len(content),
        "reason_len": len(reasoning),
        "preview": (content or json.dumps(tc, ensure_ascii=False))[:180],
        "needles": {
            "tick": "1847" in content,
            "protocol": "delta-net-ok" in content,
            "replay": "seed-42" in content,
        },
        "n_tools": len(tc),
        "gpu": gpu(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:18443")
    ap.add_argument("--model", default="qwen38-coldfusion-ymq")
    ap.add_argument("--lane", required=True)
    ap.add_argument("--n-ctx", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    idle = gpu()
    rows = []
    think_off = {"enable_thinking": False}
    think_med = {"enable_thinking": True, "reasoning_effort": "medium", "preserve_thinking": False}

    needle_sizes = [28000, 64000]
    if args.n_ctx >= 180000:
        needle_sizes += [128000]
    if args.n_ctx >= 250000:
        needle_sizes += [200000, 240000]

    for n in needle_sizes:
        if n + 512 >= args.n_ctx:
            continue
        prompt = (
            pad(n)
            + f"\n{NEEDLE_A}\n{NEEDLE_B}\n{NEEDLE_C}\n"
            + 'Return JSON only: {"tick":...,"protocol":"...","replay":"..."}\n'
        )
        rec = {"id": f"L_{n}_needles", "class": "needle"}
        try:
            rec.update(chat(args.base, args.model, [{"role": "user", "content": prompt}], 256, 1800, think_med))
        except Exception as e:
            rec["error"] = str(e)
        rows.append(rec)
        print(json.dumps({"id": rec["id"], "err": rec.get("error"), "needles": rec.get("needles"), "pt": rec.get("prompt_tokens")}, ensure_ascii=False), flush=True)

    for n in (16000, int(args.n_ctx * 0.8)):
        if n + 300 >= args.n_ctx:
            continue
        prompt = pad(n) + "\nContinue writing numbers in English words without stopping."
        rec = {"id": f"D_{n}", "class": "decode"}
        try:
            rec.update(chat(args.base, args.model, [{"role": "user", "content": prompt}], 256, 1800, think_off, min_tokens=128))
        except Exception as e:
            rec["error"] = str(e)
        rows.append(rec)
        print(json.dumps({"id": rec["id"], "err": rec.get("error"), "decode": rec.get("decode_tok_s"), "prefill": rec.get("prefill_tok_s"), "pt": rec.get("prompt_tokens"), "ct": rec.get("completion_tokens")}, ensure_ascii=False), flush=True)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            },
        }
    ]
    rec = {"id": "A_tools", "class": "tools"}
    try:
        body = json.dumps(
            {
                "model": args.model,
                "messages": [{"role": "user", "content": "Call read_file on Agents.md and stop."}],
                "tools": tools,
                "tool_choice": "auto",
                "max_tokens": 512,
                "chat_template_kwargs": think_off,
            }
        ).encode()
        req = urllib.request.Request(
            f"{args.base}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode())
        wall = time.time() - t0
        msg = ((data.get("choices") or [{}])[0].get("message") or {})
        tc = msg.get("tool_calls") or []
        rec.update(
            {
                "wall_s": round(wall, 2),
                "finish": (data.get("choices") or [{}])[0].get("finish_reason"),
                "n_tools": len(tc),
                "tool_preview": json.dumps(tc, ensure_ascii=False)[:400],
                "empty": not bool(tc or (msg.get("content") or "").strip()),
                "gpu": gpu(),
            }
        )
    except Exception as e:
        rec["error"] = str(e)
    rows.append(rec)
    print(json.dumps({"id": "A_tools", "err": rec.get("error"), "n_tools": rec.get("n_tools"), "finish": rec.get("finish")}, ensure_ascii=False), flush=True)

    think = {"id": "T_medium", "class": "think"}
    try:
        think.update(
            chat(
                args.base,
                args.model,
                [{"role": "user", "content": "In one sentence: why is 17 prime? Show brief reasoning."}],
                1024,
                180,
                think_med,
            )
        )
    except Exception as e:
        think["error"] = str(e)
    rows.append(think)

    summary = {"lane": args.lane, "n_ctx": args.n_ctx, "idle_gpu": idle, "gpu_end": gpu(), "rows": rows}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
