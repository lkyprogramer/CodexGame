#!/usr/bin/env python3
"""Two prefix patterns against production NInfer.

A: growing history (Pi/OpenClaw happy path: append assistant + tool + user).
B: rewrite the last user message in place (reminder stuffed into newest user).
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

URL = os.environ.get("SERVER_URL", "http://127.0.0.1:18343/v1").rstrip("/")
MODEL = os.environ.get("MODEL_ID", "openclaw/Qwen3.8-27B-WORK")
OUT = Path(os.environ.get("PROBE_OUT", "prefix_probe.json"))


def chat(messages: list, tag: str) -> dict:
    body = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 64,
        "temperature": 0.2,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {
            "enable_thinking": True,
            "reasoning_effort": "medium",
        },
    }
    req = urllib.request.Request(
        URL + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.monotonic()
    first = None
    text: list[str] = []
    usage: dict = {}
    err = None
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            for raw in r:
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
                timings = obj.get("timings") or {}
                if timings:
                    usage.setdefault("_timings", timings)
                for ch in obj.get("choices") or []:
                    d = ch.get("delta") or {}
                    s = (d.get("content") or "") + (d.get("reasoning_content") or "")
                    if s:
                        if first is None:
                            first = time.monotonic()
                        text.append(s)
    except Exception as e:
        err = repr(e)
    end = time.monotonic()
    timings = usage.get("_timings") or {}
    pt = usage.get("prompt_tokens") or timings.get("prompt_n")
    details = usage.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens") if isinstance(details, dict) else None
    if cached is None:
        cached = timings.get("cache_n")
    row = {
        "tag": tag,
        "ok": err is None,
        "error": err,
        "prompt_tokens": pt,
        "cached_tokens": cached,
        "ttft_s": round(first - t0, 3) if first else None,
        "wall_s": round(end - t0, 3),
        "text": "".join(text)[:500],
        "hit_ratio": round(cached / pt, 3) if cached and pt else 0.0,
    }
    print(
        f"[probe] {tag} pt={pt} cached={cached} hit={row['hit_ratio']} "
        f"ttft={row['ttft_s']} wall={row['wall_s']}",
        flush=True,
    )
    return row


def main() -> None:
    sys = (
        "You are a Java coding agent. Available tools: read, bash, edit. "
        "Keep answers short. Marker=PREFIX-NEEDLE-7Q4."
    )
    tools_blob = (
        "Tools schema (stable): read(path), bash(command), edit(path, old, new). "
        "Do not actually emit tools in this probe; just answer."
    )
    task = "Confirm you see Marker and name the three tools."
    follow = "Repeat the Marker exactly, then say READY."

    rows = []
    m1 = [
        {"role": "system", "content": sys},
        {"role": "user", "content": tools_blob + "\n\n" + task},
    ]
    r1 = chat(m1, "A-cold")
    rows.append(r1)
    m2 = m1 + [
        {"role": "assistant", "content": r1.get("text") or "ok"},
        {"role": "user", "content": follow},
    ]
    rows.append(chat(m2, "A-append"))

    m1b = [
        {"role": "system", "content": sys},
        {"role": "user", "content": tools_blob + "\n\n" + task},
    ]
    r1b = chat(m1b, "B-cold")
    rows.append(r1b)
    rewritten = (
        "[SYSTEM REMINDER bound to this user turn]: be concise, no markdown.\n\n"
        + tools_blob
        + "\n\n"
        + task
    )
    m2b = [
        {"role": "system", "content": sys},
        {"role": "user", "content": rewritten},
        {"role": "assistant", "content": r1b.get("text") or "ok"},
        {"role": "user", "content": follow},
    ]
    rows.append(chat(m2b, "B-rewrite-last-user-root"))

    m2c = m1b + [
        {"role": "assistant", "content": r1b.get("text") or "ok"},
        {
            "role": "user",
            "content": "[SYSTEM REMINDER]: be concise.\n" + follow,
        },
    ]
    rows.append(chat(m2c, "B-rewrite-newest-user-only"))

    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
