#!/usr/bin/env python3
"""Stage1 HTTP ladder. Env: SERVER_URL MODEL_ID THINKING (off|medium)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = Path(os.environ.get("RESULTS_ROOT", str(ROOT / "results"))) / os.environ.get("BACKEND", "work")
CACHE = ROOT / ".state" / "prompts"
RES.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

URL = os.environ.get("SERVER_URL", "http://127.0.0.1:18343/v1").rstrip("/")
MODEL = os.environ.get("MODEL_ID", "openclaw/Qwen3.8-27B-WORK")
THINKING = os.environ.get("THINKING", "off")


def post(path: str, body: dict, timeout: int = 1800):
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("API_KEY") or os.environ.get("VLLM_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(
        URL + path,
        data=data,
        headers=headers,
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=timeout)


def make_lines(n: int, needle: str) -> str:
    lines = []
    for i in range(n):
        if i == int(n * 0.86):
            lines.append(f"// RELEASE_NEEDLE={needle} do-not-alter marker for long-context retrieval.\n")
        lines.append(
            f"// repo-line {i:07d} module=exam-runtime state=ACTIVE tenant=t{i%97:02d} "
            f"invariant=idempotent-reconnect; public final long tickMs={(i % 7 + 1) * 50};\n"
        )
    return "".join(lines)


def prompt_for(target: int) -> tuple[str, dict]:
    p = CACHE / f"{target}.txt"
    meta = CACHE / f"{target}.json"
    if p.exists() and meta.exists():
        return p.read_text(), json.loads(meta.read_text())
    needle = f"JAVA-AGENT-{target}-N7Q4"
    # Empirically ~40 tokens/line on WORK. Cap so 185k stays inside 200k ctx.
    n = max(80, min(target // 40, 8000))
    text = make_lines(n, needle)
    p.write_text(text)
    meta.write_text(json.dumps({"target": target, "chars": len(text), "lines": n, "needle": needle}))
    return text, {"target": target, "chars": len(text), "lines": n, "needle": needle}


def stream_chat(messages: list, max_tokens: int, tag: str) -> dict:
    body = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": True,
    }
    backend = os.environ.get("BACKEND", "")
    # NInfer rejects chat_template_kwargs.enable_thinking (HTTP 400).
    if backend.startswith("ninfer"):
        body["reasoning_effort"] = THINKING if THINKING != "off" else "none"
    elif THINKING != "off":
        body["reasoning_effort"] = THINKING
        body["chat_template_kwargs"] = {
            "enable_thinking": True,
            "reasoning_effort": THINKING,
        }
    elif backend == "work":
        body["chat_template_kwargs"] = {
            "enable_thinking": False,
            "reasoning_effort": "low",
        }
    t0 = time.monotonic()
    first = None
    text: list[str] = []
    usage: dict = {}
    err = None
    try:
        with post("/chat/completions", body) as r:
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
                timings = obj.get("timings") or (usage.get("timings") if isinstance(usage, dict) else {}) or {}
                if timings:
                    usage.setdefault("_timings", timings)
                for ch in obj.get("choices") or []:
                    d = ch.get("delta") or {}
                    s = (d.get("content") or "") + (d.get("reasoning") or "") + (d.get("reasoning_content") or "")
                    if s:
                        if first is None:
                            first = time.monotonic()
                        text.append(s)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        err = f"HTTP {e.code}: {detail}"
    except Exception as e:
        err = repr(e)
    end = time.monotonic()
    out = "".join(text)
    timings = usage.get("_timings") or {}
    pt = usage.get("prompt_tokens") or usage.get("input_tokens") or timings.get("prompt_n")
    ct = usage.get("completion_tokens") or usage.get("output_tokens") or timings.get("predicted_n")
    if not ct:
        ct = max(1, len(out) // 4)
    ttft = (first - t0) if first else None
    dec = (ct / (end - first)) if first and end > first else 0.0
    prefill = None
    if timings.get("prompt_n") and timings.get("prompt_ms"):
        prefill = round(1000.0 * float(timings["prompt_n"]) / float(timings["prompt_ms"]), 2)
        if timings.get("predicted_per_second"):
            dec = float(timings["predicted_per_second"])
    elif ttft and pt:
        prefill = round(float(pt) / ttft, 2)
    details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    cached = details.get("cached_tokens") if isinstance(details, dict) else None
    if cached is None:
        cached = timings.get("cache_n")
    return {
        "tag": tag,
        "ok": err is None,
        "error": err,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "cached_tokens": cached,
        "ttft_s": round(ttft, 3) if ttft else None,
        "wall_s": round(end - t0, 3),
        "decode_tps": round(dec, 2),
        "prefill_tps": prefill,
        "text": out[:4000],
    }


def main() -> None:
    quick = os.getenv("QUICK_ONLY", "0") == "1"
    specs = [
        ("short", int(os.getenv("SHORT_PROMPT_TOKENS", "4096")), int(os.getenv("SHORT_OUTPUT_TOKENS", "256"))),
        ("mid", int(os.getenv("MID_PROMPT_TOKENS", "64000")), int(os.getenv("MID_OUTPUT_TOKENS", "256"))),
    ]
    if not quick:
        specs += [
            ("long", int(os.getenv("LONG_PROMPT_TOKENS", "120000")), int(os.getenv("LONG_OUTPUT_TOKENS", "128"))),
            ("deep", int(os.getenv("DEEP_PROMPT_TOKENS", "185000")), int(os.getenv("DEEP_OUTPUT_TOKENS", "128"))),
        ]
    rows = []
    for tag, target, outn in specs:
        print(f"[http] {tag} target={target}", flush=True)
        corpus, meta = prompt_for(target)
        ask = (
            "You are reviewing a long Java backend repository dump. The dump contains exactly one RELEASE_NEEDLE. "
            "First print the exact RELEASE_NEEDLE value. Then write a concise Java reliability review.\n\n"
            + corpus
        )
        row = stream_chat([{"role": "user", "content": ask}], outn, tag)
        row["target_prompt_tokens"] = target
        row["needle"] = meta["needle"]
        row["needle_ok"] = meta["needle"] in (row.get("text") or "")
        rows.append(row)
        print(
            f"[http] {tag}: pt={row['prompt_tokens']} ttft={row['ttft_s']} "
            f"decode={row['decode_tps']} prefill={row['prefill_tps']} needle={row['needle_ok']}",
            flush=True,
        )
    (RES / "http_bench.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
