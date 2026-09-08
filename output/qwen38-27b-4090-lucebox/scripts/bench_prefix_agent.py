#!/usr/bin/env python3
"""OpenClaw-like tool/prefix-cache bench against a live dflash_server.

Measures usage.timings (cached_prefix_tokens, prefilled_tokens, cache_hit,
agent_turn_cache_hit) plus wall. Designed for three server modes:
  nocache  --prefix-cache-slots 0
  prefix   default 32 slots
  agent    32 slots + --agent-turn-cache
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

UNIT = "The quick brown fox jumps over the lazy dog. "
TOK_PER_UNIT = 10.02

SYSTEM = (
    "You are the CodexGame runtime coding agent. "
    "Runtime authority lives in apps/game-runtime. The client is presentation-only. "
    "tickMs is 200. protocol is v1. Replay lives under data/replay. "
    "Use tools to read files. Do not invent rm, git_push, or ssh. "
    "When you need a file, call read_file. Reply with JSON when asked for facts."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file from the workspace. Path is relative to repo root.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative path"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Run a short Python snippet in a sandbox and return stdout.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob_search",
            "description": "Find files matching a glob under the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "root": {"type": "string"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Search file contents with a regular expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "glob": {"type": "string"},
                },
                "required": ["pattern"],
            },
        },
    },
]


def pad(target: int) -> str:
    n = max(1, int(target / TOK_PER_UNIT) - 8)
    return UNIT * n


def chat(base: str, model: str, messages: list, *, tools=None, tool_choice=None,
         max_tokens: int = 128, temperature: float = 1.0, timeout: int = 1800) -> dict:
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.95 if temperature > 0 else 1.0,
        "top_k": 20 if temperature > 0 else 0,
        "chat_template_kwargs": {"enable_thinking": False},
        "stream": False,
    }
    if tools is not None:
        body["tools"] = tools
        body["tool_choice"] = tool_choice or "auto"
    t0 = time.time()
    req = urllib.request.Request(
        f"{base}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
        err = None
    except Exception as e:
        return {"error": str(e), "wall_s": round(time.time() - t0, 2)}
    wall = time.time() - t0
    usage = payload.get("usage") or {}
    timings = usage.get("timings") or payload.get("timings") or {}
    ch = (payload.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    tc = msg.get("tool_calls") or []
    content = msg.get("content") or ""
    return {
        "wall_s": round(wall, 2),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "finish": ch.get("finish_reason"),
        "empty": not bool(content.strip() or tc),
        "n_tools": len(tc),
        "tool_preview": json.dumps(tc, ensure_ascii=False)[:240] if tc else "",
        "preview": (content[:160] if content else "").replace("\n", " / "),
        "cache_hit": timings.get("cache_hit"),
        "cached_prefix_tokens": timings.get("cached_prefix_tokens"),
        "prefilled_tokens": timings.get("prefilled_tokens"),
        "effective_prompt_tokens": timings.get("effective_prompt_tokens"),
        "agent_turn_cache_hit": timings.get("agent_turn_cache_hit"),
        "prefill_ms": timings.get("prefill_ms"),
        "decode_ms": timings.get("decode_ms"),
        "timings": timings,
        "assistant": msg,
    }


def emit(rec: dict) -> None:
    slim = {k: rec.get(k) for k in (
        "id", "error", "wall_s", "prompt_tokens", "completion_tokens",
        "finish", "n_tools", "cache_hit", "cached_prefix_tokens",
        "prefilled_tokens", "effective_prompt_tokens", "agent_turn_cache_hit",
        "prefill_ms", "decode_ms", "preview", "tool_preview",
    )}
    print(json.dumps(slim, ensure_ascii=False), flush=True)


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:18343"
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen38-lucebox"
    out = Path(sys.argv[3] if len(sys.argv) > 3 else ".")
    lane = sys.argv[4] if len(sys.argv) > 4 else "unknown"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    history: list[dict] = [{"role": "system", "content": SYSTEM}]

    def run(rid: str, messages, **kw):
        rec = {"id": rid, "lane": lane}
        rec.update(chat(base, model, messages, **kw))
        rows.append(rec)
        emit(rec)
        return rec

    # --- short OpenClaw-like agent ---
    run("A0_pin", history + [{"role": "user", "content": "Reply with the single word OK."}],
        tools=TOOLS, tool_choice="none", max_tokens=8, temperature=0.0, timeout=180)

    rec = run(
        "A1_tool_call",
        history + [{"role": "user", "content": "Read Agents.md and tell me the runtime tickMs. Use tools."}],
        tools=TOOLS, tool_choice="auto", max_tokens=256, temperature=1.0, timeout=180,
    )
    asst = rec.get("assistant") or {}
    history.append({"role": "user", "content": "Read Agents.md and tell me the runtime tickMs. Use tools."})
    if asst:
        history.append(asst)
        if asst.get("tool_calls"):
            tid = asst["tool_calls"][0].get("id") or "call_1"
            history.append({
                "role": "tool",
                "tool_call_id": tid,
                "content": "tickMs = 200\nprotocol = v1\nreplay = data/replay\n",
            })
            run("A2_tool_result", history + [{"role": "user", "content": "Now answer with JSON only: {\"tick\":...}"}],
                tools=TOOLS, tool_choice="none", max_tokens=64, temperature=1.0, timeout=180)
            history.append({"role": "user", "content": "Now answer with JSON only: {\"tick\":...}"})
            history.append({"role": "assistant", "content": "{\"tick\":200}"})

    run("A3_followup", history + [{"role": "user", "content": "What is protocol version? One word."}],
        tools=TOOLS, tool_choice="none", max_tokens=16, temperature=1.0, timeout=180)
    history.append({"role": "user", "content": "What is protocol version? One word."})
    history.append({"role": "assistant", "content": "v1"})

    # --- grow context, then a short follow-up (the long-ctx cache test) ---
    for target, grow_id, after_id in (
        (28000, "G28", "W28"),
        (64000, "G64", "W64"),
        (128000, "G128", "W128"),
    ):
        history.append({
            "role": "user",
            "content": f"SESSION_LOG_{target}\n" + pad(target) + "\nAcknowledge with OK.",
        })
        run(grow_id, history, tools=TOOLS, tool_choice="none", max_tokens=8, temperature=0.0, timeout=1800)
        history.append({"role": "assistant", "content": "OK"})
        run(
            after_id,
            history + [{"role": "user", "content": "From the session so far, return JSON {\"tick\":200,\"protocol\":\"v1\"} only."}],
            tools=TOOLS, tool_choice="none", max_tokens=48, temperature=0.0, timeout=300,
        )
        history.append({"role": "user", "content": "From the session so far, return JSON {\"tick\":200,\"protocol\":\"v1\"} only."})
        history.append({"role": "assistant", "content": "{\"tick\":200,\"protocol\":\"v1\"}"})

    # mutation: change tools → must miss if cache is identity-correct
    bad = json.loads(json.dumps(TOOLS))
    bad[0]["function"]["description"] += " MUTATION"
    run(
        "M_tool_mut",
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "Reply OK."}],
        tools=bad, tool_choice="none", max_tokens=8, temperature=0.0, timeout=180,
    )

    summary = {"lane": lane, "n": len(rows), "rows": rows}
    (out / f"{lane}.summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
