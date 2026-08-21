#!/usr/bin/env python3
"""Text-generation eval for HauhauCS Aggressive (not a coding/agent suite)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

NEEDLES = {
    "tick": "FACT_A_RUNTIME_TICK_MS=200",
    "protocol": "FACT_B_PROTOCOL_VERSION=v1",
    "replay": "FACT_C_REPLAY_DIR=data/replay",
}
OFF = {"enable_thinking": False, "reasoning_effort": "low", "preserve_thinking": False}
MED = {"enable_thinking": True, "reasoning_effort": "medium", "preserve_thinking": False}
FILL = (
    "Continue a dense travel essay about a night market in Chengdu. "
    "Keep adding sensory detail and small incidents until the token budget is exhausted. "
    "Do not summarize. Do not stop early."
)


def gpu() -> dict[str, Any]:
    try:
        raw = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.free,utilization.gpu,power.draw,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=5,
        ).strip()
        used, free, util, power, temp = [p.strip() for p in raw.split(",")]
        return {
            "memory_used_mib": float(used),
            "memory_free_mib": float(free),
            "utilization_gpu_pct": float(util),
            "power_w": float(power),
            "temperature_c": float(temp),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


def detect_junk(text: str) -> dict[str, Any]:
    if not text:
        return {"junk_repeat": False, "reason": None}
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) >= 6:
        for window in (1, 2, 4):
            if len(lines) < window * 4:
                continue
            gram = tuple(lines[:window])
            repeats = 1
            idx = window
            while idx + window <= len(lines) and tuple(lines[idx : idx + window]) == gram:
                repeats += 1
                idx += window
            if repeats >= 6:
                return {"junk_repeat": True, "reason": f"line_gram_{window}_x{repeats}"}
    words = text.split()
    if len(words) >= 64:
        for n in (8, 16, 32):
            gram = tuple(words[:n])
            repeats = 1
            idx = n
            while idx + n <= len(words) and tuple(words[idx : idx + n]) == gram:
                repeats += 1
                idx += n
            if repeats >= 4:
                return {"junk_repeat": True, "reason": f"word_gram_{n}_x{repeats}"}
    if re.search(r"(.)\1{40,}", text):
        return {"junk_repeat": True, "reason": "char_run"}
    return {"junk_repeat": False, "reason": None}


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"error_text": body}
        return exc.code, parsed


def pad(n: int) -> str:
    unit = (
        "The archive keeps night-market ledgers, ferry tickets, and rain-blurred postcards. "
        "Simulation authority stays in the runtime. The client is presentation-only. "
    )
    return (unit * max(1, n // 20))[: n * 4]


def chat(
    base: str,
    model: str,
    messages: list[dict[str, Any]],
    *,
    max_tokens: int,
    timeout: int,
    temperature: float,
    top_p: float,
    kwargs: dict[str, Any],
    presence: float = 1.5,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": 20,
        "presence_penalty": presence,
        "max_tokens": max_tokens,
        "chat_template_kwargs": kwargs,
        "stream": False,
    }
    t0 = time.perf_counter()
    status, body = post_json(f"{base}/v1/chat/completions", payload, timeout)
    elapsed = time.perf_counter() - t0
    msg = ((body.get("choices") or [{}])[0].get("message") or {})
    usage = body.get("usage") or {}
    timings = body.get("timings") or {}
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    completion = usage.get("completion_tokens") or 0
    predicted_ms = timings.get("predicted_ms")
    tps = timings.get("predicted_per_second")
    if tps is None and predicted_ms:
        tps = completion / (predicted_ms / 1000)
    draft_n = timings.get("draft_n") or 0
    draft_acc = timings.get("draft_n_accepted") or 0
    junk = detect_junk(str(content) + "\n" + str(reasoning))
    return {
        "http": status,
        "elapsed_s": elapsed,
        "content": content,
        "reasoning": reasoning,
        "empty": not str(content).strip(),
        "finish": ((body.get("choices") or [{}])[0].get("finish_reason")),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": completion,
        "decode_tokens_per_s": tps,
        "accept_rate": (draft_acc / draft_n) if draft_n else None,
        "draft_n": draft_n,
        "draft_n_accepted": draft_acc,
        "timings": timings,
        "junk_repeat": junk["junk_repeat"],
        "junk_reason": junk["reason"],
        "error": body.get("error") or body.get("error_text"),
        "gpu_after": gpu(),
    }


def cases(long_needles: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in (1, 2, 3):
        out.append(
            {
                "id": f"F_off_1024_r{i}",
                "class": "F",
                "temperature": 0.7,
                "top_p": 0.80,
                "presence": 1.5,
                "max_tokens": 1024,
                "timeout": 180,
                "kwargs": OFF,
                "messages": [{"role": "user", "content": FILL}],
            }
        )
    out.extend(
        [
            {
                "id": "CN_story_2048",
                "class": "Q",
                "temperature": 0.7,
                "top_p": 0.80,
                "presence": 1.5,
                "max_tokens": 2048,
                "timeout": 300,
                "kwargs": OFF,
                "messages": [
                    {
                        "role": "user",
                        "content": "写一篇两千字左右的短小说：雨夜的成都，一个修钟表的人等到了二十年前寄出的信。不要列提纲，直接正文。",
                    }
                ],
            },
            {
                "id": "EN_cont_2048",
                "class": "Q",
                "temperature": 0.7,
                "top_p": 0.80,
                "presence": 1.5,
                "max_tokens": 2048,
                "timeout": 300,
                "kwargs": OFF,
                "messages": [
                    {
                        "role": "user",
                        "content": "Continue this opening for a long stretch, stay in close third person, no outline:\n\nThe lighthouse keeper counted the missing bolts by lantern-light and decided not to tell the mainland yet.",
                    }
                ],
            },
            {
                "id": "style_turn1",
                "class": "S",
                "temperature": 0.7,
                "top_p": 0.80,
                "presence": 1.5,
                "max_tokens": 400,
                "timeout": 120,
                "kwargs": OFF,
                "messages": [
                    {
                        "role": "user",
                        "content": "用冷硬短句写一段码头守夜。不要抒情。",
                    }
                ],
            },
            {
                "id": "empty_budget",
                "class": "E",
                "temperature": 0.7,
                "top_p": 0.80,
                "presence": 1.5,
                "max_tokens": 2048,
                "timeout": 240,
                "kwargs": OFF,
                "messages": [{"role": "user", "content": "用三百字描写一碗担担面冷却时的声音。"}],
            },
            {
                "id": "think_on_smoke",
                "class": "T",
                "temperature": 1.0,
                "top_p": 0.95,
                "presence": 0.0,
                "max_tokens": 1024,
                "timeout": 180,
                "kwargs": MED,
                "messages": [{"role": "user", "content": "用三句话说明为什么单卡 24GB 不该同时加载两个 27B。"}],
            },
            {
                "id": "L_28k",
                "class": "L",
                "temperature": 0.7,
                "top_p": 0.80,
                "presence": 1.5,
                "max_tokens": 256,
                "timeout": 600,
                "kwargs": OFF,
                "messages": [
                    {
                        "role": "user",
                        "content": pad(28000)
                        + "\n"
                        + "\n".join(NEEDLES.values())
                        + '\nReturn JSON only: {"tick":...,"protocol":"...","replay":"..."}\n',
                    }
                ],
            },
        ]
    )
    if long_needles:
        out.append(
            {
                "id": "L_64k",
                "class": "L",
                "temperature": 0.7,
                "top_p": 0.80,
                "presence": 1.5,
                "max_tokens": 256,
                "timeout": 900,
                "kwargs": OFF,
                "messages": [
                    {
                        "role": "user",
                        "content": pad(64000)
                        + "\n"
                        + "\n".join(NEEDLES.values())
                        + '\nReturn JSON only: {"tick":...,"protocol":"...","replay":"..."}\n',
                    }
                ],
            }
        )
    return out


def median(xs: list[float]) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    n = len(xs)
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:18443")
    parser.add_argument("--model", default="openclaw/Qwen3.8-27B-TEXT")
    parser.add_argument("--out", required=True)
    parser.add_argument("--long-needles", action="store_true")
    parser.add_argument("--skip-wait", action="store_true")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not args.skip_wait:
        deadline = time.monotonic() + 300
        last = ""
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"{args.base}/v1/models", timeout=5) as res:
                    if json.loads(res.read().decode()).get("data"):
                        break
            except Exception as exc:  # noqa: BLE001
                last = repr(exc)
            time.sleep(2)
        else:
            raise RuntimeError(f"not ready: {last}")
    idle = gpu()
    results = []
    style_prev = None
    for spec in cases(args.long_needles):
        messages = list(spec["messages"])
        if spec["id"] == "style_turn1":
            pass
        result = chat(
            args.base,
            args.model,
            messages,
            max_tokens=spec["max_tokens"],
            timeout=spec["timeout"],
            temperature=spec["temperature"],
            top_p=spec["top_p"],
            kwargs=spec["kwargs"],
            presence=spec["presence"],
        )
        if spec["id"].startswith("L_"):
            blob = (result.get("content") or "") + (result.get("reasoning") or "")
            result["needles"] = {k: ("200" in blob if k == "tick" else NEEDLES[k].split("=")[-1] in blob or v.split("=")[-1] in blob) for k, v in NEEDLES.items()}
            result["needles"] = {
                "tick": "200" in blob,
                "protocol": "v1" in blob,
                "replay": "data/replay" in blob,
            }
        result["id"] = spec["id"]
        result["class"] = spec["class"]
        if spec["id"] == "style_turn1":
            style_prev = result.get("content") or ""
            follow = chat(
                args.base,
                args.model,
                [
                    {"role": "user", "content": "用冷硬短句写一段码头守夜。不要抒情。"},
                    {"role": "assistant", "content": style_prev},
                    {"role": "user", "content": "同一人看见一封没有署名的信。保持同一文风，再写一段。"},
                ],
                max_tokens=400,
                timeout=120,
                temperature=0.7,
                top_p=0.80,
                kwargs=OFF,
                presence=1.5,
            )
            follow["id"] = "style_turn2"
            follow["class"] = "S"
            (out / "style_turn2.json").write_text(json.dumps(follow, ensure_ascii=False, indent=2) + "\n")
            slim_f = {k: follow[k] for k in follow if k not in {"content", "reasoning"}}
            slim_f["content_preview"] = (follow.get("content") or "")[:400]
            slim_f["content_len"] = len(follow.get("content") or "")
            results.append(slim_f)
        (out / f"{spec['id']}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        slim = {k: result[k] for k in result if k not in {"content", "reasoning"}}
        slim["content_preview"] = (result.get("content") or "")[:400]
        slim["content_len"] = len(result.get("content") or "")
        results.append(slim)
        print(
            json.dumps(
                {
                    "id": spec["id"],
                    "tps": result.get("decode_tokens_per_s"),
                    "empty": result.get("empty"),
                    "junk": result.get("junk_repeat"),
                    "tok": result.get("completion_tokens"),
                    "needles": result.get("needles"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    fills = [r["decode_tokens_per_s"] for r in results if r.get("class") == "F" and isinstance(r.get("decode_tokens_per_s"), (int, float))]
    summary = {
        "model": args.model,
        "base": args.base,
        "idle_gpu": idle,
        "empty": sum(1 for r in results if r.get("empty")),
        "junk": sum(1 for r in results if r.get("junk_repeat")),
        "fill_median_tps": median(fills),
        "fill_avg_tps": (sum(fills) / len(fills)) if fills else None,
        "gpu": gpu(),
        "results": results,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in summary if k != "results"}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
