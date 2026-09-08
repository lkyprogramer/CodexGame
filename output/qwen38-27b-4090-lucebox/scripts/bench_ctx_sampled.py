#!/usr/bin/env python3
"""200K-window needles + short spec probes. Sampling (T=1.0); thinking off."""
from __future__ import annotations

import json
import subprocess
import sys
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
            ["nvidia-smi", "--query-gpu=memory.used,memory.free,utilization.gpu", "--format=csv,noheader"],
            text=True,
            timeout=5,
        ).strip()
    except Exception:
        return "?"


def pad(target: int) -> str:
    n = max(1, int(target / TOK_PER_UNIT) - 16)
    return UNIT * n


def chat(base: str, model: str, messages: list, max_tokens: int, timeout: int, tools=None) -> dict:
    body_obj = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if tools:
        body_obj["tools"] = tools
        body_obj["tool_choice"] = "auto"
    data = json.dumps(body_obj).encode()
    req = urllib.request.Request(
        f"{base}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
    wall = time.time() - t0
    usage = payload.get("usage") or {}
    timings = payload.get("timings") or {}
    choice = (payload.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
    tc = msg.get("tool_calls") or []
    text = content + reasoning
    return {
        "wall_s": round(wall, 2),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "finish": choice.get("finish_reason"),
        "empty": not bool(content.strip() or tc),
        "preview": (content or json.dumps(tc, ensure_ascii=False))[:200].replace("\n", " / "),
        "timings": timings,
        "n_tools": len(tc),
        "needles": {
            "tick": "1847" in text,
            "protocol": "delta-net-ok" in text,
            "replay": "seed-42" in text,
        },
        "gpu": gpu(),
    }


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:18343"
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen38-lucebox"
    n_ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 200000
    out = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(".")
    out.mkdir(parents=True, exist_ok=True)
    rows = []

    short = [
        "Write a Python merge_sorted(a, b) that merges two sorted lists. Code only.",
        "Write Dijkstra in Python using heapq. Code only.",
    ]
    for i, p in enumerate(short):
        rec = {"id": f"S_short_{i}", "class": "short"}
        try:
            rec.update(chat(base, model, [{"role": "user", "content": p}], 256, 180))
        except Exception as e:
            rec["error"] = str(e)
        rows.append(rec)
        print(json.dumps({"id": rec["id"], "err": rec.get("error"), "pt": rec.get("prompt_tokens"), "ct": rec.get("completion_tokens"), "wall": rec.get("wall_s"), "empty": rec.get("empty")}, ensure_ascii=False), flush=True)

    needles = [28000, 64000, 128000, 180000]
    for n in needles:
        if n + 2048 >= n_ctx:
            continue
        prompt = (
            pad(n)
            + f"\n{NEEDLE_A}\n{NEEDLE_B}\n{NEEDLE_C}\n"
            + 'Return JSON only: {"tick":...,"protocol":"...","replay":"..."}\n'
        )
        rec = {"id": f"L_{n}_needles", "class": "needle", "target": n}
        try:
            rec.update(chat(base, model, [{"role": "user", "content": prompt}], 256, 1800))
        except Exception as e:
            rec["error"] = str(e)
            rec["gpu"] = gpu()
        rows.append(rec)
        print(
            json.dumps(
                {
                    "id": rec["id"],
                    "err": rec.get("error"),
                    "needles": rec.get("needles"),
                    "pt": rec.get("prompt_tokens"),
                    "wall": rec.get("wall_s"),
                    "gpu": rec.get("gpu"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

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
        rec.update(
            chat(
                base,
                model,
                [{"role": "user", "content": "Call read_file on Agents.md and stop."}],
                512,
                180,
                tools=tools,
            )
        )
    except Exception as e:
        rec["error"] = str(e)
    rows.append(rec)
    print(json.dumps({"id": "A_tools", "err": rec.get("error"), "n_tools": rec.get("n_tools"), "finish": rec.get("finish")}, ensure_ascii=False), flush=True)

    summary = {"n_ctx": n_ctx, "gpu_end": gpu(), "rows": rows}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    json.dump(summary, sys.stdout, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
