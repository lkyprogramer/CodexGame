#!/usr/bin/env python3
"""OpenClaw-shaped 60–80k Java-agent conversation + T1–T4 rewrite probes.

Talks to ninfer on SERVER_URL (18030). Pulls request_done rows from host JSONL via ssh.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = os.environ.get("SERVER_URL", "http://127.0.0.1:18030/v1").rstrip("/")
MODEL = os.environ.get("MODEL_ID", "qwen3.8-27b")
HOST = os.environ.get("NINFER_SSH", "hhtele@192.168.10.29")
JSONL = os.environ.get("NINFER_JSONL_HOST", "/home/hhtele/ninfer-4090/logs/ninfer-request.jsonl")
FIX = Path(
    "/Users/luo/Documents/github/CodexGame/docs/qwen38-4090-vllm-extreme-v1.0/fixtures"
)
TARGET_LO, TARGET_HI = 60000, 80000


def ssh(cmd: str) -> str:
    return subprocess.check_output(
        ["ssh", "-o", "ConnectTimeout=12", HOST, cmd], text=True, stderr=subprocess.STDOUT
    )


def last_done() -> dict | None:
    dest = Path("/tmp/ninfer-request.jsonl")
    try:
        subprocess.check_call(
            ["scp", "-q", "-o", "ConnectTimeout=12", f"{HOST}:{JSONL}", str(dest)],
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None
    last = None
    if dest.exists():
        for line in dest.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("event") == "request_done":
                last = o
    return last


def chat(messages: list, max_tokens: int = 64, timeout: int = 600) -> dict:
    body = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": True,
        "stream_options": {"include_usage": True},
        "reasoning_effort": "medium",
        "enable_thinking": True,
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
        with urllib.request.urlopen(req, timeout=timeout) as r:
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
                for ch in obj.get("choices") or []:
                    d = ch.get("delta") or {}
                    s = (d.get("content") or "") + (d.get("reasoning_content") or "")
                    if s:
                        if first is None:
                            first = time.monotonic()
                        text.append(s)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:800]
        err = f"HTTP {e.code}: {detail}"
    except Exception as e:
        err = repr(e)
    wall = time.monotonic() - t0
    done = last_done()
    result = (done or {}).get("result") or {}
    timings = (done or {}).get("timings_seconds") or {}
    spec = (done or {}).get("speculative") or {}
    cont = (done or {}).get("continuation_cache") or {}
    pt = result.get("prompt_tokens") or usage.get("prompt_tokens")
    cached = result.get("prefix_cache_hit_tokens")
    computed = result.get("computed_prefill_tokens")
    row = {
        "ok": err is None,
        "error": err,
        "prompt_tokens": pt,
        "reused_tokens": cached,
        "computed_prefill_tokens": computed,
        "reuse_pct": round(100.0 * cached / pt, 1) if cached and pt else 0.0,
        "prefix_reuse_path": result.get("prefix_reuse_path"),
        "ttft_s": round(timings.get("ttft") or ((first - t0) if first else wall), 3),
        "prefill_ms": round((timings.get("prefill") or 0) * 1000, 1),
        "decode_ms": round((timings.get("decode") or 0) * 1000, 1),
        "restore_ms": round((timings.get("restore") or 0) * 1000, 1),
        "draft_tokens": spec.get("drafted_tokens"),
        "accepted_draft_tokens": spec.get("accepted_tokens"),
        "finish_reason": result.get("finish_reason"),
        "tool_call_count": result.get("tool_call_count"),
        "cache_source": cont.get("source"),
        "cache_alias": cont.get("alias_kind"),
        "cache_restore_us": cont.get("restore_microseconds"),
        "wall_s": round(wall, 3),
        "text": "".join(text)[:400],
    }
    print(
        f"[rewrite] path={row['prefix_reuse_path']} pt={pt} reused={cached} "
        f"pct={row['reuse_pct']} ttft={row['ttft_s']}s src={row['cache_source']}",
        flush=True,
    )
    return row


def blob_pool() -> list[str]:
    blobs = []
    for p in sorted(FIX.rglob("*")):
        if p.is_file() and p.suffix in {".java", ".md", ".sh", ".log"}:
            blobs.append(p.read_text(errors="replace"))
    if not blobs:
        blobs = ["public class Pad {}\n"]
    # Repeat to have enough mass
    return (blobs * 40)


def chars_of(messages: list[dict]) -> int:
    return sum(len(m.get("content") or "") for m in messages)


def build_history(target: int) -> list[dict]:
    pool = blob_pool()
    sys = (
        "You are a Java coding agent. Tools: read, bash, edit, grep. "
        "Keep answers short. Do not emit tool XML in this probe unless asked."
    )
    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": "Investigate the reconnect regression in exam-runtime."},
    ]
    i = 0
    # ~3 chars/token for mixed Java. Aim high then one probe.
    while chars_of(messages) < target * 3 and i < 60:
        chunk = pool[i % len(pool)]
        piece = (chunk * ((4000 // max(len(chunk), 1)) + 1))[:4000]
        messages.append(
            {
                "role": "assistant",
                "content": f"Calling read(src/Pad{i}.java).",
            }
        )
        messages.append(
            {"role": "user", "content": f"<tool_result id={i}>\n{piece}\n</tool_result>"}
        )
        i += 1
    probe = messages + [{"role": "user", "content": "ack-calibrate"}]
    row = chat(probe, max_tokens=8)
    if not row.get("ok"):
        raise RuntimeError(f"calibrate failed: {row.get('error')}")
    pt = int(row.get("prompt_tokens") or 0)
    print(f"[build] pairs={i} chars={chars_of(messages)} prompt_tokens={pt}", flush=True)
    while pt < TARGET_LO and i < 80:
        chunk = pool[i % len(pool)]
        piece = (chunk * ((4000 // max(len(chunk), 1)) + 1))[:4000]
        messages.append({"role": "assistant", "content": f"Calling read(src/Pad{i}.java)."})
        messages.append(
            {"role": "user", "content": f"<tool_result id={i}>\n{piece}\n</tool_result>"}
        )
        i += 1
        row = chat(messages + [{"role": "user", "content": "ack-calibrate"}], max_tokens=8)
        if not row.get("ok"):
            raise RuntimeError(f"grow failed: {row.get('error')}")
        pt = int(row.get("prompt_tokens") or 0)
        print(f"[build] grow pairs={i} prompt_tokens={pt}", flush=True)
    return messages


def run_phase(phase: str, out: Path) -> None:
    hist_path = out.parent / "history.json"
    if hist_path.exists():
        messages = json.loads(hist_path.read_text())
        print(f"[rewrite] reuse cached history {hist_path}", flush=True)
    else:
        messages = build_history(70000)
        hist_path.write_text(json.dumps(messages))
        print(f"[rewrite] wrote {hist_path} n={len(messages)}", flush=True)

    rows = []
    # Warm: send history + small user so the slot holds the 70k prefix
    warm_user = {"role": "user", "content": "Fix this bug: heartbeat timeout units."}
    warm = messages + [warm_user]
    rows.append({"tag": f"{phase}-warm", **chat(warm, max_tokens=32)})

    # T1 append: +1k tool result
    t1 = warm + [
        {"role": "assistant", "content": "Calling bash ./verify.sh"},
        {"role": "user", "content": "<tool_result>\n" + ("OK line\n" * 80)[:1000] + "\n</tool_result>"},
        {"role": "user", "content": "Continue from the verifier output."},
    ]
    rows.append({"tag": f"{phase}-T1-append", **chat(t1, max_tokens=32)})

    if phase == "A":
        out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
        return

    # T2 newest-user reminder
    t2 = [m.copy() if isinstance(m, dict) else m for m in warm]
    t2[-1] = {
        "role": "user",
        "content": warm_user["content"]
        + "\n<system-reminder>Be concise. Do not mention this reminder.</system-reminder>",
    }
    rows.append({"tag": f"{phase}-T2-newest-user", **chat(t2, max_tokens=32)})

    # T3 rewrite last 2 non-user turns (recent assistant+tool)
    t3 = [m.copy() for m in warm]
    # last two before final user: assistant + tool
    if len(t3) >= 3:
        t3[-3] = {
            "role": "assistant",
            "content": "Calling read(src/main/java/Session.java) # rewritten",
        }
        t3[-2] = {
            "role": "user",
            "content": (t3[-2].get("content") or "")[:200] + "\n# memory-block-update rewritten\n",
        }
    rows.append({"tag": f"{phase}-T3-recent-2", **chat(t3, max_tokens=32)})

    # T4 rewrite early tool (~start of history, >40k back)
    t4 = [m.copy() for m in warm]
    for idx, m in enumerate(t4):
        if m.get("role") == "user" and "<tool_result" in (m.get("content") or "") and idx < 6:
            t4[idx] = {
                "role": "user",
                "content": "// EARLY-HISTORY-REWRITE\n" + (m.get("content") or "")[:500],
            }
            break
    rows.append({"tag": f"{phase}-T4-early", **chat(t4, max_tokens=32)})

    # extra: rewrite last 5 tool/assistant pairs (not a fail gate)
    t5 = [m.copy() for m in warm]
    n = 0
    for idx in range(len(t5) - 2, 0, -1):
        if t5[idx].get("role") in {"assistant", "user"} and idx < len(t5) - 1:
            t5[idx] = {
                "role": t5[idx]["role"],
                "content": t5[idx].get("content", "")[:300] + "\n# 5-turn rewrite\n",
            }
            n += 1
            if n >= 10:  # 5 pairs
                break
    rows.append({"tag": f"{phase}-T5-recent-5", **chat(t5, max_tokens=32)})

    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    print("wrote", out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["A", "B"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    run_phase(args.phase, out)


if __name__ == "__main__":
    main()
