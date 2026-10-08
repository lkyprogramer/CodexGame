#!/usr/bin/env python3
"""Print live 18343/1082 usage objects for pi-ai field matching. Do not print secrets."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

PAD = "Java reconnect invariant token pad. " * 400
MSGS = [
    {"role": "system", "content": "You are a coding agent. " + PAD},
    {"role": "user", "content": "Reply with the single word PONG."},
]
MODEL = "openclaw/Qwen3.8-27B-WORK"


def post(url: str, body: dict, headers: dict | None = None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=180)


def pi_fields(usage: dict) -> dict:
    details = usage.get("prompt_tokens_details") or {}
    cache_read = (
        details.get("cached_tokens")
        if details.get("cached_tokens") is not None
        else usage.get("prompt_cache_hit_tokens")
        if usage.get("prompt_cache_hit_tokens") is not None
        else usage.get("cached_tokens")
        if usage.get("cached_tokens") is not None
        else 0
    )
    cache_write = details.get("cache_write_tokens") or 0
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "pi_cacheRead": cache_read,
        "pi_cacheWrite": cache_write,
        "has_prompt_tokens_details.cached_tokens": isinstance(details, dict)
        and "cached_tokens" in details,
    }


def collect_stream_usages(url: str, headers: dict | None = None) -> list[dict]:
    body = {
        "model": MODEL,
        "messages": MSGS,
        "max_tokens": 8,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    usages: list[dict] = []
    naive: list[str] = []
    with post(url, body, headers) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if '"usage"' in line:
                m = re.search(r'"usage":\{[^}]*\}', line)
                naive.append(m.group(0) if m else "NO_FLAT_MATCH")
            if not line.startswith("data:"):
                continue
            dat = line[5:].strip()
            if dat in {"", "[DONE]"}:
                continue
            try:
                obj = json.loads(dat)
            except json.JSONDecodeError:
                continue
            if obj.get("usage") is not None:
                usages.append(obj["usage"])
    return usages, naive


def main() -> None:
    ns_body = {
        "model": MODEL,
        "messages": MSGS,
        "max_tokens": 8,
        "temperature": 0,
        "stream": False,
    }
    with post("http://127.0.0.1:18343/v1/chat/completions", ns_body) as r:
        u1 = json.loads(r.read().decode())["usage"]
    with post("http://127.0.0.1:18343/v1/chat/completions", ns_body) as r:
        u2 = json.loads(r.read().decode())["usage"]
    print("NONSTREAM_COLD", json.dumps(u1, ensure_ascii=False))
    print("NONSTREAM_EXACT", json.dumps(u2, ensure_ascii=False))
    print("PI_NONSTREAM_EXACT", json.dumps(pi_fields(u2), ensure_ascii=False))

    usages, naive = collect_stream_usages("http://127.0.0.1:18343/v1/chat/completions")
    print("STREAM_USAGE_N", len(usages))
    if usages:
        print("STREAM_LAST", json.dumps(usages[-1], ensure_ascii=False))
        print("PI_STREAM_LAST", json.dumps(pi_fields(usages[-1]), ensure_ascii=False))
    print("NAIVE_GREP_LAST", naive[-1] if naive else None)

    conf = open("/tmp/openclaw-28343.conf").read()
    auth = re.search(r'"(Bearer [^"]+)"', conf).group(1)
    usages, _ = collect_stream_usages(
        "http://47.106.205.246:1082/v1/chat/completions",
        {"Authorization": auth},
    )
    print("PUBLIC_STREAM_N", len(usages))
    if usages:
        print("PUBLIC_LAST", json.dumps(usages[-1], ensure_ascii=False))
        print("PI_PUBLIC_LAST", json.dumps(pi_fields(usages[-1]), ensure_ascii=False))


if __name__ == "__main__":
    main()
